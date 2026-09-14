"""Unit Tests for IRONCLAD Structured Outputs.

Tests LineItemMappingAndDiscrepancy, RiderClauseClassification, and DecisionCardStructuredOutput,
verifying strict Pydantic V2 schema validation and strict JSON schema conformity.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.state.schema import Discrepancy, LineItem
from src.structured_outputs import (
    DECISION_CARD_PAYLOAD_SCHEMA,
    LINE_ITEM_MAPPING_AND_DISCREPANCY_SCHEMA,
    RIDER_CLAUSE_CLASSIFICATION_SCHEMA,
    DecisionCardStructuredOutput,
    FlaggedDiscrepancyEntry,
    LineItemMappingAndDiscrepancy,
    RiderClauseClassification,
    StatutoryClockSummary,
)

# ==============================================================================
# 1. LineItemMappingAndDiscrepancy Tests
# ==============================================================================


def test_line_item_mapping_and_discrepancy_valid() -> None:
    """Verify valid LineItemMappingAndDiscrepancy creation and field validation."""
    line_item = LineItem(
        line_item_id="LI-001",
        description="Drywall installation",
        contract_retainage_pct=Decimal("0.10"),
        current_billed=Decimal("25000.00"),
        stored_materials=Decimal("0.00"),
        prior_payments=Decimal("10000.00"),
    )
    discrepancy = Discrepancy(
        line_item_id="LI-002",
        discrepancy_type="MISSING_RETAINAGE_CLAUSE",
        description="Retainage clause illegible in continuation sheet",
    )

    mapping = LineItemMappingAndDiscrepancy(
        normalized_line_items=[line_item],
        new_discrepancies=[discrepancy],
        confidence=0.95,
    )
    assert len(mapping.normalized_line_items) == 1
    assert len(mapping.new_discrepancies) == 1
    assert mapping.confidence == 0.95


def test_line_item_mapping_and_discrepancy_confidence_bounds() -> None:
    """Assert confidence outside [0.0, 1.0] raises ValidationError."""
    with pytest.raises(ValidationError):
        LineItemMappingAndDiscrepancy(
            normalized_line_items=[],
            new_discrepancies=[],
            confidence=1.5,
        )


def test_line_item_mapping_and_discrepancy_schema() -> None:
    """Verify strict JSON schema structure for LineItemMappingAndDiscrepancy."""
    schema = LINE_ITEM_MAPPING_AND_DISCREPANCY_SCHEMA
    assert schema["name"] == "line_item_mapping_and_discrepancy"
    assert schema["strict"] is True
    assert "properties" in schema["schema"]
    assert "normalized_line_items" in schema["schema"]["required"]


# ==============================================================================
# 2. RiderClauseClassification Tests
# ==============================================================================


def test_rider_clause_classification_pay_if_paid() -> None:
    """Verify pay-if-paid classification."""
    classification = RiderClauseClassification(
        contract_clause="pay-if-paid",
        confidence=0.98,
        ambiguous=False,
    )
    assert classification.contract_clause == "pay-if-paid"
    assert classification.ambiguous is False


def test_rider_clause_classification_ambiguous() -> None:
    """Verify ambiguous clause handling."""
    classification = RiderClauseClassification(
        contract_clause=None,
        confidence=0.45,
        ambiguous=True,
    )
    assert classification.contract_clause is None
    assert classification.ambiguous is True


def test_rider_clause_classification_schema() -> None:
    """Verify strict JSON schema structure for RiderClauseClassification."""
    schema = RIDER_CLAUSE_CLASSIFICATION_SCHEMA
    assert schema["name"] == "rider_clause_classification"
    assert schema["strict"] is True
    assert "contract_clause" in schema["schema"]["required"]


# ==============================================================================
# 3. DecisionCardStructuredOutput Tests
# ==============================================================================


def test_decision_card_structured_output_valid() -> None:
    """Verify valid DecisionCardStructuredOutput creation with exact fields."""
    clock_summary = StatutoryClockSummary(
        state="TX",
        days_remaining=21,
        deadline_timestamp="2026-10-04T00:00:00Z",
        penalty_interest_rate=Decimal("0.015"),
    )
    discrepancy = FlaggedDiscrepancyEntry(
        line_item_id="LI-001",
        discrepancy_type="PRE_DATED_NOTARY",
        description="Notary date precedes check date",
        variance_amount=Decimal("1500.00"),
    )

    card = DecisionCardStructuredOutput(
        project_id="PRJ-101",
        subcontractor_name="Apex Foundation LLC",
        draw_number=4,
        gross_amount_requested=Decimal("50000.00"),
        contractual_retainage_withheld=Decimal("2500.00"),
        net_recommended_release=Decimal("47500.00"),
        flagged_discrepancies=[discrepancy],
        lien_chain_status="SUSPECT_PRE_DATED_NOTARY",
        statutory_prompt_pay_clock=clock_summary,
        recommended_action="HOLD_REQUEST_CORRECTED_WAIVER",
    )
    assert card.project_id == "PRJ-101"
    assert card.gross_amount_requested == Decimal("50000.00")
    assert card.recommended_action == "HOLD_REQUEST_CORRECTED_WAIVER"
    assert len(card.flagged_discrepancies) == 1


def test_decision_card_structured_output_schema() -> None:
    """Verify strict JSON schema structure for DecisionCardStructuredOutput."""
    schema = DECISION_CARD_PAYLOAD_SCHEMA
    assert schema["name"] == "decision_card_payload"
    assert schema["strict"] is True
    assert "recommended_action" in schema["schema"]["required"]
    assert "net_recommended_release" in schema["schema"]["required"]
