"""Hop-1 SSE Event Stream Consumer and Live UI State Accumulator.

Consumes typed streaming events from the backend AgentCore / graph execution
and maintains the reactive UI state accumulator driving the Streamlit Executive
Decision Card and Audit Trail.

Conforms to INTERFACE_OBSERVABILITY_SYSTEM.md Sections 2, 2a, 3, 4.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.state.schema import (
    DecisionCardPayload,
    Discrepancy,
    IroncladState,
    LienChainStatus,
    RetainageAuditResult,
    StatutoryClock,
)
from src.ui.event_types import (
    ApprovalRequiredEvent,
    BaseStreamEvent,
    ErrorEvent,
    IroncladStreamEvent,
    ReasoningDeltaEvent,
    StateUpdateEvent,
    StreamEndEvent,
    StreamEventType,
    TextDeltaEvent,
    ToolCallDeltaEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
    parse_sse_event,
)

logger = logging.getLogger("ironclad.ui.stream_consumer")


class ToolCallStatusLine(BaseModel):
    """Status record of an individual tool invocation within a node expander."""

    model_config = ConfigDict(extra="forbid")

    tool_call_id: str
    tool_name: str
    node: str
    status: Literal["running", "completed", "failed"] = "running"
    input_preview: dict[str, Any] = Field(default_factory=dict)
    partial_output: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class ReasoningTraceEntry(BaseModel):
    """Captured reasoning or thinking token delta for the Audit Trail."""

    model_config = ConfigDict(extra="forbid")

    node: str
    source: Literal["native-thinking", "graph-trace"]
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UIStateAccumulator(BaseModel):
    """Live accumulated UI state for the zero-chat Streamlit application."""

    model_config = ConfigDict(extra="forbid")

    # Status Banner & Life Cycle
    status_banner: str = "Initializing draw packet audit..."
    is_running: bool = True
    is_paused_for_hitl: bool = False
    checkpoint_id: str | None = None

    # Audit Trail Sub-Expanders (Keyed by Agent Node Name)
    node_status_lines: dict[str, list[ToolCallStatusLine]] = Field(default_factory=dict)
    node_reasoning_traces: dict[str, list[ReasoningTraceEntry]] = Field(default_factory=dict)

    # Primary Card Progressive State
    gross_amount_requested: Decimal | None = None
    contractual_retainage_withheld: Decimal | None = None
    net_recommended_release: Decimal | None = None
    calculation_trace: list[str] = Field(default_factory=list)

    lien_chain_status: LienChainStatus | None = None
    waiver_findings: list[dict[str, Any]] = Field(default_factory=list)
    statutory_clock: StatutoryClock | None = None

    # Structured Deliverable & Compliance Defects
    decision_card_payload: DecisionCardPayload | None = None
    flagged_discrepancies: list[Discrepancy] = Field(default_factory=list)

    # Toast Notifications & Failure States
    toast_notifications: list[str] = Field(default_factory=list)
    error_notice: dict[str, Any] | None = None


class StreamConsumer:
    """Consumes typed streaming events and updates UIStateAccumulator."""

    def __init__(self, initial_state: IroncladState | None = None) -> None:
        self.state = UIStateAccumulator()
        if initial_state is not None:
            self.ingest_state_snapshot(initial_state)

    def ingest_state_snapshot(
        self, snapshot: IroncladState, checkpoint_id: str | None = None
    ) -> None:
        """Re-hydrates accumulator from an IroncladState snapshot directly (tab reloads)."""
        if snapshot.retainage_audit_result:
            self.state.gross_amount_requested = snapshot.retainage_audit_result.gross_amount_requested
            self.state.contractual_retainage_withheld = snapshot.retainage_audit_result.contractual_retainage_withheld
            self.state.net_recommended_release = snapshot.retainage_audit_result.net_recommended_release
            self.state.calculation_trace = list(snapshot.retainage_audit_result.calculation_trace)

        if snapshot.lien_chain_status:
            self.state.lien_chain_status = snapshot.lien_chain_status

        if snapshot.statutory_prompt_pay_clock:
            self.state.statutory_clock = snapshot.statutory_prompt_pay_clock

        self.state.flagged_discrepancies = list(snapshot.flagged_discrepancies)

        if snapshot.decision_card_payload:
            self.state.decision_card_payload = snapshot.decision_card_payload
            self.state.is_paused_for_hitl = True
            self.state.is_running = False
            self.state.status_banner = "Audit complete — awaiting your decision."

        if checkpoint_id:
            self.state.checkpoint_id = checkpoint_id

        if any(e.blocking for e in snapshot.error_logs):
            blocking_err = next(e for e in snapshot.error_logs if e.blocking)
            self.state.error_notice = {
                "code": blocking_err.error_type,
                "message": blocking_err.message,
                "recoverable": False,
            }
            self.state.is_running = False
            self.state.status_banner = "Audit could not complete automatically — flagged for manual review"

    def consume_event(self, event: BaseStreamEvent) -> None:
        """Applies a single typed streaming event to the accumulator."""
        match event.event_type:
            case StreamEventType.TEXT_DELTA:
                assert isinstance(event, TextDeltaEvent)
                self.state.status_banner = event.content

            case StreamEventType.REASONING_DELTA:
                assert isinstance(event, ReasoningDeltaEvent)
                entry = ReasoningTraceEntry(
                    node=event.node,
                    source=event.source,
                    content=event.content,
                    timestamp=event.timestamp,
                )
                self.state.node_reasoning_traces.setdefault(event.node, []).append(entry)

            case StreamEventType.TOOL_CALL_START:
                assert isinstance(event, ToolCallStartEvent)
                line = ToolCallStatusLine(
                    tool_call_id=event.tool_call_id,
                    tool_name=event.tool_name,
                    node=event.node,
                    status="running",
                    input_preview=event.input_preview,
                    started_at=event.timestamp,
                )
                self.state.node_status_lines.setdefault(event.node, []).append(line)

            case StreamEventType.TOOL_CALL_DELTA:
                assert isinstance(event, ToolCallDeltaEvent)
                for lines in self.state.node_status_lines.values():
                    for line in lines:
                        if line.tool_call_id == event.tool_call_id:
                            line.partial_output.update(event.partial_output)

            case StreamEventType.TOOL_CALL_RESULT:
                assert isinstance(event, ToolCallResultEvent)
                for lines in self.state.node_status_lines.values():
                    for line in lines:
                        if line.tool_call_id == event.tool_call_id:
                            line.status = "completed" if event.success else "failed"
                            line.result = event.result
                            line.error = event.error
                            line.completed_at = event.timestamp

                # Capture notification toast confirmations
                if event.tool_name == "dispatch_decision_notification" and event.success:
                    dispatched_to = event.result.get("dispatched_to", [])
                    self.state.toast_notifications.append(
                        f"Notification dispatched to: {', '.join(dispatched_to)}"
                    )

            case StreamEventType.STATE_UPDATE:
                assert isinstance(event, StateUpdateEvent)
                self._apply_state_update(event)

            case StreamEventType.APPROVAL_REQUIRED:
                assert isinstance(event, ApprovalRequiredEvent)
                self.state.checkpoint_id = event.checkpoint_id
                self.state.decision_card_payload = event.action_preview
                self.state.is_paused_for_hitl = True
                self.state.is_running = False
                self.state.status_banner = "Audit complete — awaiting your decision."

            case StreamEventType.ERROR:
                assert isinstance(event, ErrorEvent)
                self.state.error_notice = {
                    "code": event.code,
                    "message": event.message,
                    "recoverable": event.recoverable,
                }
                self.state.is_running = False
                self.state.status_banner = (
                    "Audit could not complete automatically — flagged for manual review"
                )

            case StreamEventType.STREAM_END:
                assert isinstance(event, StreamEndEvent)
                self.state.is_running = False

    def _apply_state_update(self, event: StateUpdateEvent) -> None:
        """Internal handler for progressive state-update event fields."""
        field_name = event.field_name
        val = event.value

        if field_name == "retainage_audit_result" and val:
            if isinstance(val, dict):
                val = RetainageAuditResult.model_validate(val)
            self.state.gross_amount_requested = val.gross_amount_requested
            self.state.contractual_retainage_withheld = val.contractual_retainage_withheld
            self.state.net_recommended_release = val.net_recommended_release
            self.state.calculation_trace = list(val.calculation_trace)

        elif field_name == "lien_chain_status" and val:
            self.state.lien_chain_status = LienChainStatus(val) if isinstance(val, str) else val

        elif field_name == "statutory_prompt_pay_clock" and val:
            if isinstance(val, dict):
                val = StatutoryClock.model_validate(val)
            self.state.statutory_clock = val

        elif field_name == "flagged_discrepancies" and val:
            if isinstance(val, list):
                self.state.flagged_discrepancies = [
                    Discrepancy.model_validate(d) if isinstance(d, dict) else d for d in val
                ]
            elif isinstance(val, (dict, Discrepancy)):
                d_obj = Discrepancy.model_validate(val) if isinstance(val, dict) else val
                self.state.flagged_discrepancies.append(d_obj)

        elif field_name == "decision_card_payload" and val:
            if isinstance(val, dict):
                val = DecisionCardPayload.model_validate(val)
            self.state.decision_card_payload = val

    async def consume_stream(
        self, stream: AsyncIterator[IroncladStreamEvent | str]
    ) -> UIStateAccumulator:
        """Asynchronously consumes an entire event stream or SSE text stream."""
        async for chunk in stream:
            if isinstance(chunk, str):
                if chunk.strip():
                    event = parse_sse_event(chunk)
                    self.consume_event(event)
            else:
                self.consume_event(chunk)
        return self.state
