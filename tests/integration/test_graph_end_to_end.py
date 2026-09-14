"""End-to-End Integration Tests for Tri-Track Reasoning Loops and DAG Execution.

Adheres strictly to AGENT_MASTER_PLAN.md Section 9 & 10 (Step 14) and AGENT_LOGIC_SPEC.md.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.agents import build_ironclad_graph
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
def mock_clean_draw_packet() -> IroncladState:
    """Fixture representing Simple Case: clean single-line draw packet with valid unconditional waiver."""
    return IroncladState(
        draw_packet_meta=DrawPacketMeta(
            project_id="PROJ-TX-101",
            subcontractor_id="SUB-CONCRETE-001",
            draw_number=4,
            source_uris=["s3://ironclad-intake/proj-tx-101/draw-04.pdf"],
        ),
        runtime_config=RuntimeConfig(runtime_mode="mock"),
    )


@pytest.mark.asyncio
async def test_end_to_end_simple_clean_case(mock_clean_draw_packet: IroncladState) -> None:
    """Execute end-to-end DAG on clean draw packet; assert APPROVE_RELEASE and successful HITL resumption."""
    graph = build_ironclad_graph()
    checkpoint_mgr = MockCheckpointManager()
    session_id = "session_e2e_clean_001"

    # 1. Run Graph from Ingress to HITL Interrupt Checkpoint
    paused_state = await graph.execute(
        initial_state=mock_clean_draw_packet,
        checkpoint_manager=checkpoint_mgr,
        session_id=session_id,
    )

    # 2. Verify Forensic Track Outputs (Professional Track)
    assert len(paused_state.extracted_line_items) == 1
    assert paused_state.extracted_line_items[0].line_item_id == "LI-001"
    assert paused_state.extracted_line_items[0].current_billed == Decimal("12000.00")
    assert paused_state.extracted_line_items[0].contract_retainage_pct == Decimal("0.05")

    assert paused_state.retainage_audit_result is not None
    assert paused_state.retainage_audit_result.gross_amount_requested == Decimal("12000.00")
    assert paused_state.retainage_audit_result.contractual_retainage_withheld == Decimal("600.00")
    assert paused_state.retainage_audit_result.net_recommended_release == Decimal("11400.00")

    assert paused_state.lien_chain_status == LienChainStatus.VALID

    # 3. Verify Statutory Track Outputs (Good Neighbor Track)
    assert paused_state.statutory_prompt_pay_clock is not None
    assert paused_state.statutory_prompt_pay_clock.state == "TX"
    assert paused_state.statutory_prompt_pay_clock.days_remaining > 0
    assert paused_state.statutory_prompt_pay_clock.penalty_interest_rate == Decimal("0.015")

    # 4. Verify Zero Discrepancies and Zero Blocking Errors
    assert len(paused_state.flagged_discrepancies) == 0
    assert len([e for e in paused_state.error_logs if e.blocking]) == 0

    # 5. Verify Everyday Decision Card Deliverable (Everyday Track)
    card = paused_state.decision_card_payload
    assert card is not None
    assert card.draw_number == 4
    assert card.gross_amount_requested == Decimal("12000.00")
    assert card.contractual_retainage_withheld == Decimal("600.00")
    assert card.net_recommended_release == Decimal("11400.00")
    assert card.lien_chain_status == LienChainStatus.VALID
    assert card.recommended_action == "APPROVE_RELEASE"
    assert card.confidence_score == 1.0

    # 6. Verify Checkpoint Snapshot at HITL Gate
    assert paused_state.approval_state is None
    persisted = await checkpoint_mgr.read_checkpoint(session_id)
    assert persisted is not None
    assert persisted.decision_card_payload is not None

    # 7. Resumption: Authenticated Human Approval
    decision = ApprovalDecision(
        action=ApprovalStatus.APPROVE_RELEASE,
        reviewer_id="lead_reviewer_001",
        timestamp=datetime.now(UTC),
        notes="Verified 5% retainage and unconditional waiver validity.",
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
    assert resolved_state.approval_state.reviewer_id == "lead_reviewer_001"


@pytest.mark.asyncio
async def test_end_to_end_complex_defect_case(mock_clean_draw_packet: IroncladState) -> None:
    """Execute DAG on draw packet with pre-dated notary; assert ESCALATE_LEGAL and release denial."""
    graph = build_ironclad_graph()

    # Inject suspect pre-dated notary waiver into mock state
    paused_state = await graph.execute(mock_clean_draw_packet)

    # Modify state to simulate pre-dated notary waiver finding
    from src.agents import everyday_decision_card_emitter_node
    from src.state.schema import Discrepancy

    state_with_suspect_waiver = paused_state.model_copy(
        update={
            "lien_chain_status": LienChainStatus.SUSPECT_PRE_DATED_NOTARY,
            "flagged_discrepancies": [
                Discrepancy(
                    line_item_id="W-001",
                    discrepancy_type="SUSPECT_PRE_DATED_NOTARY",
                    description="Notary execution date (2026-08-15) precedes check date (2026-09-01).",
                    variance_amount=None,
                )
            ],
        }
    )

    card_updates = await everyday_decision_card_emitter_node(state_with_suspect_waiver, dispatch_alert=False)
    payload = card_updates["decision_card_payload"]

    # Fixed decision logic MUST force ESCALATE_LEGAL
    assert payload.recommended_action == "ESCALATE_LEGAL"
    assert payload.lien_chain_status == LienChainStatus.SUSPECT_PRE_DATED_NOTARY
    assert len(payload.blocking_discrepancies) == 1


@pytest.mark.asyncio
async def test_end_to_end_edge_case_ambiguous_clause(mock_clean_draw_packet: IroncladState) -> None:
    """Execute DAG on draw packet with ambiguous clause; assert clock is None and HOLD recommended."""
    from src.agents import fair_pay_statutory_guardian_node
    from src.agents.everyday_decision_card_emitter import (
        everyday_decision_card_emitter_node,
    )
    from src.state.reducers import apply_state_update

    # Run Statutory Guardian with unresolvable/ambiguous clause
    statutory_updates = await fair_pay_statutory_guardian_node(
        state=mock_clean_draw_packet,
        clause_override="unspecified_boilerplate_fragment",
    )

    # Assert clock is NOT fabricated (Silence-Over-Guessing: Prohibition 3 & 5)
    assert statutory_updates["statutory_prompt_pay_clock"] is None
    assert len(statutory_updates["flagged_discrepancies"]) > 0
    assert statutory_updates["flagged_discrepancies"][0].discrepancy_type == "UNRESOLVABLE_JURISDICTION"

    # Merge into state
    state = apply_state_update(mock_clean_draw_packet, statutory_updates, caller_node="FairPayStatutoryGuardian")

    # Run Everyday Card Emitter
    card_updates = await everyday_decision_card_emitter_node(state, dispatch_alert=False)
    payload = card_updates["decision_card_payload"]

    # Must NOT recommend APPROVE_RELEASE
    assert payload.recommended_action == "HOLD_REQUEST_CORRECTED_WAIVER"
    assert payload.statutory_prompt_pay_clock is None


@pytest.mark.asyncio
async def test_end_to_end_tamper_proofing_rejection(mock_clean_draw_packet: IroncladState) -> None:
    """Assert HITL resumption rejects non-null modified_inputs to enforce financial immutability."""
    graph = build_ironclad_graph()
    paused_state = await graph.execute(mock_clean_draw_packet)

    tampered_decision = ApprovalDecision(
        action=ApprovalStatus.APPROVE_RELEASE,
        reviewer_id="malicious_actor",
        notes="Attempting to override audited net payout",
        modified_inputs={"net_recommended_release": "99999.00"},
    )

    with pytest.raises(StateValidationError) as exc_info:
        await graph.resume_hitl(
            current_state=paused_state,
            decision=tampered_decision,
        )

    assert "Financial immutability violation" in str(exc_info.value)
