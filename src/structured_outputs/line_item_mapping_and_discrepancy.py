"""Structured Output: LineItemMappingAndDiscrepancy.

Adheres strictly to AGENT_LOGIC_SPEC.md Section 5.
Normalizes raw OCR-extracted fields into typed LineItem/Discrepancy state records before any math tool is called.
Used by ForensicAuditSentinel.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.state.schema import Discrepancy, LineItem


class LineItemMappingAndDiscrepancy(BaseModel):
    """Normalization judgment mapping raw extraction output to typed state records."""

    model_config = ConfigDict(extra="forbid")

    normalized_line_items: list[LineItem] = Field(
        ...,
        description="Line items with all fields mapped and validated as ready for audit_retainage_math, or with numeric fields left null if unreadable",
    )
    new_discrepancies: list[Discrepancy] = Field(
        default_factory=list,
        description="Discrepancies to append for any field that could not be confidently mapped",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall mapping confidence for this document",
    )


LINE_ITEM_MAPPING_AND_DISCREPANCY_SCHEMA: dict[str, Any] = {
    "name": "line_item_mapping_and_discrepancy",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "normalized_line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "line_item_id": {"type": "string"},
                        "description": {"type": "string"},
                        "contract_retainage_pct": {"type": "string"},
                        "current_billed": {"type": "string"},
                        "stored_materials": {"type": "string"},
                        "prior_payments": {"type": "string"},
                    },
                    "required": ["line_item_id", "description", "contract_retainage_pct", "current_billed"],
                    "additionalProperties": False,
                },
            },
            "new_discrepancies": {
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
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
        "required": ["normalized_line_items", "new_discrepancies", "confidence"],
        "additionalProperties": False,
    },
}
