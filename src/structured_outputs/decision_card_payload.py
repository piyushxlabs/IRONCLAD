"""Structured Output: DecisionCardPayload.

Adheres strictly to AGENT_LOGIC_SPEC.md Section 5 and AGENT_BEHAVIOR_PROFILE.md Section 4.
Assembles the final, single zero-chat Executive Decision Card deliverable.
Used by EverydayDecisionCardEmitter.
"""

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FlaggedDiscrepancyEntry(BaseModel):
    """Structured discrepancy item on the executive card."""

    model_config = ConfigDict(extra="forbid")

    line_item_id: str
    discrepancy_type: str
    description: str
    variance_amount: Decimal | None = None


class StatutoryClockSummary(BaseModel):
    """Statutory countdown snapshot on the executive card."""

    model_config = ConfigDict(extra="forbid")

    state: str
    days_remaining: int
    deadline_timestamp: str
    penalty_interest_rate: Decimal


class DecisionCardStructuredOutput(BaseModel):
    """The single zero-chat, 1-click decision card — matches AGENT_BEHAVIOR_PROFILE.md Section 4 Deliverable Contract exactly."""

    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(..., description="Copied verbatim from draw_packet_meta")
    subcontractor_name: str = Field(..., description="Copied verbatim from extracted_line_items context")
    draw_number: int = Field(..., description="Copied verbatim from draw_packet_meta")
    gross_amount_requested: Decimal = Field(
        ..., description="Copied verbatim from retainage_audit_result — never recomputed here"
    )
    contractual_retainage_withheld: Decimal = Field(
        ..., description="Copied verbatim from retainage_audit_result"
    )
    net_recommended_release: Decimal = Field(..., description="Copied verbatim from retainage_audit_result")
    flagged_discrepancies: list[FlaggedDiscrepancyEntry] = Field(
        default_factory=list, description="Copied verbatim from flagged_discrepancies state field"
    )
    lien_chain_status: Literal["VALID", "MISSING_WAIVER", "SUSPECT_PRE_DATED_NOTARY", "INVALID_FORM"] = Field(
        ..., description="Copied verbatim from lien_chain_status"
    )
    statutory_prompt_pay_clock: StatutoryClockSummary = Field(
        ..., description="Copied verbatim from statutory_prompt_pay_clock"
    )
    recommended_action: Literal[
        "APPROVE_RELEASE", "HOLD_REQUEST_CORRECTED_WAIVER", "ESCALATE_LEGAL"
    ] = Field(
        ...,
        description="Fixed-rule decision: APPROVE_RELEASE only if flagged_discrepancies is empty AND lien_chain_status is VALID",
    )


DECISION_CARD_PAYLOAD_SCHEMA: dict[str, Any] = {
    "name": "decision_card_payload",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "subcontractor_name": {"type": "string"},
            "draw_number": {"type": "integer"},
            "gross_amount_requested": {"type": "string"},
            "contractual_retainage_withheld": {"type": "string"},
            "net_recommended_release": {"type": "string"},
            "flagged_discrepancies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "line_item_id": {"type": "string"},
                        "discrepancy_type": {"type": "string"},
                        "description": {"type": "string"},
                        "variance_amount": {"type": ["string", "null"]},
                    },
                    "required": ["line_item_id", "discrepancy_type", "description"],
                    "additionalProperties": False,
                },
            },
            "lien_chain_status": {
                "type": "string",
                "enum": ["VALID", "MISSING_WAIVER", "SUSPECT_PRE_DATED_NOTARY", "INVALID_FORM"],
            },
            "statutory_prompt_pay_clock": {
                "type": "object",
                "properties": {
                    "state": {"type": "string"},
                    "days_remaining": {"type": "integer"},
                    "deadline_timestamp": {"type": "string"},
                    "penalty_interest_rate": {"type": "string"},
                },
                "required": ["state", "days_remaining", "deadline_timestamp", "penalty_interest_rate"],
                "additionalProperties": False,
            },
            "recommended_action": {
                "type": "string",
                "enum": ["APPROVE_RELEASE", "HOLD_REQUEST_CORRECTED_WAIVER", "ESCALATE_LEGAL"],
            },
        },
        "required": [
            "project_id",
            "subcontractor_name",
            "draw_number",
            "gross_amount_requested",
            "contractual_retainage_withheld",
            "net_recommended_release",
            "flagged_discrepancies",
            "lien_chain_status",
            "statutory_prompt_pay_clock",
            "recommended_action",
        ],
        "additionalProperties": False,
    },
}
