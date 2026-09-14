"""Unit tests for Pydantic V2 State Schemas and Invariant Validation."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.state.schema import (
    DecisionCardPayload,
    DrawPacketMeta,
    LienChainStatus,
    LineItem,
)


def test_draw_packet_meta_strict_validation() -> None:
    """Verify DrawPacketMeta validation and extra='forbid' enforcement."""
    meta = DrawPacketMeta(
        project_id="P-100",
        subcontractor_id="SUB-99",
        draw_number=1,
        source_uris=["s3://bucket/invoice.pdf"],
    )
    assert meta.draw_number == 1

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        DrawPacketMeta(
            project_id="P-100",
            subcontractor_id="SUB-99",
            draw_number=1,
            source_uris=["s3://bucket/invoice.pdf"],
            unauthorized_field="injection_attempt",
        )


def test_line_item_decimal_validation() -> None:
    """Verify LineItem uses precise Decimals and validates ranges."""
    item = LineItem(
        line_item_id="LI-001",
        description="Steel Framing",
        contract_retainage_pct=Decimal("0.10"),
        current_billed=Decimal("12345.67"),
        stored_materials=Decimal("0.00"),
        prior_payments=Decimal("5000.00"),
    )
    assert isinstance(item.current_billed, Decimal)
    assert item.current_billed == Decimal("12345.67")

    # Negative billing rejected
    with pytest.raises(ValidationError):
        LineItem(
            line_item_id="LI-001",
            description="Steel Framing",
            contract_retainage_pct=Decimal("0.10"),
            current_billed=Decimal("-500.00"),
        )


def test_decision_card_payload_structure() -> None:
    """Verify DecisionCardPayload schema and required deliverable contract."""
    payload = DecisionCardPayload(
        draw_number=2,
        project_name="Commercial Tower A",
        subcontractor_trade="Electrical",
        gross_amount_requested=Decimal("25000.00"),
        contractual_retainage_withheld=Decimal("2500.00"),
        net_recommended_release=Decimal("22500.00"),
        lien_chain_status=LienChainStatus.VALID,
        recommended_action="APPROVE_RELEASE",
        blocking_discrepancies=[],
    )
    assert payload.recommended_action == "APPROVE_RELEASE"
    assert payload.net_recommended_release == Decimal("22500.00")
