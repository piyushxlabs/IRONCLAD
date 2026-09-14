"""Evaluation tests for HITL interrupt checkpointing, resumption, and safety invariants.

Tests the Human-in-the-Loop decision gateway conforming to:
- AGENT_MASTER_PLAN.md Section 9.3 & 10 (Step 18)
- INTERFACE_OBSERVABILITY_SYSTEM.md Section 5
- .agents/rules/code-level-verification-over-model-discretion.md
"""

from decimal import Decimal

import pytest

from src.agents import everyday_decision_card_emitter_node
from src.agents.graph import build_ironclad_graph
from src.errors import ApprovalTimeoutError, StateValidationError
from src.state.checkpointing import MockCheckpointManager
from src.state.schema import (
    ApprovalStatus,
    Discrepancy,
    DrawPacketMeta,
    IroncladState,
    LienChainStatus,
    RuntimeConfig,
)
from src.ui.hitl_resumption import (
    handle_approve_release,
    handle_escalate_legal,
    handle_hold_request_correction,
    submit_decision,
)


async def create_paused_clean_state(
    checkpoint_mgr: MockCheckpointManager,
    session_id: str = "session-eval-clean-001",
) -> tuple[str, IroncladState]:
    """Helper creating a clean audit run paused at the HITL interrupt checkpoint."""
    graph = build_ironclad_graph()
    initial_state = IroncladState(
        draw_packet_meta=DrawPacketMeta(
            project_id="PROJ-EVAL-01",
            subcontractor_id="SUB-EVAL-01",
            draw_number=1,
            source_uris=["docs/simple_packet.pdf"],
        ),
        runtime_config=RuntimeConfig(runtime_mode="mock"),
    )

    paused_state = await graph.execute(
        initial_state=initial_state,
        checkpoint_manager=checkpoint_mgr,
        session_id=session_id,
    )
    return session_id, paused_state


async def create_paused_defect_state(
    checkpoint_mgr: MockCheckpointManager,
    session_id: str = "session-eval-defect-001",
) -> tuple[str, IroncladState]:
    """Helper creating an audit run with a suspect pre-dated notary waiver paused at HITL."""
    session_id, clean_state = await create_paused_clean_state(checkpoint_mgr, session_id)

    # Inject pre-dated notary discrepancy
    state_with_suspect_waiver = clean_state.model_copy(
        update={
            "lien_chain_status": LienChainStatus.SUSPECT_PRE_DATED_NOTARY,
            "flagged_discrepancies": [
                Discrepancy(
                    line_item_id="W-004",
                    discrepancy_type="SUSPECT_PRE_DATED_NOTARY",
                    description="Notary execution date (2026-08-10) precedes check date (2026-09-01).",
                    variance_amount=None,
                )
            ],
        }
    )

    card_updates = await everyday_decision_card_emitter_node(
        state_with_suspect_waiver, dispatch_alert=False
    )
    paused_defect_state = state_with_suspect_waiver.model_copy(
        update={"decision_card_payload": card_updates["decision_card_payload"]}
    )

    await checkpoint_mgr.write_checkpoint(session_id, paused_defect_state)
    return session_id, paused_defect_state


@pytest.mark.asyncio
async def test_hitl_resumption_approve_release_clean_audit() -> None:
    """Scenario 1: Authenticated reviewer approves clean draw release."""
    checkpoint_mgr = MockCheckpointManager()
    session_id, _ = await create_paused_clean_state(checkpoint_mgr, "sess-hitl-app-01")

    resolved_state = await submit_decision(
        checkpoint_id=session_id,
        action="APPROVE_RELEASE",
        reviewer_id="cfo_john_doe",
        notes="All retainage and lien calculations verified by sentinel.",
        checkpoint_manager=checkpoint_mgr,
    )

    assert resolved_state.approval_state is not None
    assert resolved_state.approval_state.action == ApprovalStatus.APPROVE_RELEASE
    assert resolved_state.approval_state.reviewer_id == "cfo_john_doe"
    assert "All retainage" in (resolved_state.approval_state.notes or "")

    # Verify state was saved to checkpoint store
    checkpoint_state = await checkpoint_mgr.read_checkpoint(session_id)
    assert checkpoint_state is not None
    assert checkpoint_state.approval_state is not None
    assert checkpoint_state.approval_state.action == ApprovalStatus.APPROVE_RELEASE


@pytest.mark.asyncio
async def test_hitl_resumption_hold_request_correction_with_notes() -> None:
    """Scenario 2: Reviewer holds release requesting corrected documentation."""
    checkpoint_mgr = MockCheckpointManager()
    session_id, _ = await create_paused_clean_state(checkpoint_mgr, "sess-hitl-hold-01")

    resolved_state = await submit_decision(
        checkpoint_id=session_id,
        action="HOLD_REQUEST_CORRECTION",
        reviewer_id="pm_jane_smith",
        notes="Hold payment pending site architect stored materials confirmation.",
        checkpoint_manager=checkpoint_mgr,
    )

    assert resolved_state.approval_state is not None
    assert resolved_state.approval_state.action == ApprovalStatus.HOLD_REQUEST_CORRECTION
    assert resolved_state.approval_state.reviewer_id == "pm_jane_smith"
    assert "stored materials" in (resolved_state.approval_state.notes or "")


@pytest.mark.asyncio
async def test_hitl_resumption_escalate_legal_with_fraud_findings() -> None:
    """Scenario 3: Reviewer escalates to legal due to pre-dated notary defects."""
    checkpoint_mgr = MockCheckpointManager()
    session_id, paused_state = await create_paused_defect_state(checkpoint_mgr, "sess-hitl-esc-01")

    assert paused_state.decision_card_payload is not None
    assert paused_state.decision_card_payload.recommended_action == "ESCALATE_LEGAL"

    resolved_state = await submit_decision(
        checkpoint_id=session_id,
        action="ESCALATE_LEGAL",
        reviewer_id="legal_counsel_01",
        notes="Pre-dated notary signature detected on final waiver; refer to outside counsel.",
        checkpoint_manager=checkpoint_mgr,
    )

    assert resolved_state.approval_state is not None
    assert resolved_state.approval_state.action == ApprovalStatus.ESCALATE_LEGAL
    assert resolved_state.approval_state.reviewer_id == "legal_counsel_01"


@pytest.mark.asyncio
async def test_hitl_resumption_rejects_unauthorized_action() -> None:
    """Scenario 4: Attempting unapproved actions raises StateValidationError."""
    checkpoint_mgr = MockCheckpointManager()
    session_id, _ = await create_paused_clean_state(checkpoint_mgr, "sess-hitl-invalid-01")

    for invalid_action in ["DENY", "PAY_PARTIAL", "RELEASE_FUNDS", "OVERRIDE_RETAINAGE", ""]:
        with pytest.raises(StateValidationError) as exc_info:
            await submit_decision(
                checkpoint_id=session_id,
                action=invalid_action,
                reviewer_id="auditor_01",
                checkpoint_manager=checkpoint_mgr,
            )
        assert "Invalid HITL action" in str(exc_info.value)


@pytest.mark.asyncio
async def test_hitl_resumption_rejects_tampered_financial_inputs() -> None:
    """Scenario 5: Attempting to modify audited financial figures raises StateValidationError."""
    checkpoint_mgr = MockCheckpointManager()
    session_id, _ = await create_paused_clean_state(checkpoint_mgr, "sess-hitl-tamper-01")

    with pytest.raises(StateValidationError) as exc_info:
        await submit_decision(
            checkpoint_id=session_id,
            action="APPROVE_RELEASE",
            reviewer_id="malicious_actor",
            modified_inputs={"net_recommended_release": Decimal("999999.00")},
            checkpoint_manager=checkpoint_mgr,
        )

    assert "Financial immutability violation" in str(exc_info.value)

    # Verify state remains paused and untouched in checkpoint store
    saved_state = await checkpoint_mgr.read_checkpoint(session_id)
    assert saved_state is not None
    assert saved_state.approval_state is None


@pytest.mark.asyncio
async def test_hitl_resumption_missing_checkpoint_error() -> None:
    """Scenario 6: Non-existent or expired checkpoint ID raises ApprovalTimeoutError."""
    checkpoint_mgr = MockCheckpointManager()
    with pytest.raises(ApprovalTimeoutError) as exc_info:
        await submit_decision(
            checkpoint_id="non-existent-session-id-9999",
            action="APPROVE_RELEASE",
            reviewer_id="reviewer_01",
            checkpoint_manager=checkpoint_mgr,
        )

    assert "not found or session has expired" in str(exc_info.value)


@pytest.mark.asyncio
async def test_hitl_button_helpers() -> None:
    """Scenario 7: Button helper wrappers invoke submit_decision with exact actions."""
    checkpoint_mgr = MockCheckpointManager()

    # 1. Test handle_approve_release
    session_id, _ = await create_paused_clean_state(checkpoint_mgr, "sess-btn-01")
    state_approved = await handle_approve_release(
        checkpoint_id=session_id,
        reviewer_id="btn_reviewer_1",
        notes="Approved via button",
        checkpoint_manager=checkpoint_mgr,
    )
    assert state_approved.approval_state is not None
    assert state_approved.approval_state.action == ApprovalStatus.APPROVE_RELEASE

    # 2. Test handle_hold_request_correction
    session_id_hold, _ = await create_paused_clean_state(checkpoint_mgr, "sess-btn-02")
    state_held = await handle_hold_request_correction(
        checkpoint_id=session_id_hold,
        reviewer_id="btn_reviewer_2",
        notes="Held via button",
        checkpoint_manager=checkpoint_mgr,
    )
    assert state_held.approval_state is not None
    assert state_held.approval_state.action == ApprovalStatus.HOLD_REQUEST_CORRECTION

    # 3. Test handle_escalate_legal
    session_id_esc, _ = await create_paused_clean_state(checkpoint_mgr, "sess-btn-03")
    state_escalated = await handle_escalate_legal(
        checkpoint_id=session_id_esc,
        reviewer_id="btn_reviewer_3",
        notes="Escalated via button",
        checkpoint_manager=checkpoint_mgr,
    )
    assert state_escalated.approval_state is not None
    assert state_escalated.approval_state.action == ApprovalStatus.ESCALATE_LEGAL
