"""Unit tests for IroncladState Reducers and Single-Writer Boundary Enforcement."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.errors import StateValidationError
from src.state.reducers import (
    EVERYDAY_WRITER,
    FORENSIC_WRITER,
    HITL_WRITER,
    STATUTORY_WRITER,
    apply_state_update,
)
from src.state.schema import (
    ApprovalDecision,
    ApprovalStatus,
    DecisionCardPayload,
    Discrepancy,
    DrawPacketMeta,
    IroncladState,
    LienChainStatus,
    LineItem,
    RetainageAuditResult,
    StatutoryClock,
    ToolArtifact,
)


@pytest.fixture
def initial_state() -> IroncladState:
    """Fixture providing a valid initialized IroncladState."""
    meta = DrawPacketMeta(
        project_id="PROJ-789",
        subcontractor_id="SUB-042",
        draw_number=3,
        source_uris=["s3://ironclad-test/g702.pdf", "s3://ironclad-test/waiver.pdf"],
    )
    return IroncladState(draw_packet_meta=meta)


def test_immutable_draw_packet_meta_rejection(initial_state: IroncladState) -> None:
    """Verify that attempting to mutate draw_packet_meta raises StateValidationError."""
    new_meta = DrawPacketMeta(
        project_id="PROJ-OVERWRITE",
        subcontractor_id="SUB-042",
        draw_number=4,
        source_uris=["s3://ironclad-test/tampered.pdf"],
    )
    with pytest.raises(StateValidationError):
        apply_state_update(initial_state, {"draw_packet_meta": new_meta}, caller_node=FORENSIC_WRITER)


def test_forensic_writer_single_writer_enforcement(initial_state: IroncladState) -> None:
    """Verify ForensicAuditSentinel can write line items and retainage audit, while others are rejected."""
    line_item = LineItem(
        line_item_id="LI-001",
        description="HVAC Rough-in",
        contract_retainage_pct=Decimal("0.10"),
        current_billed=Decimal("50000.00"),
        stored_materials=Decimal("0.00"),
        prior_payments=Decimal("0.00"),
    )
    audit_res = RetainageAuditResult(
        gross_amount_requested=Decimal("50000.00"),
        contractual_retainage_withheld=Decimal("5000.00"),
        net_recommended_release=Decimal("45000.00"),
        calculation_trace=["50000 * 0.10 = 5000 retainage"],
    )

    # Valid write by ForensicAuditSentinel
    updated = apply_state_update(
        initial_state,
        {
            "extracted_line_items": [line_item],
            "retainage_audit_result": audit_res,
            "lien_chain_status": LienChainStatus.VALID,
        },
        caller_node=FORENSIC_WRITER,
    )
    assert len(updated.extracted_line_items) == 1
    assert updated.retainage_audit_result.net_recommended_release == Decimal("45000.00")
    assert updated.lien_chain_status == LienChainStatus.VALID

    # Unauthorized write attempt by FairPayStatutoryGuardian rejected
    with pytest.raises(StateValidationError):
        apply_state_update(
            initial_state,
            {"extracted_line_items": [line_item]},
            caller_node=STATUTORY_WRITER,
        )

    # Unauthorized write attempt by EverydayDecisionCardEmitter rejected
    with pytest.raises(StateValidationError):
        apply_state_update(
            initial_state,
            {"retainage_audit_result": audit_res},
            caller_node=EVERYDAY_WRITER,
        )


def test_statutory_writer_single_writer_enforcement(initial_state: IroncladState) -> None:
    """Verify FairPayStatutoryGuardian can write statutory prompt pay clock."""
    clock = StatutoryClock(
        state="TX",
        days_remaining=14,
        deadline_timestamp=datetime(2026, 10, 1, 0, 0, tzinfo=UTC),
        penalty_interest_rate=Decimal("0.015"),
        statute_reference="Tex. Prop. Code § 28.002",
    )

    # Authorized write
    updated = apply_state_update(
        initial_state,
        {"statutory_prompt_pay_clock": clock},
        caller_node=STATUTORY_WRITER,
    )
    assert updated.statutory_prompt_pay_clock.days_remaining == 14

    # Unauthorized write by ForensicAuditSentinel
    with pytest.raises(StateValidationError):
        apply_state_update(
            initial_state,
            {"statutory_prompt_pay_clock": clock},
            caller_node=FORENSIC_WRITER,
        )


def test_append_only_flagged_discrepancies(initial_state: IroncladState) -> None:
    """Verify flagged_discrepancies accumulates entries without dropping prior ones."""
    d1 = Discrepancy(
        line_item_id="LI-001",
        discrepancy_type="RETAINAGE_MATH_MISMATCH",
        description="Invoice claimed 5% retainage but contract requires 10%",
        variance_amount=Decimal("2500.00"),
    )
    d2 = Discrepancy(
        line_item_id="W-002",
        discrepancy_type="PRE_DATED_NOTARY",
        description="Waiver notary date precedes period through date",
        variance_amount=None,
    )

    # Step 1: Forensic node appends discrepancy
    s1 = apply_state_update(initial_state, {"flagged_discrepancies": [d1]}, caller_node=FORENSIC_WRITER)
    assert len(s1.flagged_discrepancies) == 1

    # Step 2: Statutory node appends second discrepancy
    s2 = apply_state_update(s1, {"flagged_discrepancies": [d2]}, caller_node=STATUTORY_WRITER)
    assert len(s2.flagged_discrepancies) == 2
    assert s2.flagged_discrepancies[0].discrepancy_type == "RETAINAGE_MATH_MISMATCH"
    assert s2.flagged_discrepancies[1].discrepancy_type == "PRE_DATED_NOTARY"


def test_everyday_writer_decision_card_payload(initial_state: IroncladState) -> None:
    """Verify EverydayDecisionCardEmitter can write decision_card_payload."""
    payload = DecisionCardPayload(
        draw_number=3,
        project_name="Metro Station B",
        subcontractor_trade="HVAC",
        gross_amount_requested=Decimal("50000.00"),
        contractual_retainage_withheld=Decimal("5000.00"),
        net_recommended_release=Decimal("45000.00"),
        lien_chain_status=LienChainStatus.VALID,
        recommended_action="APPROVE_RELEASE",
        blocking_discrepancies=[],
    )

    # Authorized write
    updated = apply_state_update(
        initial_state,
        {"decision_card_payload": payload},
        caller_node=EVERYDAY_WRITER,
    )
    assert updated.decision_card_payload.recommended_action == "APPROVE_RELEASE"

    # Unauthorized write by ForensicAuditSentinel
    with pytest.raises(StateValidationError):
        apply_state_update(
            initial_state,
            {"decision_card_payload": payload},
            caller_node=FORENSIC_WRITER,
        )


def test_hitl_writer_approval_state(initial_state: IroncladState) -> None:
    """Verify approval_state is only writable by HITLInterruptHandler."""
    decision = ApprovalDecision(
        action=ApprovalStatus.APPROVE_RELEASE,
        reviewer_id="lead_compliance_officer_101",
        notes="All waivers verified and retainage matched contract.",
    )

    # Authorized write by HITLInterruptHandler
    updated = apply_state_update(
        initial_state,
        {"approval_state": decision},
        caller_node=HITL_WRITER,
    )
    assert updated.approval_state.action == ApprovalStatus.APPROVE_RELEASE

    # Unauthorized write by EverydayDecisionCardEmitter
    with pytest.raises(StateValidationError):
        apply_state_update(
            initial_state,
            {"approval_state": decision},
            caller_node=EVERYDAY_WRITER,
        )


def test_merge_by_key_tool_artifacts(initial_state: IroncladState) -> None:
    """Verify tool_artifacts merges records by tool_call_id."""
    art1 = ToolArtifact(
        tool_call_id="call_ocr_001",
        tool_name="extract_draw_packet_metadata",
        output={"pages_processed": 2},
    )
    art2 = ToolArtifact(
        tool_call_id="call_math_002",
        tool_name="audit_retainage_math",
        output={"status": "OK"},
    )

    s1 = apply_state_update(initial_state, {"tool_artifacts": {art1.tool_call_id: art1}}, caller_node=FORENSIC_WRITER)
    assert "call_ocr_001" in s1.tool_artifacts

    s2 = apply_state_update(s1, {"tool_artifacts": {art2.tool_call_id: art2}}, caller_node=FORENSIC_WRITER)
    assert "call_ocr_001" in s2.tool_artifacts
    assert "call_math_002" in s2.tool_artifacts
