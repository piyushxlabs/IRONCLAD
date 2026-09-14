"""Unit tests for typed streaming events, SSE serialization, and StreamConsumer."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.state.schema import (
    DecisionCardPayload,
    DrawPacketMeta,
    IroncladState,
    LienChainStatus,
    RetainageAuditResult,
    StatutoryClock,
)
from src.ui.event_types import (
    ApprovalRequiredEvent,
    ErrorEvent,
    ReasoningDeltaEvent,
    StateUpdateEvent,
    StreamEndEvent,
    StreamEventType,
    TextDeltaEvent,
    ToolCallDeltaEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
    format_sse_event,
    parse_sse_event,
)
from src.ui.stream_consumer import StreamConsumer


def test_text_delta_event_serialization_and_sse() -> None:
    """Verify TextDeltaEvent validation, JSON serialization, and SSE formatting."""
    event = TextDeltaEvent(
        content="Auditing draw application #1...",
        node="ForensicAuditSentinel",
    )
    assert event.event_type == StreamEventType.TEXT_DELTA
    assert event.content == "Auditing draw application #1..."
    assert event.node == "ForensicAuditSentinel"

    sse_text = format_sse_event(event)
    assert sse_text.startswith("event: text-delta\ndata: {")
    assert "Auditing draw application #1..." in sse_text

    parsed = parse_sse_event(sse_text)
    assert isinstance(parsed, TextDeltaEvent)
    assert parsed.content == event.content
    assert parsed.node == event.node


def test_reasoning_delta_and_sensitive_text_filter() -> None:
    """Verify reasoning delta filtering of long verbatim document dumps."""
    short_reasoning = "Mapped 3 continuation items to G703 line item specs."
    event_short = ReasoningDeltaEvent(
        node="ForensicAuditSentinel",
        source="graph-trace",
        content=short_reasoning,
    )
    assert event_short.content == short_reasoning

    long_verbatim = (
        "Item 1: Masonry work done\n"
        "Item 2: Electrical conduit installed\n"
        "Item 3: Drywall framing stage 1\n"
        "Item 4: Concrete foundation poured\n"
        "Item 5: Plumbing rough-in complete\n"
        "Item 6: HVAC ductwork installed\n"
        "Item 7: Fire alarm cabling pulled\n"
        "Item 8: Steel girder erection\n"
        "CONFIDENTIAL SUBCONTRACTOR UNIT PRICING: $450,000"
    )
    event_filtered = ReasoningDeltaEvent(
        node="ForensicAuditSentinel",
        source="native-thinking",
        content=long_verbatim,
    )
    assert "[document text — see field value above]" in event_filtered.content

    sse_text = format_sse_event(event_filtered)
    parsed = parse_sse_event(sse_text)
    assert isinstance(parsed, ReasoningDeltaEvent)
    assert parsed.source == "native-thinking"


def test_tool_call_lifecycle_events() -> None:
    """Verify tool-call-start -> tool-call-delta -> tool-call-result lifecycle."""
    start_ev = ToolCallStartEvent(
        tool_call_id="call-extract-001",
        tool_name="extract_draw_packet_metadata",
        node="ForensicAuditSentinel",
        input_preview={"source_document": "draw_1.pdf"},
    )
    delta_ev = ToolCallDeltaEvent(
        tool_call_id="call-extract-001",
        partial_output={"line_items_count": 2},
    )
    result_ev = ToolCallResultEvent(
        tool_call_id="call-extract-001",
        tool_name="extract_draw_packet_metadata",
        node="ForensicAuditSentinel",
        success=True,
        result={"line_items": [{"line_item_id": "LI-001"}]},
    )

    consumer = StreamConsumer()
    consumer.consume_event(start_ev)
    lines = consumer.state.node_status_lines["ForensicAuditSentinel"]
    assert len(lines) == 1
    assert lines[0].status == "running"
    assert lines[0].input_preview["source_document"] == "draw_1.pdf"

    consumer.consume_event(delta_ev)
    assert lines[0].partial_output["line_items_count"] == 2

    consumer.consume_event(result_ev)
    assert lines[0].status == "completed"
    assert lines[0].result["line_items"][0]["line_item_id"] == "LI-001"


def test_state_update_progressive_card_population() -> None:
    """Verify state-update events progressively populate primary card metrics and badges."""
    consumer = StreamConsumer()

    # Retainage Math update
    retainage_result = RetainageAuditResult(
        gross_amount_requested=Decimal("150000.00"),
        contractual_retainage_withheld=Decimal("15000.00"),
        net_recommended_release=Decimal("135000.00"),
        calculation_trace=["Gross: 150000.00", "Retainage (10%): 15000.00", "Net: 135000.00"],
    )
    consumer.consume_event(
        StateUpdateEvent(
            field_name="retainage_audit_result",
            reducer="single-writer last-write-wins",
            value=retainage_result.model_dump(),
            caller_node="ForensicAuditSentinel",
        )
    )

    assert consumer.state.gross_amount_requested == Decimal("150000.00")
    assert consumer.state.contractual_retainage_withheld == Decimal("15000.00")
    assert consumer.state.net_recommended_release == Decimal("135000.00")
    assert len(consumer.state.calculation_trace) == 3

    # Lien Chain status update
    consumer.consume_event(
        StateUpdateEvent(
            field_name="lien_chain_status",
            reducer="single-writer last-write-wins",
            value="VALID",
            caller_node="ForensicAuditSentinel",
        )
    )
    assert consumer.state.lien_chain_status == LienChainStatus.VALID

    # Statutory clock update
    clock = StatutoryClock(
        state="TX",
        days_remaining=7,
        deadline_timestamp=datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC),
        penalty_interest_rate=Decimal("0.015"),
        statute_reference="Tex. Prop. Code § 28.002",
    )
    consumer.consume_event(
        StateUpdateEvent(
            field_name="statutory_prompt_pay_clock",
            reducer="single-writer last-write-wins",
            value=clock.model_dump(),
            caller_node="FairPayStatutoryGuardian",
        )
    )
    assert consumer.state.statutory_clock is not None
    assert consumer.state.statutory_clock.days_remaining == 7


def test_approval_required_and_pause_handling() -> None:
    """Verify approval-required event pauses execution, freezes banner, and loads decision card."""
    card_payload = DecisionCardPayload(
        draw_number=1,
        project_name="Metropolitan Medical Center",
        subcontractor_trade="Structural Steel Framing",
        gross_amount_requested=Decimal("250000.00"),
        contractual_retainage_withheld=Decimal("25000.00"),
        net_recommended_release=Decimal("225000.00"),
        lien_chain_status=LienChainStatus.VALID,
        statutory_prompt_pay_clock=StatutoryClock(
            state="TX",
            days_remaining=10,
            deadline_timestamp=datetime(2026, 10, 5, tzinfo=UTC),
            penalty_interest_rate=Decimal("0.015"),
            statute_reference="Tex. Prop. Code § 28.002",
        ),
        recommended_action="APPROVE_RELEASE",
        blocking_discrepancies=[],
        confidence_score=1.0,
    )

    event = ApprovalRequiredEvent(
        checkpoint_id="chk-session-hitl-001",
        action_preview=card_payload,
        graph_node="EverydayDecisionCardEmitter",
    )

    sse_text = format_sse_event(event)
    parsed = parse_sse_event(sse_text)
    assert isinstance(parsed, ApprovalRequiredEvent)

    consumer = StreamConsumer()
    consumer.consume_event(parsed)

    assert consumer.state.is_paused_for_hitl is True
    assert consumer.state.is_running is False
    assert consumer.state.checkpoint_id == "chk-session-hitl-001"
    assert consumer.state.status_banner == "Audit complete — awaiting your decision."
    assert consumer.state.decision_card_payload is not None
    assert consumer.state.decision_card_payload.recommended_action == "APPROVE_RELEASE"


def test_error_event_handling() -> None:
    """Verify error event switches status banner and attaches typed notice."""
    err_event = ErrorEvent(
        code="SecurityValidationError",
        message="Path traversal detected in draw packet source URI",
        recoverable=False,
        node="Ingress",
    )

    consumer = StreamConsumer()
    consumer.consume_event(err_event)

    assert consumer.state.is_running is False
    assert consumer.state.error_notice is not None
    assert consumer.state.error_notice["code"] == "SecurityValidationError"
    assert "Path traversal" in consumer.state.error_notice["message"]
    assert "flagged for manual review" in consumer.state.status_banner


def test_stream_consumer_tab_reload_snapshot_ingestion() -> None:
    """Verify consumer re-hydrates state directly from an IroncladState snapshot."""
    card_payload = DecisionCardPayload(
        draw_number=2,
        project_name="Civic Center Phase 2",
        subcontractor_trade="HVAC Mechanical",
        gross_amount_requested=Decimal("80000.00"),
        contractual_retainage_withheld=Decimal("8000.00"),
        net_recommended_release=Decimal("72000.00"),
        lien_chain_status=LienChainStatus.VALID,
        recommended_action="APPROVE_RELEASE",
    )
    retainage_result = RetainageAuditResult(
        gross_amount_requested=Decimal("80000.00"),
        contractual_retainage_withheld=Decimal("8000.00"),
        net_recommended_release=Decimal("72000.00"),
        calculation_trace=["Calculated 10%"],
    )

    state = IroncladState(
        draw_packet_meta=DrawPacketMeta(
            project_id="PROJ-CIVIC",
            subcontractor_id="SUB-HVAC",
            draw_number=2,
            source_uris=["docs/draw_2.pdf"],
        ),
        retainage_audit_result=retainage_result,
        lien_chain_status=LienChainStatus.VALID,
        decision_card_payload=card_payload,
    )

    consumer = StreamConsumer(initial_state=state)
    assert consumer.state.gross_amount_requested == Decimal("80000.00")
    assert consumer.state.net_recommended_release == Decimal("72000.00")
    assert consumer.state.lien_chain_status == LienChainStatus.VALID
    assert consumer.state.decision_card_payload is not None
    assert consumer.state.is_paused_for_hitl is True
    assert consumer.state.is_running is False


@pytest.mark.asyncio
async def test_consume_stream_async_iterator() -> None:
    """Verify consume_stream handles an asynchronous stream of SSE chunks end-to-end."""
    async def mock_sse_stream() -> AsyncIterator[str]:
        yield format_sse_event(TextDeltaEvent(content="Starting analysis..."))
        yield format_sse_event(
            ToolCallStartEvent(
                tool_call_id="c1",
                tool_name="audit_retainage_math",
                node="ForensicAuditSentinel",
            )
        )
        yield format_sse_event(
            ToolCallResultEvent(
                tool_call_id="c1",
                tool_name="audit_retainage_math",
                node="ForensicAuditSentinel",
                success=True,
                result={"net": "50000.00"},
            )
        )
        yield format_sse_event(
            ToolCallResultEvent(
                tool_call_id="c2",
                tool_name="dispatch_decision_notification",
                node="EverydayDecisionCardEmitter",
                success=True,
                result={"dispatched_to": ["GENERAL_CONTRACTOR", "OWNER"]},
            )
        )
        yield format_sse_event(StreamEndEvent(reason="completed"))

    consumer = StreamConsumer()
    final_state = await consumer.consume_stream(mock_sse_stream())

    assert final_state.is_running is False
    assert final_state.status_banner == "Starting analysis..."
    assert len(final_state.node_status_lines["ForensicAuditSentinel"]) == 1
    assert final_state.node_status_lines["ForensicAuditSentinel"][0].status == "completed"
    assert len(final_state.toast_notifications) == 1
    assert "GENERAL_CONTRACTOR, OWNER" in final_state.toast_notifications[0]
