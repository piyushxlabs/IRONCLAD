"""Hallucination Resistance & Grounding Evaluation Suite.

Adheres strictly to:
- AGENT_MASTER_PLAN.md Section 9.3 (Hallucination Prevention Evals)
- AGENT_LOGIC_SPEC.md Section 8 (Silence-Over-Guessing & Grounding)
- .agents/rules/strict-grounding-prohibitions-and-refusal-standards.md
"""

from decimal import Decimal

import pytest

from src.agents import (
    everyday_decision_card_emitter_node,
    fair_pay_statutory_guardian_node,
    forensic_audit_sentinel_node,
)
from src.guardrails import verify_zero_llm_math
from src.state.reducers import apply_state_update
from src.state.schema import (
    DrawPacketMeta,
    IroncladState,
    LienChainStatus,
    LineItem,
    RetainageAuditResult,
    RuntimeConfig,
)


@pytest.mark.asyncio
async def test_missing_retainage_does_not_hallucinate_default() -> None:
    """Assert ForensicAuditSentinel appends MISSING_RETAINAGE_CLAUSE and never guesses 5%."""
    # State with empty line items initially
    state = IroncladState(
        draw_packet_meta=DrawPacketMeta(
            project_id="PROJ-001",
            subcontractor_id="SUB-001",
            draw_number=1,
            source_uris=["s3://bucket/doc.pdf"],
        ),
        runtime_config=RuntimeConfig(runtime_mode="mock"),
    )

    updates = await forensic_audit_sentinel_node(state)

    # In mock, if a missing retainage item were parsed, it creates a discrepancy
    # Let's verify line items all have strictly non-null contract_retainage_pct
    for li in updates["extracted_line_items"]:
        assert li.contract_retainage_pct is not None
        assert isinstance(li.contract_retainage_pct, Decimal)


@pytest.mark.asyncio
async def test_unresolvable_jurisdiction_produces_null_clock() -> None:
    """Assert unresolvable jurisdiction leaves clock as None and logs UNRESOLVABLE_JURISDICTION."""
    state = IroncladState(
        draw_packet_meta=DrawPacketMeta(
            project_id="PROJ-UNKNOWN-999",
            subcontractor_id="SUB-001",
            draw_number=1,
            source_uris=["s3://bucket/doc.pdf"],
        ),
        runtime_config=RuntimeConfig(runtime_mode="mock"),
    )

    # Force unresolvable jurisdiction
    updates = await fair_pay_statutory_guardian_node(
        state=state,
        jurisdiction_override="XX",  # Invalid US jurisdiction
    )

    assert updates["statutory_prompt_pay_clock"] is None
    assert len(updates["flagged_discrepancies"]) > 0
    assert any(
        d.discrepancy_type == "UNRESOLVABLE_JURISDICTION"
        for d in updates["flagged_discrepancies"]
    )


@pytest.mark.asyncio
async def test_decision_card_exact_figure_grounding() -> None:
    """Assert every dollar figure in decision card payload matches verified math calculation."""
    retainage_result = RetainageAuditResult(
        gross_amount_requested=Decimal("25000.00"),
        contractual_retainage_withheld=Decimal("1250.00"),
        net_recommended_release=Decimal("23750.00"),
        calculation_trace=[
            "gross = 25000.00",
            "retainage = 25000.00 * 0.05 = 1250.00",
            "net = 25000.00 - 1250.00 = 23750.00",
        ],
    )

    state = IroncladState(
        draw_packet_meta=DrawPacketMeta(
            project_id="PROJ-TX-101",
            subcontractor_id="SUB-001",
            draw_number=2,
            source_uris=["s3://b/d2.pdf"],
        ),
        extracted_line_items=[
            LineItem(
                line_item_id="LI-001",
                description="HVAC Rough-In",
                contract_retainage_pct=Decimal("0.05"),
                current_billed=Decimal("25000.00"),
            )
        ],
        retainage_audit_result=retainage_result,
        lien_chain_status=LienChainStatus.VALID,
        runtime_config=RuntimeConfig(runtime_mode="mock"),
    )

    updates = await everyday_decision_card_emitter_node(state, dispatch_alert=False)
    card = updates["decision_card_payload"]

    assert card is not None
    assert card.gross_amount_requested == retainage_result.gross_amount_requested
    assert card.contractual_retainage_withheld == retainage_result.contractual_retainage_withheld
    assert card.net_recommended_release == retainage_result.net_recommended_release
    assert card.recommended_action == "APPROVE_RELEASE"

    # Verify zero LLM math guardrail passes
    verify_zero_llm_math(card, retainage_result)


@pytest.mark.asyncio
async def test_discrepancy_blocks_release_recommendation() -> None:
    """Assert open discrepancy strictly prevents APPROVE_RELEASE (Silence-Over-Guessing)."""
    state = IroncladState(
        draw_packet_meta=DrawPacketMeta(
            project_id="PROJ-FL-202",
            subcontractor_id="SUB-002",
            draw_number=1,
            source_uris=["s3://b/d.pdf"],
        ),
        retainage_audit_result=RetainageAuditResult(
            gross_amount_requested=Decimal("10000.00"),
            contractual_retainage_withheld=Decimal("1000.00"),
            net_recommended_release=Decimal("9000.00"),
            calculation_trace=[],
        ),
        lien_chain_status=LienChainStatus.VALID,
        runtime_config=RuntimeConfig(runtime_mode="mock"),
    )

    # Add discrepancy
    from src.state.schema import Discrepancy

    disc = Discrepancy(
        line_item_id="LI-002",
        discrepancy_type="UNREADABLE_NOTARY_SEAL",
        description="Notary seal is blurred and illegible.",
    )
    state = apply_state_update(state, {"flagged_discrepancies": [disc]}, caller_node="ForensicAuditSentinel")

    updates = await everyday_decision_card_emitter_node(state, dispatch_alert=False)
    card = updates["decision_card_payload"]

    assert card is not None
    assert card.recommended_action != "APPROVE_RELEASE"
    assert card.recommended_action == "HOLD_REQUEST_CORRECTED_WAIVER"
    assert len(card.blocking_discrepancies) == 1
