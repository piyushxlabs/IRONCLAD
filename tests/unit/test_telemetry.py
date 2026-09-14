"""Unit tests for OpenTelemetry tracing, GenAI semantic conventions, and Langfuse annotations."""

from unittest.mock import MagicMock

import pytest

from src.agents.graph import build_ironclad_graph
from src.state.schema import (
    ApprovalDecision,
    ApprovalStatus,
    Discrepancy,
    DrawPacketMeta,
    IroncladState,
    LienChainStatus,
    RuntimeConfig,
)
from src.telemetry.feedback_annotations import record_hitl_feedback
from src.telemetry.tracing import (
    DRAW_NUMBER_ATTR,
    GEN_AI_OPERATION_NAME,
    GEN_AI_PROVIDER_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
    NODE_NAME_ATTR,
    PROJECT_ID_ATTR,
    SESSION_ID_ATTR,
    SUBCONTRACTOR_ID_ATTR,
    TOOL_NAME_ATTR,
    get_telemetry_manager,
    trace_agent_invocation,
    trace_audit_run,
    trace_model_inference,
    trace_tool_execution,
)


@pytest.fixture(autouse=True)
def clean_telemetry_spans() -> None:
    """Ensure in-memory telemetry exporter is clear before each test."""
    manager = get_telemetry_manager()
    manager.clear_exported_spans()


def test_telemetry_manager_singleton_and_in_memory_export() -> None:
    """Verify TelemetryManager singleton behavior and in-memory span capture."""
    manager = get_telemetry_manager()
    tracer = manager.get_tracer("test.tracer")
    assert tracer is not None

    with tracer.start_as_current_span("test_span", attributes={"test.attr": "value"}):
        pass

    spans = manager.get_exported_spans()
    assert len(spans) == 1
    assert spans[0].name == "test_span"
    assert spans[0].attributes["test.attr"] == "value"

    hierarchy = manager.get_span_hierarchy()
    assert len(hierarchy) == 1
    assert hierarchy[0]["name"] == "test_span"
    assert hierarchy[0]["attributes"]["test.attr"] == "value"


def test_trace_audit_run_root_span() -> None:
    """Verify trace_audit_run creates a root span with required GenAI attributes."""
    manager = get_telemetry_manager()
    session_id = "sess-proj-101-d1"

    with trace_audit_run(
        session_id=session_id,
        project_id="PROJ-101",
        subcontractor_id="SUB-404",
        draw_number=3,
    ) as span:
        assert span is not None

    spans = manager.get_exported_spans()
    assert len(spans) == 1
    root = spans[0]
    assert root.name == f"audit_run:{session_id}"
    assert root.attributes[GEN_AI_OPERATION_NAME] == "audit_run"
    assert root.attributes[SESSION_ID_ATTR] == session_id
    assert root.attributes[PROJECT_ID_ATTR] == "PROJ-101"
    assert root.attributes[SUBCONTRACTOR_ID_ATTR] == "SUB-404"
    assert root.attributes[DRAW_NUMBER_ATTR] == 3


@pytest.mark.asyncio
async def test_trace_agent_invocation_node_span() -> None:
    """Verify trace_agent_invocation creates invoke_agent GenAI semantic spans."""
    manager = get_telemetry_manager()
    agent_name = "ForensicAuditSentinel"
    session_id = "sess-node-test"

    async with trace_agent_invocation(agent_name=agent_name, session_id=session_id) as span:
        assert span is not None

    spans = manager.get_exported_spans()
    assert len(spans) == 1
    node_span = spans[0]
    assert node_span.name == f"invoke_agent:{agent_name}"
    assert node_span.attributes[GEN_AI_OPERATION_NAME] == "invoke_agent"
    assert node_span.attributes[NODE_NAME_ATTR] == agent_name
    assert node_span.attributes[SESSION_ID_ATTR] == session_id
    assert GEN_AI_PROVIDER_NAME in node_span.attributes


def test_trace_tool_execution_and_privacy_digest() -> None:
    """Verify trace_tool_execution captures tool duration and sanitizes inputs into events."""
    manager = get_telemetry_manager()
    tool_name = "audit_retainage_math"

    with trace_tool_execution(
        tool_name=tool_name,
        input_digest={"contract_retainage_pct": "0.10", "current_billed": "50000.00"},
    ) as span:
        assert span is not None

    spans = manager.get_exported_spans()
    assert len(spans) == 1
    tool_span = spans[0]
    assert tool_span.name == f"execute_tool:{tool_name}"
    assert tool_span.attributes[GEN_AI_OPERATION_NAME] == "execute_tool"
    assert tool_span.attributes[TOOL_NAME_ATTR] == tool_name
    assert "tool.duration_ms" in tool_span.attributes

    # Privacy verification: Input summary is stored in events, not root span attributes
    events = tool_span.events
    assert len(events) == 1
    assert events[0].name == "tool_input_digest"
    assert events[0].attributes["input.contract_retainage_pct"] == "0.10"


def test_trace_model_inference_span() -> None:
    """Verify trace_model_inference captures model parameters and token counts."""
    manager = get_telemetry_manager()

    with trace_model_inference(
        model_id="anthropic.claude-3-5-sonnet",
        provider_name="aws.bedrock",
        input_tokens=1200,
        output_tokens=350,
    ):
        pass

    spans = manager.get_exported_spans()
    assert len(spans) == 1
    inf_span = spans[0]
    assert inf_span.name == "inference:anthropic.claude-3-5-sonnet"
    assert inf_span.attributes[GEN_AI_OPERATION_NAME] == "inference"
    assert inf_span.attributes[GEN_AI_PROVIDER_NAME] == "aws.bedrock"
    assert inf_span.attributes[GEN_AI_REQUEST_MODEL] == "anthropic.claude-3-5-sonnet"
    assert inf_span.attributes[GEN_AI_USAGE_INPUT_TOKENS] == 1200
    assert inf_span.attributes[GEN_AI_USAGE_OUTPUT_TOKENS] == 350


@pytest.mark.asyncio
async def test_trace_span_hierarchy() -> None:
    """Verify 3-level hierarchy: trace -> invoke_agent -> execute_tool / inference."""
    manager = get_telemetry_manager()
    session_id = "sess-hierarchy-test"

    with trace_audit_run(session_id=session_id):
        async with trace_agent_invocation(agent_name="ForensicAuditSentinel", session_id=session_id):
            with trace_tool_execution(tool_name="extract_draw_packet_metadata"):
                pass
            with trace_model_inference(model_id="gemini-3.8-flash", provider_name="google.genai"):
                pass

    hierarchy = manager.get_span_hierarchy()
    assert len(hierarchy) == 4

    # The order of export is innermost to outermost
    tool_span = next(s for s in hierarchy if s["name"].startswith("execute_tool:"))
    inf_span = next(s for s in hierarchy if s["name"].startswith("inference:"))
    node_span = next(s for s in hierarchy if s["name"].startswith("invoke_agent:"))
    root_span = next(s for s in hierarchy if s["name"].startswith("audit_run:"))

    assert tool_span["parent_id"] == node_span["span_id"]
    assert inf_span["parent_id"] == node_span["span_id"]
    assert node_span["parent_id"] == root_span["span_id"]
    assert root_span["parent_id"] is None
    assert all(s["trace_id"] == root_span["trace_id"] for s in hierarchy)


def test_record_hitl_feedback_approved() -> None:
    """Verify record_hitl_feedback records categorical scores for APPROVE_RELEASE."""
    mock_langfuse = MagicMock()

    record = record_hitl_feedback(
        session_id="sess-hitl-approve",
        action="APPROVE_RELEASE",
        reason="Clean audit with 10% retainage verified",
        langfuse_client=mock_langfuse,
    )

    assert record.session_id == "sess-hitl-approve"
    assert record.action == "APPROVE_RELEASE"
    assert record.categorical_decision == "approve_release"
    assert record.human_override_of_clean_audit is False
    assert record.langfuse_score_recorded is True

    mock_langfuse.create_score.assert_called_once_with(
        name="reviewer_decision",
        value="approve_release",
        trace_id="sess-hitl-approve",
        session_id="sess-hitl-approve",
        data_type="CATEGORICAL",
        comment="Clean audit with 10% retainage verified",
        metadata={
            "raw_action": "APPROVE_RELEASE",
            "clean_audit_override": False,
        },
    )


def test_record_hitl_feedback_human_override_detection() -> None:
    """Verify detection of human overrides on 100% clean audits."""
    mock_langfuse = MagicMock()

    # Clean audit state: 0 discrepancies and valid lien chain
    clean_state = IroncladState(
        draw_packet_meta=DrawPacketMeta(
            project_id="PROJ-CLEAN",
            subcontractor_id="SUB-1",
            draw_number=1,
            source_uris=["docs/draw_1.pdf"],
        ),
        flagged_discrepancies=[],
        lien_chain_status=LienChainStatus.VALID,
    )

    record = record_hitl_feedback(
        session_id="sess-hitl-override",
        action="HOLD_REQUEST_CORRECTION",
        reason="Holding for owner verification of stored materials",
        state=clean_state,
        langfuse_client=mock_langfuse,
    )

    assert record.action == "HOLD_REQUEST_CORRECTION"
    assert record.categorical_decision == "hold_request_correction"
    assert record.human_override_of_clean_audit is True
    assert record.langfuse_score_recorded is True

    # Check that both categorical decision and boolean override scores were emitted
    assert mock_langfuse.create_score.call_count == 2
    calls = mock_langfuse.create_score.call_args_list

    # Score 1: reviewer_decision
    assert calls[0].kwargs["name"] == "reviewer_decision"
    assert calls[0].kwargs["value"] == "hold_request_correction"

    # Score 2: human_override_of_clean_audit
    assert calls[1].kwargs["name"] == "human_override_of_clean_audit"
    assert calls[1].kwargs["value"] == "true"
    assert calls[1].kwargs["data_type"] == "BOOLEAN"


def test_record_hitl_feedback_with_existing_discrepancy() -> None:
    """Verify human_override_of_clean_audit is False when discrepancies were already present."""
    mock_langfuse = MagicMock()

    state_with_error = IroncladState(
        draw_packet_meta=DrawPacketMeta(
            project_id="PROJ-DEFECT",
            subcontractor_id="SUB-2",
            draw_number=2,
            source_uris=["docs/draw_2.pdf"],
        ),
        flagged_discrepancies=[
            Discrepancy(
                line_item_id="W-004",
                discrepancy_type="PRE_DATED_NOTARY",
                description="Pre-dated notary detected",
            )
        ],
        lien_chain_status=LienChainStatus.SUSPECT_PRE_DATED_NOTARY,
    )

    record = record_hitl_feedback(
        session_id="sess-hitl-defect",
        action="ESCALATE_LEGAL",
        reason="Pre-dated notary fraud identified by sentinel",
        state=state_with_error,
        langfuse_client=mock_langfuse,
    )

    assert record.action == "ESCALATE_LEGAL"
    assert record.human_override_of_clean_audit is False
    assert mock_langfuse.create_score.call_count == 1


@pytest.mark.asyncio
async def test_end_to_end_graph_execution_telemetry_integration() -> None:
    """Verify full graph execution populates telemetry spans and records HITL feedback."""
    manager = get_telemetry_manager()
    manager.clear_exported_spans()

    graph = build_ironclad_graph()
    initial_state = IroncladState(
        draw_packet_meta=DrawPacketMeta(
            project_id="PROJ-TEL-001",
            subcontractor_id="SUB-TEL-001",
            draw_number=1,
            source_uris=["docs/simple_packet.pdf"],
        ),
        runtime_config=RuntimeConfig(runtime_mode="mock"),
    )
    session_id = "session_tel_integration_001"

    # Step 1: Execute graph through to HITL interrupt
    interrupted_state = await graph.execute(
        initial_state=initial_state,
        session_id=session_id,
    )

    assert interrupted_state.decision_card_payload is not None

    spans = manager.get_exported_spans()
    span_names = [s.name for s in spans]

    # Verify root span and node spans exist
    assert f"audit_run:{session_id}" in span_names
    assert "invoke_agent:ForensicAuditSentinel" in span_names
    assert "invoke_agent:FairPayStatutoryGuardian" in span_names
    assert "invoke_agent:EverydayDecisionCardEmitter" in span_names

    # Step 2: Resume HITL with human decision
    decision = ApprovalDecision(
        action=ApprovalStatus.APPROVE_RELEASE,
        notes="Telemetry audit verified",
        reviewer_id="human_cfo_01",
    )

    terminal_state = await graph.resume_hitl(
        current_state=interrupted_state,
        decision=decision,
        session_id=session_id,
    )

    assert terminal_state.approval_state is not None
    assert terminal_state.approval_state.action == ApprovalStatus.APPROVE_RELEASE
