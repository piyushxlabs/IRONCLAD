"""Unit Tests for IRONCLAD Tools and Schemas.

Tests all five tools and their strict Pydantic and JSON schemas, verifying input sanitization,
deterministic Decimal arithmetic, chronological notary verification, statutory prompt-pay clocks,
and notification dispatch.
"""

from datetime import date
from decimal import Decimal

import pytest

from src.errors import StateValidationError
from src.tools import (
    AUDIT_RETAINAGE_MATH_SCHEMA,
    DISPATCH_DECISION_NOTIFICATION_SCHEMA,
    EXTRACT_DRAW_PACKET_METADATA_SCHEMA,
    STATUTORY_PROMPT_PAY_CLOCK_SCHEMA,
    VERIFY_LIEN_CHAIN_INTEGRITY_SCHEMA,
    AuditRetainageMathOutput,
    DispatchDecisionNotificationOutput,
    ExtractDrawPacketMetadataOutput,
    LienWaiverRecord,
    StatutoryPromptPayClockOutput,
    VerifyLienChainIntegrityOutput,
    audit_retainage_math,
    dispatch_decision_notification,
    extract_draw_packet_metadata,
    statutory_prompt_pay_clock,
    verify_lien_chain_integrity,
)

# ==============================================================================
# 1. extract_draw_packet_metadata Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_extract_draw_packet_metadata_mock() -> None:
    """Verify OCR extraction tool execution against mock runtime."""
    res = await extract_draw_packet_metadata("s3://ironclad-draws/PRJ-101/draw4.pdf")
    assert isinstance(res, ExtractDrawPacketMetadataOutput)
    assert res.success is True
    assert res.document_type_detected == "G703_CONTINUATION"
    assert len(res.line_items) >= 1
    assert len(res.waiver_records) >= 1


@pytest.mark.asyncio
async def test_extract_draw_packet_metadata_path_traversal_rejection() -> None:
    """Assert path traversal sequences in pdf_uri are rejected."""
    with pytest.raises(StateValidationError) as exc:
        await extract_draw_packet_metadata("s3://bucket/../../etc/passwd.pdf")
    assert "Path traversal sequence detected" in str(exc.value)


@pytest.mark.asyncio
async def test_extract_draw_packet_metadata_empty_uri_rejection() -> None:
    """Assert empty pdf_uri is rejected."""
    with pytest.raises(StateValidationError) as exc:
        await extract_draw_packet_metadata("   ")
    assert "pdf_uri cannot be empty" in str(exc.value)


# ==============================================================================
# 2. audit_retainage_math Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_audit_retainage_math_clean_calculation() -> None:
    """Verify deterministic Decimal retainage calculation without prior payments."""
    res = await audit_retainage_math(
        contract_retainage_pct=0.05,
        current_billed=Decimal("12000.00"),
        stored_materials=Decimal("0.00"),
        prior_payments=Decimal("0.00"),
    )
    assert isinstance(res, AuditRetainageMathOutput)
    assert res.success is True
    assert res.gross_amount_requested == Decimal("12000.00")
    assert res.contractual_retainage_withheld == Decimal("600.00")
    assert res.net_recommended_release == Decimal("11400.00")
    assert len(res.calculation_trace) == 3


@pytest.mark.asyncio
async def test_audit_retainage_math_with_stored_materials_and_prior_payments() -> None:
    """Verify calculation with stored materials and prior payments."""
    res = await audit_retainage_math(
        contract_retainage_pct="0.10",
        current_billed="50000.00",
        stored_materials="10000.00",
        prior_payments="20000.00",
    )
    assert res.success is True
    # gross = 50000 + 10000 = 60000
    assert res.gross_amount_requested == Decimal("60000.00")
    # retainage = 60000 * 0.10 = 6000
    assert res.contractual_retainage_withheld == Decimal("6000.00")
    # net = 60000 - 6000 - 20000 = 34000
    assert res.net_recommended_release == Decimal("34000.00")


@pytest.mark.asyncio
async def test_audit_retainage_math_negative_input_rejection() -> None:
    """Assert negative monetary input is rejected."""
    with pytest.raises(StateValidationError) as exc:
        await audit_retainage_math(
            contract_retainage_pct=0.05,
            current_billed=Decimal("-500.00"),
        )
    assert "must be non-negative" in str(exc.value)


@pytest.mark.asyncio
async def test_audit_retainage_math_out_of_bounds_retainage_rejection() -> None:
    """Assert retainage percentage outside [0.0, 1.0] is rejected."""
    with pytest.raises(StateValidationError) as exc:
        await audit_retainage_math(
            contract_retainage_pct=5.0,  # Passed 5 instead of 0.05
            current_billed=10000,
        )
    assert "within [0.0, 1.0]" in str(exc.value)


# ==============================================================================
# 3. verify_lien_chain_integrity Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_verify_lien_chain_integrity_valid_waiver() -> None:
    """Verify clean chronological waiver validation."""
    waiver = LienWaiverRecord(
        waiver_id="W-001",
        waiver_type="CONDITIONAL_PROGRESS",
        notary_execution_date=date(2026, 9, 5),
        associated_line_item_id="LI-001",
    )
    check_date = date(2026, 9, 1)

    res = await verify_lien_chain_integrity(
        waivers=[waiver],
        check_date=check_date,
    )
    assert isinstance(res, VerifyLienChainIntegrityOutput)
    assert res.success is True
    assert res.lien_chain_status == "VALID"
    assert res.findings[0].finding == "OK"


@pytest.mark.asyncio
async def test_verify_lien_chain_integrity_pre_dated_notary() -> None:
    """Verify detection of pre-dated notary execution (notary date < check date)."""
    waiver = LienWaiverRecord(
        waiver_id="W-002",
        waiver_type="CONDITIONAL_PROGRESS",
        notary_execution_date=date(2026, 8, 25),  # Before check date!
        associated_line_item_id="LI-001",
    )
    check_date = date(2026, 9, 1)

    res = await verify_lien_chain_integrity(
        waivers=[waiver],
        check_date=check_date,
    )
    assert res.success is True
    assert res.lien_chain_status == "SUSPECT_PRE_DATED_NOTARY"
    assert res.findings[0].finding == "PRE_DATED_NOTARY"


@pytest.mark.asyncio
async def test_verify_lien_chain_integrity_missing_notary_date() -> None:
    """Verify handling of unnotarized or missing date waiver."""
    waiver = LienWaiverRecord(
        waiver_id="W-003",
        waiver_type="CONDITIONAL_PROGRESS",
        notary_execution_date=None,
        associated_line_item_id="LI-001",
    )
    res = await verify_lien_chain_integrity(
        waivers=[waiver],
        check_date="2026-09-01",
    )
    assert res.success is True
    assert res.lien_chain_status == "INVALID_FORM"
    assert res.findings[0].finding == "MISSING_NOTARY_DATE"


@pytest.mark.asyncio
async def test_verify_lien_chain_integrity_empty_waiver_rejection() -> None:
    """Assert empty waiver list is rejected immediately."""
    with pytest.raises(StateValidationError) as exc:
        await verify_lien_chain_integrity(waivers=[], check_date="2026-09-01")
    assert "Waivers list cannot be empty" in str(exc.value)


# ==============================================================================
# 4. statutory_prompt_pay_clock Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_statutory_prompt_pay_clock_valid_texas() -> None:
    """Verify statutory prompt-pay tool invocation for Texas."""
    res = await statutory_prompt_pay_clock(
        state_jurisdiction="TX",
        invoice_receipt_date="2026-09-01",
        contract_clause="pay-if-paid",
    )
    assert isinstance(res, StatutoryPromptPayClockOutput)
    assert res.success is True
    assert res.state == "TX"
    assert res.penalty_interest_rate == Decimal("0.015")
    assert res.statute_reference is not None


@pytest.mark.asyncio
async def test_statutory_prompt_pay_clock_invalid_clause_rejection() -> None:
    """Assert invalid contract clause is rejected."""
    with pytest.raises(StateValidationError) as exc:
        await statutory_prompt_pay_clock(
            state_jurisdiction="TX",
            invoice_receipt_date="2026-09-01",
            contract_clause="ambiguous_custom",
        )
    assert "must be 'pay-if-paid' or 'pay-when-paid'" in str(exc.value)


@pytest.mark.asyncio
async def test_statutory_prompt_pay_clock_unknown_jurisdiction_rejection() -> None:
    """Assert unresolvable state jurisdiction is rejected."""
    with pytest.raises(StateValidationError) as exc:
        await statutory_prompt_pay_clock(
            state_jurisdiction="ZZ",
            invoice_receipt_date="2026-09-01",
            contract_clause="pay-if-paid",
        )
    assert "Unresolvable or unsupported state jurisdiction" in str(exc.value)


# ==============================================================================
# 5. dispatch_decision_notification Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_dispatch_decision_notification_standard() -> None:
    """Verify standard decision card notification dispatch."""
    res = await dispatch_decision_notification(
        notification_type="DECISION_CARD_READY",
        project_id="PRJ-101",
        draw_number=4,
        recipients=["GENERAL_CONTRACTOR", "OWNER", "SUBCONTRACTOR"],
    )
    assert isinstance(res, DispatchDecisionNotificationOutput)
    assert res.success is True
    assert len(res.dispatched_to) == 3


@pytest.mark.asyncio
async def test_dispatch_decision_notification_urgent_escalation() -> None:
    """Verify urgent statutory escalation notification dispatch."""
    res = await dispatch_decision_notification(
        notification_type="URGENT_STATUTORY_ESCALATION",
        project_id="PRJ-101",
        draw_number=4,
        recipients=["GENERAL_CONTRACTOR"],
    )
    assert res.success is True


@pytest.mark.asyncio
async def test_dispatch_decision_notification_invalid_type() -> None:
    """Assert invalid notification type is rejected."""
    with pytest.raises(StateValidationError) as exc:
        await dispatch_decision_notification(
            notification_type="RANDOM_ALERT",
            project_id="PRJ-101",
            draw_number=4,
            recipients=["GENERAL_CONTRACTOR"],
        )
    assert "Invalid notification_type" in str(exc.value)


# ==============================================================================
# 6. JSON Schema Conformity Tests
# ==============================================================================


def test_strict_json_schemas_structure() -> None:
    """Verify all 5 strict JSON schemas match OpenAPI / MCP tool calling specs."""
    schemas = [
        EXTRACT_DRAW_PACKET_METADATA_SCHEMA,
        AUDIT_RETAINAGE_MATH_SCHEMA,
        VERIFY_LIEN_CHAIN_INTEGRITY_SCHEMA,
        STATUTORY_PROMPT_PAY_CLOCK_SCHEMA,
        DISPATCH_DECISION_NOTIFICATION_SCHEMA,
    ]
    for s in schemas:
        assert "name" in s
        assert "description" in s
        assert s.get("strict") is True
        assert "parameters" in s
        params = s["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert "required" in params
        assert params.get("additionalProperties") is False
