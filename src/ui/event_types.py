"""Typed Streaming Event Contracts for IRONCLAD Sentinel.

Defines the authoritative 8 streaming event contracts and SSE transport formats
conforming to INTERFACE_OBSERVABILITY_SYSTEM.md Sections 2, 2a, 3, 4 and
AGENT_MASTER_PLAN.md Section 7.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.state.schema import DecisionCardPayload


class StreamEventType(str, Enum):
    """Authoritative streaming event types emitted across Hop-1."""

    TEXT_DELTA = "text-delta"
    REASONING_DELTA = "reasoning-delta"
    TOOL_CALL_START = "tool-call-start"
    TOOL_CALL_DELTA = "tool-call-delta"
    TOOL_CALL_RESULT = "tool-call-result"
    STATE_UPDATE = "state-update"
    APPROVAL_REQUIRED = "approval-required"
    ERROR = "error"
    STREAM_END = "stream-end"


def filter_sensitive_reasoning(text: str, max_verbatim_len: int = 250) -> str:
    """Filters out long verbatim extracted PDF text from reasoning traces.

    Conforms to INTERFACE_OBSERVABILITY_SYSTEM.md Section 3c.
    """
    # Replace lengthy raw table blocks or repetitive document text dumps
    if len(text) > max_verbatim_len and "\n" in text:
        lines = text.split("\n")
        if len(lines) > 6:
            summary = lines[0]
            return f"{summary}\n[document text — see field value above]"
    return text


class BaseStreamEvent(BaseModel):
    """Base schema for all typed streaming events."""

    model_config = ConfigDict(extra="forbid")

    event_type: StreamEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TextDeltaEvent(BaseStreamEvent):
    """Status banner and top-level textual state transitions."""

    event_type: Literal[StreamEventType.TEXT_DELTA] = StreamEventType.TEXT_DELTA
    node: str | None = Field(default=None, description="Originating graph node")
    content: str = Field(..., description="Status banner message")


class ReasoningDeltaEvent(BaseStreamEvent):
    """Node internal thoughts or native model thinking deltas."""

    event_type: Literal[StreamEventType.REASONING_DELTA] = StreamEventType.REASONING_DELTA
    node: str = Field(..., description="Originating agent node name")
    source: Literal["native-thinking", "graph-trace"] = Field(
        ..., description="Origin of reasoning delta"
    )
    content: str = Field(..., description="Reasoning text")

    def model_post_init(self, context: Any, /) -> None:
        """Filter sensitive raw document text upon initialization."""
        object.__setattr__(self, "content", filter_sensitive_reasoning(self.content))


class ToolCallStartEvent(BaseStreamEvent):
    """Emitted the instant an external or deterministic tool is invoked."""

    event_type: Literal[StreamEventType.TOOL_CALL_START] = StreamEventType.TOOL_CALL_START
    tool_call_id: str = Field(..., description="Unique tool call invocation ID")
    tool_name: str = Field(..., description="Name of invoked tool")
    node: str = Field(..., description="Originating agent node name")
    input_preview: dict[str, Any] = Field(
        default_factory=dict,
        description="Sanitized input summary (never raw bytes or paths)",
    )


class ToolCallDeltaEvent(BaseStreamEvent):
    """Emitted during partial extraction streams (e.g. OCR field by field)."""

    event_type: Literal[StreamEventType.TOOL_CALL_DELTA] = StreamEventType.TOOL_CALL_DELTA
    tool_call_id: str = Field(..., description="Associated tool call ID")
    partial_output: dict[str, Any] = Field(..., description="Partial extraction fields")


class ToolCallResultEvent(BaseStreamEvent):
    """Emitted on completion of any tool invocation."""

    event_type: Literal[StreamEventType.TOOL_CALL_RESULT] = StreamEventType.TOOL_CALL_RESULT
    tool_call_id: str = Field(..., description="Associated tool call ID")
    tool_name: str = Field(..., description="Name of executed tool")
    node: str = Field(..., description="Originating agent node name")
    success: bool = Field(..., description="Whether tool execution succeeded")
    result: dict[str, Any] = Field(default_factory=dict, description="Typed output payload")
    error: str | None = Field(default=None, description="Failure description if failed")


class StateUpdateEvent(BaseStreamEvent):
    """Emitted when a verified field write is merged into IroncladState."""

    event_type: Literal[StreamEventType.STATE_UPDATE] = StreamEventType.STATE_UPDATE
    field_name: str = Field(..., description="Target IroncladState attribute name")
    reducer: str = Field(
        ...,
        description="Applied reducer: immutable-after-init | single-writer last-write-wins | append-only | merge-by-key",
    )
    value: Any = Field(..., description="Updated value or record snapshot")
    caller_node: str = Field(..., description="Authorized writer node name")


class ApprovalRequiredEvent(BaseStreamEvent):
    """Emitted when the graph reaches the HITL interrupt gate."""

    event_type: Literal[StreamEventType.APPROVAL_REQUIRED] = StreamEventType.APPROVAL_REQUIRED
    checkpoint_id: str = Field(..., description="Durable checkpoint identifier")
    action_preview: DecisionCardPayload = Field(
        ..., description="Full Executive Decision Card payload for human sign-off"
    )
    graph_node: str = Field(
        default="EverydayDecisionCardEmitter",
        description="Node paused at interrupt checkpoint",
    )


class ErrorEvent(BaseStreamEvent):
    """Emitted on permanent system failures or blocking compliance halts."""

    event_type: Literal[StreamEventType.ERROR] = StreamEventType.ERROR
    code: str = Field(..., description="Typed domain error code")
    message: str = Field(..., description="Descriptive error explanation")
    recoverable: bool = Field(default=False, description="Whether error is recoverable")
    node: str | None = Field(default=None, description="Failing node if localized")


class StreamEndEvent(BaseStreamEvent):
    """Emitted when execution halts, pauses for HITL, or finishes."""

    event_type: Literal[StreamEventType.STREAM_END] = StreamEventType.STREAM_END
    reason: Literal["interrupted", "completed", "error"] = Field(
        ..., description="Reason stream closed"
    )


# Tagged Union for all streaming events
IroncladStreamEvent = Annotated[
    TextDeltaEvent | ReasoningDeltaEvent | ToolCallStartEvent | ToolCallDeltaEvent | ToolCallResultEvent | StateUpdateEvent | ApprovalRequiredEvent | ErrorEvent | StreamEndEvent,
    Field(discriminator="event_type"),
]


def format_sse_event(event: BaseStreamEvent) -> str:
    """Encodes a typed streaming event into standard Server-Sent Event (SSE) wire format."""
    payload_json = event.model_dump_json()
    return f"event: {event.event_type.value}\ndata: {payload_json}\n\n"


def parse_sse_event(raw_sse_text: str) -> IroncladStreamEvent:
    """Parses a Server-Sent Event (SSE) chunk into a strictly typed IroncladStreamEvent."""
    event_type_str: str | None = None
    data_lines: list[str] = []

    for line in raw_sse_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("event:"):
            event_type_str = line[len("event:") :].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:") :].strip())

    if not event_type_str:
        raise ValueError(f"Invalid SSE packet: missing 'event:' header in '{raw_sse_text}'")

    data_json_str = "\n".join(data_lines)
    if not data_json_str:
        raise ValueError(f"Invalid SSE packet: missing 'data:' payload in '{raw_sse_text}'")

    raw_dict = json.loads(data_json_str)
    return parse_stream_event_dict(raw_dict, event_type_str)


def parse_stream_event_dict(data: dict[str, Any], event_type_hint: str | None = None) -> IroncladStreamEvent:
    """Constructs the exact typed stream event model from a raw dictionary."""
    event_type_val = event_type_hint or data.get("event_type")
    if not event_type_val:
        raise ValueError(f"Missing event_type in dictionary payload: {data}")

    type_mapping: dict[str, type[BaseStreamEvent]] = {
        StreamEventType.TEXT_DELTA.value: TextDeltaEvent,
        StreamEventType.REASONING_DELTA.value: ReasoningDeltaEvent,
        StreamEventType.TOOL_CALL_START.value: ToolCallStartEvent,
        StreamEventType.TOOL_CALL_DELTA.value: ToolCallDeltaEvent,
        StreamEventType.TOOL_CALL_RESULT.value: ToolCallResultEvent,
        StreamEventType.STATE_UPDATE.value: StateUpdateEvent,
        StreamEventType.APPROVAL_REQUIRED.value: ApprovalRequiredEvent,
        StreamEventType.ERROR.value: ErrorEvent,
        StreamEventType.STREAM_END.value: StreamEndEvent,
    }

    cls = type_mapping.get(event_type_val)
    if not cls:
        raise ValueError(f"Unknown stream event type '{event_type_val}'")

    return cls.model_validate(data)  # type: ignore[return-value]
