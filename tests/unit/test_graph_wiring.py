"""Unit tests for Tri-Track Orchestration DAG Wiring and Execution."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.agents import (
    build_ironclad_graph,
    everyday_decision_card_emitter_node,
    fair_pay_statutory_guardian_node,
    forensic_audit_sentinel_node,
    ingress_node,
)
from src.errors import StateValidationError
from src.state.checkpointing import MockCheckpointManager
from src.state.schema import (
    ApprovalDecision,
    ApprovalStatus,
    DrawPacketMeta,
    IroncladState,
    LienChainStatus,
    RuntimeConfig,
)


@pytest.fixture
def clean_initial_state() -> IroncladState:
    """Fixture providing clean initial state container."""
    return IroncladState(
        draw_packet_meta=DrawPacketMeta(
            project_id="PROJ-TX-101",
            subcontractor_id="SUB-CONCRETE-001",
            draw_number=4,
            source_uris=["s3://ironclad-intake/proj-tx-101/draw-04.pdf"],
        ),
        runtime_config=RuntimeConfig(runtime_mode="mock"),
    )


def test_compiled_graph_structure() -> None:
    """Assert graph contains exactly the 6 mandated nodes and documented edges."""
    graph = build_ironclad_graph()

    expected_nodes = {
        "ingress",
        "forensic_audit_sentinel",
        "fair_pay_statutory_guardian",
        "everyday_decision_card_emitter",
        "hitl_interrupt",
        "terminal",
    }
    assert set(graph.nodes.keys()) == expected_nodes
    assert graph.entry_point == "ingress"
    assert graph.interrupt_nodes == {"hitl_interrupt"}

    # Validate downstream edges
    assert set(graph.get_downstream_nodes("ingress")) == {
        "forensic_audit_sentinel",
        "fair_pay_statutory_guardian",
    }
    assert set(graph.get_downstream_nodes("forensic_audit_sentinel")) == {
        "everyday_decision_card_emitter"
    }
    assert set(graph.get_downstream_nodes("fair_pay_statutory_guardian")) == {
        "everyday_decision_card_emitter"
    }
    assert set(graph.get_downstream_nodes("everyday_decision_card_emitter")) == {
        "hitl_interrupt"
    }
    assert set(graph.get_downstream_nodes("hitl_interrupt")) == {"terminal"}
    assert graph.get_downstream_nodes("terminal") == []


@pytest.mark.asyncio
async def test_ingress_node_path_traversal_rejection() -> None:
    """Assert ingress node blocks path traversal in document URIs."""
    malicious_state = IroncladState(
        draw_packet_meta=DrawPacketMeta(
            project_id="PROJ-001",
            subcontractor_id="SUB-001",
            draw_number=1,
            source_uris=["s3://ironclad-intake/../../../etc/passwd"],
        ),
        runtime_config=RuntimeConfig(runtime_mode="mock"),
    )

    updates = await ingress_node(malicious_state)
    assert "error_logs" in updates
    assert len(updates["error_logs"]) > 0
    assert updates["error_logs"][0].blocking is True
    assert "Path traversal" in updates["error_logs"][0].message


@pytest.mark.asyncio
async def test_forensic_audit_sentinel_execution(clean_initial_state: IroncladState) -> None:
    """Assert ForensicAuditSentinel populates line items, retainage math, and lien status."""
    updates = await forensic_audit_sentinel_node(clean_initial_state)

    assert "extracted_line_items" in updates
    assert len(updates["extracted_line_items"]) > 0
    assert "retainage_audit_result" in updates
    assert updates["retainage_audit_result"] is not None
    assert updates["retainage_audit_result"].gross_amount_requested == Decimal("12000.00")
    assert updates["retainage_audit_result"].contractual_retainage_withheld == Decimal("600.00")
    assert updates["retainage_audit_result"].net_recommended_release == Decimal("11400.00")
    assert "lien_chain_status" in updates
    assert updates["lien_chain_status"] == LienChainStatus.VALID


@pytest.mark.asyncio
async def test_fair_pay_statutory_guardian_execution(clean_initial_state: IroncladState) -> None:
    """Assert FairPayStatutoryGuardian populates statutory clock without suppression."""
    updates = await fair_pay_statutory_guardian_node(clean_initial_state)

    assert "statutory_prompt_pay_clock" in updates
    clock = updates["statutory_prompt_pay_clock"]
    assert clock is not None
    assert clock.state == "TX"
    assert clock.days_remaining > 0
    assert clock.penalty_interest_rate == Decimal("0.015")


@pytest.mark.asyncio
async def test_graph_full_execution_clean_packet(clean_initial_state: IroncladState) -> None:
    """Assert full DAG execution runs ingress, parallel fan-out, fan-in, and pauses at HITL."""
    graph = build_ironclad_graph()
    checkpoint_mgr = MockCheckpointManager()
    session_id = "session_test_001"

    paused_state = await graph.execute(
        initial_state=clean_initial_state,
        checkpoint_manager=checkpoint_mgr,
        session_id=session_id,
    )

    # 1. Forensic results populated
    assert len(paused_state.extracted_line_items) > 0
    assert paused_state.retainage_audit_result is not None
    assert paused_state.lien_chain_status == LienChainStatus.VALID

    # 2. Statutory clock populated
    assert paused_state.statutory_prompt_pay_clock is not None
    assert paused_state.statutory_prompt_pay_clock.state == "TX"

    # 3. Everyday Decision Card payload generated
    assert paused_state.decision_card_payload is not None
    assert paused_state.decision_card_payload.recommended_action == "APPROVE_RELEASE"
    assert paused_state.decision_card_payload.gross_amount_requested == Decimal("12000.00")
    assert paused_state.decision_card_payload.net_recommended_release == Decimal("11400.00")

    # 4. Checkpoint written at HITL gate
    persisted = await checkpoint_mgr.read_checkpoint(session_id)
    assert persisted is not None
    assert persisted.decision_card_payload is not None
    assert persisted.approval_state is None


@pytest.mark.asyncio
async def test_everyday_emitter_decision_logic_with_discrepancies(
    clean_initial_state: IroncladState,
) -> None:
    """Assert everyday emitter forces HOLD when discrepancies exist."""
    graph = build_ironclad_graph()

    # Execute graph
    state = await graph.execute(clean_initial_state)

    # Modify state to include a discrepancy
    from src.state.schema import Discrepancy

    state_with_discrepancy = state.model_copy(
        update={
            "flagged_discrepancies": [
                Discrepancy(
                    line_item_id="LI-001",
                    discrepancy_type="MISSING_RETAINAGE_CLAUSE",
                    description="Retainage clause missing in G702 continuation",
                    variance_amount=None,
                )
            ]
        }
    )

    updates = await everyday_decision_card_emitter_node(state_with_discrepancy, dispatch_alert=False)
    payload = updates["decision_card_payload"]
    assert payload.recommended_action == "HOLD_REQUEST_CORRECTED_WAIVER"


@pytest.mark.asyncio
async def test_everyday_emitter_decision_logic_with_pre_dated_notary(
    clean_initial_state: IroncladState,
) -> None:
    """Assert everyday emitter forces ESCALATE_LEGAL when pre-dated notary detected."""
    state = await build_ironclad_graph().execute(clean_initial_state)

    state_suspect = state.model_copy(
        update={"lien_chain_status": LienChainStatus.SUSPECT_PRE_DATED_NOTARY}
    )

    updates = await everyday_decision_card_emitter_node(state_suspect, dispatch_alert=False)
    payload = updates["decision_card_payload"]
    assert payload.recommended_action == "ESCALATE_LEGAL"


@pytest.mark.asyncio
async def test_graph_hitl_resumption_success(clean_initial_state: IroncladState) -> None:
    """Assert graph resumes from HITL gate to terminal state upon human sign-off."""
    graph = build_ironclad_graph()
    checkpoint_mgr = MockCheckpointManager()
    session_id = "session_hitl_test"

    paused_state = await graph.execute(
        initial_state=clean_initial_state,
        checkpoint_manager=checkpoint_mgr,
        session_id=session_id,
    )
    assert paused_state.approval_state is None

    # Authenticated Human Action
    decision = ApprovalDecision(
        action=ApprovalStatus.APPROVE_RELEASE,
        reviewer_id="lead_counsel_007",
        timestamp=datetime.now(UTC),
        notes="All retainage calculations and lien waivers verified.",
        modified_inputs=None,
    )

    resolved_state = await graph.resume_hitl(
        current_state=paused_state,
        decision=decision,
        checkpoint_manager=checkpoint_mgr,
        session_id=session_id,
    )

    assert resolved_state.approval_state is not None
    assert resolved_state.approval_state.action == ApprovalStatus.APPROVE_RELEASE
    assert resolved_state.approval_state.reviewer_id == "lead_counsel_007"


@pytest.mark.asyncio
async def test_graph_hitl_resumption_immutability_rejection(
    clean_initial_state: IroncladState,
) -> None:
    """Assert resumption rejects attempts to modify financial figures during sign-off."""
    graph = build_ironclad_graph()
    paused_state = await graph.execute(initial_state=clean_initial_state)

    # Attempt to tamper with audited numbers via modified_inputs
    tampered_decision = ApprovalDecision(
        action=ApprovalStatus.APPROVE_RELEASE,
        reviewer_id="reviewer_bad",
        notes="Attempting to override retainage percentage manually",
        modified_inputs={"contract_retainage_pct": 0.10},
    )

    with pytest.raises(StateValidationError) as excinfo:
        await graph.resume_hitl(
            current_state=paused_state,
            decision=tampered_decision,
        )

    assert "Financial immutability violation" in str(excinfo.value)
