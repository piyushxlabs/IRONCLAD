"""Pydantic V2 Schemas for IRONCLAD Tools.

Adheres strictly to AGENT_LOGIC_SPEC.md Section 4 and AGENT_MASTER_PLAN.md Section 5.
Defines type-safe, strict models (extra="forbid") for tool inputs, outputs, and validation contracts.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LineItemRecord(BaseModel):
    """A single extracted AIA G703 continuation-sheet line item."""

    model_config = ConfigDict(extra="forbid")

    line_item_id: str = Field(..., description="Stable identifier for this line item within the packet")
    description: str = Field(..., description="Scope-of-work description as printed on the continuation sheet")
    contract_retainage_pct: Decimal | float | None = Field(
        None, ge=0.0, le=1.0, description="Retainage percentage for this item, e.g. 0.05 for 5%; null if unreadable"
    )
    current_billed: Decimal | None = Field(
        None, ge=0, description="Amount billed this period for this item; null if unreadable"
    )
    stored_materials: Decimal | None = Field(
        None, ge=0, description="Value of materials stored but not yet installed; null if unreadable"
    )
    prior_payments: Decimal | None = Field(
        None, ge=0, description="Cumulative amount paid for this item in prior draws; null if unreadable"
    )


class LienWaiverRecord(BaseModel):
    """A single extracted conditional/unconditional mechanics lien waiver."""

    model_config = ConfigDict(extra="forbid")

    waiver_id: str = Field(..., description="Stable identifier for this waiver document")
    waiver_type: Literal[
        "CONDITIONAL_PROGRESS",
        "UNCONDITIONAL_PROGRESS",
        "CONDITIONAL_FINAL",
        "UNCONDITIONAL_FINAL",
    ] = Field(..., description="Statutory waiver form type")
    notary_execution_date: date | None = Field(
        None, description="Date the waiver was notarized; null if illegible or unnotarized"
    )
    associated_line_item_id: str | None = Field(
        None, description="Line item this waiver corresponds to, if determinable"
    )


class ExtractDrawPacketMetadataInput(BaseModel):
    """Input for form-aware OCR and key-value extraction of a draw packet PDF."""

    model_config = ConfigDict(extra="forbid")

    pdf_uri: str = Field(
        ...,
        description="URI of the source PDF within the read-only document intake bucket (e.g. s3:// or local fixture)",
    )


class ExtractDrawPacketMetadataOutput(BaseModel):
    """Raw extracted fields from one draw packet document."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(..., description="Whether extraction completed without a fatal parsing error")
    document_type_detected: Literal[
        "G702_SUMMARY",
        "G703_CONTINUATION",
        "LIEN_WAIVER",
        "SUBCONTRACT_RIDER",
        "UNKNOWN",
    ] | None = Field(None, description="Classified document type of this source_uri")
    line_items: list[LineItemRecord] = Field(
        default_factory=list, description="Extracted line items, if this document is a G703 continuation sheet"
    )
    waiver_records: list[LienWaiverRecord] = Field(
        default_factory=list, description="Extracted waiver records, if this document is a lien waiver"
    )
    low_confidence_fields: list[str] = Field(
        default_factory=list, description="Field paths the OCR engine flagged as low-confidence"
    )
    error: str | None = Field(None, description="Error message if success is false")


class AuditRetainageMathInput(BaseModel):
    """Deterministic retainage and arithmetic verification parameters for one line item."""

    model_config = ConfigDict(extra="forbid")

    contract_retainage_pct: Decimal = Field(
        ..., ge=0, le=1, description="Contractual retainage percentage e.g. 0.05 for 5%"
    )
    current_billed: Decimal = Field(..., ge=0, description="Gross amount billed this period for this line item")
    stored_materials: Decimal = Field(
        default=Decimal("0.00"), ge=0, description="Value of materials stored but not yet installed"
    )
    prior_payments: Decimal = Field(
        default=Decimal("0.00"), ge=0, description="Cumulative amount paid for this line item in prior draws"
    )


class AuditRetainageMathOutput(BaseModel):
    """Deterministic retainage audit computation result."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(..., description="Whether the calculation completed without a validation error")
    gross_amount_requested: Decimal | None = Field(None, description="current_billed + stored_materials")
    contractual_retainage_withheld: Decimal | None = Field(
        None, description="gross_amount_requested * contract_retainage_pct"
    )
    net_recommended_release: Decimal | None = Field(
        None, description="gross_amount_requested - contractual_retainage_withheld - prior_payments"
    )
    calculation_trace: list[str] = Field(
        default_factory=list, description="Ordered, human-readable arithmetic steps for the compliance trail"
    )
    error: str | None = Field(None, description="Error message if success is false")


class WaiverFinding(BaseModel):
    """Per-waiver validation finding."""

    model_config = ConfigDict(extra="forbid")

    waiver_id: str = Field(..., description="Waiver identifier")
    finding: Literal["OK", "PRE_DATED_NOTARY", "MISSING_NOTARY_DATE", "TYPE_MISMATCH"] = Field(
        ..., description="Chronological or form check outcome"
    )


class VerifyLienChainIntegrityInput(BaseModel):
    """Input for chronological validation of notarized waiver execution dates against check date."""

    model_config = ConfigDict(extra="forbid")

    waivers: list[LienWaiverRecord] = Field(
        ..., min_length=1, description="All waiver records extracted for this draw (must be non-empty)"
    )
    check_date: date = Field(..., description="Date of the payment/check this draw corresponds to (ISO 8601)")


class VerifyLienChainIntegrityOutput(BaseModel):
    """Deterministic lien-chain validation result."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(..., description="Whether validation completed without a fatal error")
    lien_chain_status: Literal["VALID", "MISSING_WAIVER", "SUSPECT_PRE_DATED_NOTARY", "INVALID_FORM"] | None = Field(
        None, description="Overall lien-chain status for this draw"
    )
    findings: list[WaiverFinding] = Field(default_factory=list, description="Per-waiver chronological findings")
    error: str | None = Field(None, description="Error message if success is false")


class StatutoryPromptPayClockInput(BaseModel):
    """Input for deterministic statutory prompt-pay deadline calculation."""

    model_config = ConfigDict(extra="forbid")

    state_jurisdiction: str = Field(
        ..., min_length=2, max_length=2, description="Two-letter US state postal code (e.g. 'TX', 'CA')"
    )
    invoice_receipt_date: date = Field(..., description="Date payment application was received (ISO 8601)")
    contract_clause: Literal["pay-if-paid", "pay-when-paid"] = Field(
        ..., description="Classified rider clause type — never guessed"
    )


class StatutoryPromptPayClockOutput(BaseModel):
    """Deterministic statutory prompt-pay clock result."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(..., description="Whether lookup and calculation completed without error")
    state: str | None = Field(None, description="Jurisdiction the clock was calculated for")
    days_remaining: int | None = Field(None, description="Days remaining before statutory prompt-pay deadline")
    deadline_timestamp: datetime | None = Field(None, description="Exact statutory deadline timestamp (UTC)")
    penalty_interest_rate: Decimal | None = Field(
        None, description="Applicable monthly penalty interest rate if deadline is missed"
    )
    statute_reference: str | None = Field(None, description="Authoritative legal citation")
    error: str | None = Field(None, description="Error message if success is false")


class DispatchDecisionNotificationInput(BaseModel):
    """Input for sending finalized decision card or urgent escalation alerts to stakeholders."""

    model_config = ConfigDict(extra="forbid")

    notification_type: Literal["DECISION_CARD_READY", "URGENT_STATUTORY_ESCALATION"] = Field(
        ..., description="Which notification template to send"
    )
    project_id: str = Field(..., description="Project this notification relates to")
    draw_number: int = Field(..., ge=1, description="Draw number this notification relates to")
    recipients: list[Literal["GENERAL_CONTRACTOR", "OWNER", "SUBCONTRACTOR"]] = Field(
        ..., min_length=1, description="Stakeholder recipient roles"
    )


class DispatchDecisionNotificationOutput(BaseModel):
    """Notification dispatch confirmation."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(..., description="Whether the notification was accepted for delivery")
    dispatched_to: list[str] = Field(default_factory=list, description="Recipient roles notification was sent to")
    error: str | None = Field(None, description="Error message if success is false")
