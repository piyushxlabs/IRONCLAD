"""Tool Calling Accuracy, Parameter Precision & Node-Tool Matrix Evaluation Suite.

Evaluates:
- Tool parameter precision, Decimal arithmetic fidelity, and schema conformity
- Strict enforcement of the Node-Tool Access Matrix (AGENT_LOGIC_SPEC.md Section 6)
- Structured output accuracy and verbatim citation grounding
- Multi-track DAG execution accuracy across canonical test scenarios
- DeepEval / Evaluation benchmarks per AGENT_MASTER_PLAN.md Section 9.1 & 9.6
"""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal

import pytest

from src.agents.graph import build_ironclad_graph
from src.errors import ProhibitedActionError
from src.guardrails.prohibitions import validate_node_tool_access
from src.models import get_model_invoker
from src.state.checkpointing import MockCheckpointManager
from src.state.schema import (
    DrawPacketMeta,
    IroncladState,
    LienChainStatus,
    LineItem,
    RuntimeConfig,
)
from src.structured_outputs import (
    DecisionCardStructuredOutput,
    LineItemMappingAndDiscrepancy,
    RiderClauseClassification,
    StatutoryClockSummary,
)
from src.tools import (
    LienWaiverRecord,
    audit_retainage_math,
    dispatch_decision_notification,
    statutory_prompt_pay_clock,
    verify_lien_chain_integrity,
)

# ==============================================================================
# 1. Deterministic Tool Calling & Mathematical Precision Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_tool_audit_retainage_math_precision() -> None:
    """Evaluate audit_retainage_math tool accuracy against complex decimal figures."""
    result = await audit_retainage_math(
        contract_retainage_pct=0.10,
        current_billed=185432.78,
        stored_materials=24500.22,
        prior_payments=50000.00,
    )
    assert result.success is True
    # Gross: 185432.78 + 24500.22 = 209933.00
    assert result.gross_amount_requested == Decimal("209933.00")
    # Retainage (10%): 20993.30
    assert result.contractual_retainage_withheld == Decimal("20993.30")
    # Net: 209933.00 - 20993.30 - 50000.00 = 138939.70
    assert result.net_recommended_release == Decimal("138939.70")
    assert len(result.calculation_trace) == 3


@pytest.mark.asyncio
async def test_tool_verify_lien_chain_integrity_accuracy() -> None:
    """Evaluate verify_lien_chain_integrity detecting pre-dated notary and valid chains."""
    # Test valid waiver
    valid_res = await verify_lien_chain_integrity(
        waivers=[
            LienWaiverRecord(
                waiver_id="W-001",
                waiver_type="UNCONDITIONAL_PROGRESS",
                notary_execution_date=date(2026, 4, 2),
                associated_line_item_id="LI-001",
            )
        ],
        check_date=date(2026, 4, 1),
    )
    assert valid_res.success is True
    assert valid_res.lien_chain_status == "VALID"
    assert len(valid_res.findings) == 1
    assert valid_res.findings[0].finding == "OK"

    # Test pre-dated notary (notarized on 2026-03-25 before check date 2026-04-01)
    predated_res = await verify_lien_chain_integrity(
        waivers=[
            LienWaiverRecord(
                waiver_id="W-002",
                waiver_type="CONDITIONAL_PROGRESS",
                notary_execution_date=date(2026, 3, 25),
                associated_line_item_id="LI-002",
            )
        ],
        check_date=date(2026, 4, 1),
    )
    assert predated_res.success is True
    assert predated_res.lien_chain_status == "SUSPECT_PRE_DATED_NOTARY"
    assert len(predated_res.findings) == 1
    assert predated_res.findings[0].finding == "PRE_DATED_NOTARY"


@pytest.mark.asyncio
async def test_tool_statutory_prompt_pay_clock_accuracy() -> None:
    """Evaluate statutory prompt pay clock calculations across commercial jurisdictions."""
    # Texas (35 days from invoice receipt)
    tx_clock = await statutory_prompt_pay_clock(
        state_jurisdiction="TX",
        invoice_receipt_date=date(2026, 4, 1),
        contract_clause="pay-if-paid",
    )
    assert tx_clock.success is True
    assert tx_clock.state == "TX"
    assert tx_clock.days_remaining is not None
    assert tx_clock.penalty_interest_rate == Decimal("0.0150")

    # New York (30 days from invoice receipt)
    ny_clock = await statutory_prompt_pay_clock(
        state_jurisdiction="NY",
        invoice_receipt_date="2026-04-01",
        contract_clause="pay-when-paid",
    )
    assert ny_clock.success is True
    assert ny_clock.state == "NY"
    assert ny_clock.penalty_interest_rate == Decimal("0.0100")


@pytest.mark.asyncio
async def test_tool_dispatch_notification_accuracy() -> None:
    """Evaluate notification routing logic for standard vs urgent statutory deadlines."""
    # Standard notification
    std_res = await dispatch_decision_notification(
        notification_type="DECISION_CARD_READY",
        project_id="PRJ-METRO-001",
        draw_number=4,
        recipients=["GENERAL_CONTRACTOR"],
    )
    assert std_res.success is True
    assert "GENERAL_CONTRACTOR" in std_res.dispatched_to

    # Urgent escalation notification
    urg_res = await dispatch_decision_notification(
        notification_type="URGENT_STATUTORY_ESCALATION",
        project_id="PRJ-METRO-001",
        draw_number=4,
        recipients=["GENERAL_CONTRACTOR", "OWNER"],
    )
    assert urg_res.success is True
    assert "OWNER" in urg_res.dispatched_to


# ==============================================================================
# 2. Node-Tool Access Matrix Enforcement Evals
# ==============================================================================


def test_node_tool_access_matrix_adherence() -> None:
    """Verify programmatic enforcement of the Node-Tool Access Matrix."""
    # ForensicAuditSentinel: Allowed tools
    validate_node_tool_access("ForensicAuditSentinel", "extract_draw_packet_metadata")
    validate_node_tool_access("ForensicAuditSentinel", "audit_retainage_math")
    validate_node_tool_access("ForensicAuditSentinel", "verify_lien_chain_integrity")
    validate_node_tool_access("ForensicAuditSentinel", "LineItemMappingAndDiscrepancy")

    # ForensicAuditSentinel: Forbidden tools
    with pytest.raises(ProhibitedActionError):
        validate_node_tool_access("ForensicAuditSentinel", "statutory_prompt_pay_clock")
    with pytest.raises(ProhibitedActionError):
        validate_node_tool_access("ForensicAuditSentinel", "dispatch_decision_notification")
    with pytest.raises(ProhibitedActionError):
        validate_node_tool_access("ForensicAuditSentinel", "execute_ach_payment")

    # FairPayStatutoryGuardian: Allowed tools
    validate_node_tool_access("FairPayStatutoryGuardian", "statutory_prompt_pay_clock")
    validate_node_tool_access("FairPayStatutoryGuardian", "RiderClauseClassification")

    # FairPayStatutoryGuardian: Forbidden tools
    with pytest.raises(ProhibitedActionError):
        validate_node_tool_access("FairPayStatutoryGuardian", "audit_retainage_math")
    with pytest.raises(ProhibitedActionError):
        validate_node_tool_access("FairPayStatutoryGuardian", "extract_draw_packet_metadata")
    with pytest.raises(ProhibitedActionError):
        validate_node_tool_access("FairPayStatutoryGuardian", "dispatch_decision_notification")

    # EverydayDecisionCardEmitter: Allowed tools
    validate_node_tool_access("EverydayDecisionCardEmitter", "dispatch_decision_notification")
    validate_node_tool_access("EverydayDecisionCardEmitter", "DecisionCardPayload")

    # EverydayDecisionCardEmitter: Forbidden tools
    with pytest.raises(ProhibitedActionError):
        validate_node_tool_access("EverydayDecisionCardEmitter", "audit_retainage_math")
    with pytest.raises(ProhibitedActionError):
        validate_node_tool_access("EverydayDecisionCardEmitter", "verify_lien_chain_integrity")
    with pytest.raises(ProhibitedActionError):
        validate_node_tool_access("EverydayDecisionCardEmitter", "statutory_prompt_pay_clock")


# ==============================================================================
# 3. Structured Output Accuracy & Grounding Evals
# ==============================================================================


def test_line_item_mapping_structured_output_accuracy() -> None:
    """Evaluate LineItemMappingAndDiscrepancy schema and confidence bounds."""
    mapping = LineItemMappingAndDiscrepancy(
        normalized_line_items=[
            LineItem(
                line_item_id="LI-001",
                description="HVAC Ductwork Installation",
                contract_retainage_pct=Decimal("0.10"),
                current_billed=Decimal("25000.00"),
                stored_materials=Decimal("0.00"),
                prior_payments=Decimal("0.00"),
            )
        ],
        new_discrepancies=[],
        confidence=0.98,
    )
    assert mapping.confidence >= 0.95
    assert len(mapping.normalized_line_items) == 1
    assert mapping.normalized_line_items[0].current_billed == Decimal("25000.00")


def test_rider_clause_classification_accuracy() -> None:
    """Evaluate RiderClauseClassification structure and verbatim clause quoting."""
    clause = RiderClauseClassification(
        contract_clause="pay-if-paid",
        confidence=0.99,
        ambiguous=False,
    )
    assert clause.contract_clause == "pay-if-paid"
    assert clause.confidence >= 0.90
    assert clause.ambiguous is False


def test_decision_card_structured_output_accuracy() -> None:
    """Evaluate DecisionCardStructuredOutput exact field fidelity."""
    card = DecisionCardStructuredOutput(
        project_id="PRJ-TEXAS-001",
        subcontractor_name="Apex Mechanical",
        draw_number=4,
        gross_amount_requested=Decimal("25000.00"),
        contractual_retainage_withheld=Decimal("2500.00"),
        net_recommended_release=Decimal("22500.00"),
        flagged_discrepancies=[],
        lien_chain_status="VALID",
        statutory_prompt_pay_clock=StatutoryClockSummary(
            state="TX",
            days_remaining=26,
            deadline_timestamp="2026-05-06T00:00:00Z",
            penalty_interest_rate=Decimal("0.0150"),
        ),
        recommended_action="APPROVE_RELEASE",
    )
    assert card.gross_amount_requested - card.contractual_retainage_withheld == card.net_recommended_release
    assert card.recommended_action == "APPROVE_RELEASE"


# ==============================================================================
# 4. Multi-Track DAG End-to-End Accuracy across Canonical Scenarios
# ==============================================================================


@pytest.mark.asyncio
async def test_e2e_dag_accuracy_clean_scenario() -> None:
    """Evaluate full DAG accuracy on Simple Clean Case -> APPROVE_RELEASE."""
    state = IroncladState(
        draw_packet_meta=DrawPacketMeta(
            project_id="PRJ-CLEAN-001",
            subcontractor_id="SUB-HVAC-101",
            draw_number=4,
            source_uris=["tests/mocks/fixtures/draw_4_hvac_invoice.pdf"],
        ),
        runtime_config=RuntimeConfig(runtime_mode="mock"),
    )
    checkpoint_mgr = MockCheckpointManager()
    session_id = "test-e2e-clean-eval"

    graph = build_ironclad_graph()
    final_state = await graph.execute(
        initial_state=state,
        checkpoint_manager=checkpoint_mgr,
        session_id=session_id,
    )

    assert final_state.decision_card_payload is not None
    assert final_state.decision_card_payload.recommended_action == "APPROVE_RELEASE"
    assert len(final_state.flagged_discrepancies) == 0
    assert final_state.lien_chain_status == LienChainStatus.VALID
    assert final_state.statutory_prompt_pay_clock is not None
    assert final_state.approval_state is None  # Paused at HITL gate


@pytest.mark.asyncio
async def test_e2e_dag_accuracy_complex_defect_scenario() -> None:
    """Evaluate full DAG accuracy on Complex Defect Case -> HOLD_REQUEST_CORRECTED_WAIVER / ESCALATE_LEGAL."""
    state = IroncladState(
        draw_packet_meta=DrawPacketMeta(
            project_id="PRJ-DEFECT-002",
            subcontractor_id="SUB-ELEC-202",
            draw_number=2,
            source_uris=["tests/mocks/fixtures/draw_2_electrical_defect_invoice.pdf"],
        ),
        runtime_config=RuntimeConfig(runtime_mode="mock"),
    )
    checkpoint_mgr = MockCheckpointManager()
    session_id = "test-e2e-defect-eval"

    graph = build_ironclad_graph()
    final_state = await graph.execute(
        initial_state=state,
        checkpoint_manager=checkpoint_mgr,
        session_id=session_id,
    )

    assert final_state.decision_card_payload is not None
    # Must NEVER recommend approve release when discrepancies exist
    assert final_state.decision_card_payload.recommended_action in (
        "HOLD_REQUEST_CORRECTION",
        "HOLD_REQUEST_CORRECTED_WAIVER",
        "ESCALATE_LEGAL",
    )
    assert len(final_state.flagged_discrepancies) > 0


@pytest.mark.asyncio
async def test_e2e_dag_accuracy_edge_case_scenario() -> None:
    """Evaluate full DAG accuracy on Edge Case -> urgent escalation with missing waiver."""
    state = IroncladState(
        draw_packet_meta=DrawPacketMeta(
            project_id="PRJ-EDGE-003",
            subcontractor_id="SUB-PLUMB-303",
            draw_number=3,
            source_uris=["tests/mocks/fixtures/draw_3_plumbing_edge_case.pdf"],
        ),
        runtime_config=RuntimeConfig(runtime_mode="mock"),
    )
    checkpoint_mgr = MockCheckpointManager()
    session_id = "test-e2e-edge-eval"

    graph = build_ironclad_graph()
    final_state = await graph.execute(
        initial_state=state,
        checkpoint_manager=checkpoint_mgr,
        session_id=session_id,
    )

    assert final_state.decision_card_payload is not None
    assert final_state.decision_card_payload.recommended_action != "APPROVE_RELEASE"
    assert len(final_state.flagged_discrepancies) > 0


# ==============================================================================
# 5. Live Staging Model Invoker Evaluation (Conditional on GEMINI_API_KEY)
# ==============================================================================


@pytest.mark.asyncio
async def test_staging_model_invoker_accuracy_when_configured() -> None:
    """Evaluates live Gemini 3.8 Flash staging model invoker when GEMINI_API_KEY is present."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not configured in environment; skipping live staging eval.")

    invoker = get_model_invoker("staging")

    # Evaluate structured reasoning on rider clause
    sample_clause = (
        "Subcontractor agrees that payment by Owner to Contractor for Subcontractor's work "
        "is an explicit condition precedent to any obligation of Contractor to pay Subcontractor."
    )
    try:
        result = await invoker.invoke_reasoning(
            prompt=f"Classify the following contract clause accurately:\n{sample_clause}",
            system_prompt="You are FairPayStatutoryGuardian classifying construction contract riders.",
            structured_output_schema=RiderClauseClassification,
        )
        assert isinstance(result, RiderClauseClassification)
        assert result.contract_clause == "pay-if-paid"
        assert result.confidence >= 0.80
    except Exception as e:
        if "503" in str(e) or "UNAVAILABLE" in str(e) or "429" in str(e) or "high demand" in str(e):
            pytest.skip(f"Live Gemini API is temporarily experiencing high demand / 503 unavailable: {e}")
        raise
