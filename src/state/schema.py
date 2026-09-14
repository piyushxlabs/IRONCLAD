"""IroncladState: Type-Safe Central State Schema.

Adheres strictly to AGENT_ORCHESTRATION_BLUEPRINT.md Section 3 and AGENT_BEHAVIOR_PROFILE.md.
Uses strict Pydantic V2 models (extra="forbid") and Decimal types for financial figures.
"""

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LienChainStatus(str, Enum):
    """Integrity state of the subcontractor lien waiver chain-of-custody."""

    VALID = "VALID"
    MISSING_WAIVER = "MISSING_WAIVER"
    SUSPECT_PRE_DATED_NOTARY = "SUSPECT_PRE_DATED_NOTARY"
    INVALID_FORM = "INVALID_FORM"


class ApprovalStatus(str, Enum):
    """Valid actions permitted at the HITL interrupt checkpoint."""

    APPROVE_RELEASE = "APPROVE_RELEASE"
    HOLD_REQUEST_CORRECTION = "HOLD_REQUEST_CORRECTION"
    ESCALATE_LEGAL = "ESCALATE_LEGAL"


class DrawPacketMeta(BaseModel):
    """Immutable metadata describing the ingested AIA G702/G703 draw application."""

    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(..., description="Unique enterprise project identifier")
    subcontractor_id: str = Field(..., description="Tax ID / enterprise vendor code")
    draw_number: int = Field(..., ge=1, description="Sequential draw application cycle index")
    source_uris: list[str] = Field(..., min_length=1, description="Read-only document URIs")


class LineItem(BaseModel):
    """Audited continuation line item from AIA G703."""

    model_config = ConfigDict(extra="forbid")

    line_item_id: str = Field(..., description="Line item identifier e.g. LI-001")
    description: str = Field(..., description="Description of work or material")
    contract_retainage_pct: Decimal = Field(..., ge=0, le=1, description="Contractual retainage rate e.g. 0.05")
    current_billed: Decimal = Field(..., ge=0, description="Gross work completed this period")
    stored_materials: Decimal = Field(default=Decimal("0.00"), ge=0, description="Materials currently stored")
    prior_payments: Decimal = Field(default=Decimal("0.00"), ge=0, description="Total prior certificates for payment")


class RetainageAuditResult(BaseModel):
    """Deterministic mathematical output from audit_retainage_math."""

    model_config = ConfigDict(extra="forbid")

    gross_amount_requested: Decimal = Field(..., description="Total gross requested (work + materials)")
    contractual_retainage_withheld: Decimal = Field(..., description="Calculated retainage deduction")
    net_recommended_release: Decimal = Field(..., description="Verified net payable amount")
    calculation_trace: list[str] = Field(default_factory=list, description="Deterministic arithmetic steps")


class StatutoryClock(BaseModel):
    """Deterministic statutory prompt-pay computation output."""

    model_config = ConfigDict(extra="forbid")

    state: str = Field(..., min_length=2, max_length=2, description="Two-letter US state postal code")
    days_remaining: int = Field(..., description="Days until statutory payment deadline")
    deadline_timestamp: datetime = Field(..., description="Exact ISO UTC statutory deadline")
    penalty_interest_rate: Decimal = Field(..., ge=0, description="Statutory monthly penalty rate")
    statute_reference: str = Field(..., description="Authoritative legal code citation")


class Discrepancy(BaseModel):
    """Structured audit variance or compliance defect."""

    model_config = ConfigDict(extra="forbid")

    line_item_id: str = Field(..., description="Associated line item or waiver ID")
    discrepancy_type: str = Field(..., description="Discrepancy category e.g. PRE_DATED_NOTARY")
    description: str = Field(..., description="Grounded factual finding with citation")
    variance_amount: Decimal | None = Field(default=None, description="Disputed dollar variance if applicable")


class DecisionCardPayload(BaseModel):
    """Zero-Chat Executive Decision Card deliverable contract."""

    model_config = ConfigDict(extra="forbid")

    draw_number: int = Field(..., ge=1, description="Draw cycle index")
    project_name: str = Field(..., description="Commercial project title")
    subcontractor_trade: str = Field(..., description="Subcontractor trade or division")
    gross_amount_requested: Decimal = Field(..., description="Gross requested funds")
    contractual_retainage_withheld: Decimal = Field(..., description="Total retainage held")
    net_recommended_release: Decimal = Field(..., description="Audited net payable")
    lien_chain_status: LienChainStatus = Field(..., description="Waiver integrity outcome")
    statutory_prompt_pay_clock: StatutoryClock | None = Field(default=None, description="Active prompt-pay timer")
    recommended_action: str = Field(..., description="Deterministic recommendation: APPROVE_RELEASE | HOLD | ESCALATE")
    blocking_discrepancies: list[Discrepancy] = Field(default_factory=list, description="Open compliance defects")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence")


class ApprovalDecision(BaseModel):
    """Authenticated human-in-the-loop decision recorded at the interrupt gate."""

    model_config = ConfigDict(extra="forbid")

    action: ApprovalStatus = Field(..., description="Selected resolution action")
    reviewer_id: str = Field(..., description="Authenticated reviewer identity")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Decision timestamp")
    notes: str | None = Field(default=None, description="Optional reviewer audit notes")
    modified_inputs: dict[str, Any] | None = Field(default=None, description="Must remain None (financial immutability)")


class ToolArtifact(BaseModel):
    """Record of an executed external or deterministic tool."""

    model_config = ConfigDict(extra="forbid")

    tool_call_id: str = Field(..., description="Unique tool invocation identifier")
    tool_name: str = Field(..., description="Name of invoked tool")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    output: dict[str, Any] = Field(default_factory=dict, description="Raw tool execution response")


class ErrorRecord(BaseModel):
    """Typed failure entry recorded in append-only error logs."""

    model_config = ConfigDict(extra="forbid")

    error_id: str = Field(..., description="Unique error identifier")
    node_name: str = Field(..., description="Agent node that encountered failure")
    error_type: str = Field(..., description="Exception class or category")
    message: str = Field(..., description="Descriptive error explanation")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    blocking: bool = Field(default=True, description="Whether this error halts workflow")


class RuntimeConfig(BaseModel):
    """Immutable runtime execution parameters."""

    model_config = ConfigDict(extra="forbid")

    runtime_mode: str = Field(default="staging", description="staging | bedrock | mock")
    max_node_calls: int = Field(default=4, description="Maximum bounded micro-loop iterations")
    otel_enabled: bool = Field(default=True, description="OpenTelemetry dual-export toggle")


class IroncladState(BaseModel):
    """Central Type-Safe State for IRONCLAD Sentinel."""

    model_config = ConfigDict(extra="forbid")

    # Ingress & Configuration (Immutable after init)
    draw_packet_meta: DrawPacketMeta = Field(..., description="Draw application packet envelope")
    runtime_config: RuntimeConfig = Field(default_factory=RuntimeConfig, description="Execution environment config")

    # ForensicAuditSentinel Track (last-write-wins, single-writer)
    extracted_line_items: list[LineItem] = Field(default_factory=list, description="Audited line items")
    retainage_audit_result: RetainageAuditResult | None = Field(default=None, description="Retainage math verification")
    lien_chain_status: LienChainStatus | None = Field(default=None, description="Waiver chronology validation")

    # FairPayStatutoryGuardian Track (last-write-wins, single-writer)
    statutory_prompt_pay_clock: StatutoryClock | None = Field(default=None, description="Prompt pay statutory deadline")

    # Append-Only Cross-Track Audit Logs
    flagged_discrepancies: list[Discrepancy] = Field(default_factory=list, description="Compliance discrepancies")
    error_logs: list[ErrorRecord] = Field(default_factory=list, description="Runtime errors")

    # Everyday Track Deliverable (last-write-wins, single-writer)
    decision_card_payload: DecisionCardPayload | None = Field(default=None, description="Executive decision card")

    # HITL Gate Resumption (last-write-wins, interrupt-handler only)
    approval_state: ApprovalDecision | None = Field(default=None, description="Human sign-off decision")

    # Merge-by-Key Tool Artifacts
    tool_artifacts: dict[str, ToolArtifact] = Field(default_factory=dict, description="Tool execution artifacts")
