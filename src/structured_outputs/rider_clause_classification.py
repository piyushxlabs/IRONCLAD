"""Structured Output: RiderClauseClassification.

Adheres strictly to AGENT_LOGIC_SPEC.md Section 5.
Classifies subcontract rider language as pay-if-paid or pay-when-paid (or flags ambiguity).
Used by FairPayStatutoryGuardian.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RiderClauseClassification(BaseModel):
    """Classification of the subcontract rider's payment-conditioning language."""

    model_config = ConfigDict(extra="forbid")

    contract_clause: Literal["pay-if-paid", "pay-when-paid"] | None = Field(
        None, description="Classified clause type; null if ambiguous"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    ambiguous: bool = Field(..., description="True if the clause language could not be confidently classified")


RIDER_CLAUSE_CLASSIFICATION_SCHEMA: dict[str, Any] = {
    "name": "rider_clause_classification",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "contract_clause": {
                "type": ["string", "null"],
                "enum": ["pay-if-paid", "pay-when-paid", None],
                "description": "Classified clause type; null if ambiguous",
            },
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "ambiguous": {"type": "boolean"},
        },
        "required": ["contract_clause", "confidence", "ambiguous"],
        "additionalProperties": False,
    },
}
