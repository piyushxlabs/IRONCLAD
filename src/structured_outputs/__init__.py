"""Structured Output Definitions Package."""

from src.structured_outputs.decision_card_payload import (
    DECISION_CARD_PAYLOAD_SCHEMA,
    DecisionCardStructuredOutput,
    FlaggedDiscrepancyEntry,
    StatutoryClockSummary,
)
from src.structured_outputs.line_item_mapping_and_discrepancy import (
    LINE_ITEM_MAPPING_AND_DISCREPANCY_SCHEMA,
    LineItemMappingAndDiscrepancy,
)
from src.structured_outputs.rider_clause_classification import (
    RIDER_CLAUSE_CLASSIFICATION_SCHEMA,
    RiderClauseClassification,
)

__all__ = [
    "DECISION_CARD_PAYLOAD_SCHEMA",
    "LINE_ITEM_MAPPING_AND_DISCREPANCY_SCHEMA",
    "RIDER_CLAUSE_CLASSIFICATION_SCHEMA",
    "DecisionCardStructuredOutput",
    "FlaggedDiscrepancyEntry",
    "LineItemMappingAndDiscrepancy",
    "RiderClauseClassification",
    "StatutoryClockSummary",
]
