"""Strict OpenAPI / JSON Schema / MCP Tool Definitions.

Adheres strictly to AGENT_LOGIC_SPEC.md Section 4 and AGENT_MASTER_PLAN.md Section 5.
Provides strict function-calling JSON schemas for all five tools dual-compatible with
Amazon Bedrock AgentCore and Google GenAI.
"""

from typing import Any

EXTRACT_DRAW_PACKET_METADATA_SCHEMA: dict[str, Any] = {
    "name": "extract_draw_packet_metadata",
    "description": "Form-aware OCR and key-value extraction of AIA G702/G703 fields and lien waiver records from a source draw-packet PDF.",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "pdf_uri": {
                "type": "string",
                "description": "URI of the source PDF within the read-only document intake bucket (e.g. an s3:// URI)",
            }
        },
        "required": ["pdf_uri"],
        "additionalProperties": False,
    },
}

AUDIT_RETAINAGE_MATH_SCHEMA: dict[str, Any] = {
    "name": "audit_retainage_math",
    "description": "Deterministic math engine for verifying retainage withholding and net recommended release for a single draw-packet line item.",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "contract_retainage_pct": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Contractual retainage percentage, e.g. 0.05 for 5%",
            },
            "current_billed": {
                "type": "string",
                "description": 'Amount billed this period for this line item, as a decimal string (e.g. "12000.00")',
            },
            "stored_materials": {
                "type": "string",
                "description": "Value of materials stored but not yet installed, as a decimal string",
            },
            "prior_payments": {
                "type": "string",
                "description": "Cumulative amount paid for this line item in prior draws, as a decimal string",
            },
        },
        "required": ["contract_retainage_pct", "current_billed", "stored_materials", "prior_payments"],
        "additionalProperties": False,
    },
}

VERIFY_LIEN_CHAIN_INTEGRITY_SCHEMA: dict[str, Any] = {
    "name": "verify_lien_chain_integrity",
    "description": "Validates the chronological sequence of notarized lien waiver execution dates against the payment/check date, and classifies overall lien-chain status.",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "waivers": {
                "type": "array",
                "description": "All waiver records extracted for this draw",
                "items": {
                    "type": "object",
                    "properties": {
                        "waiver_id": {
                            "type": "string",
                            "description": "Stable identifier for this waiver document",
                        },
                        "waiver_type": {
                            "type": "string",
                            "enum": [
                                "CONDITIONAL_PROGRESS",
                                "UNCONDITIONAL_PROGRESS",
                                "CONDITIONAL_FINAL",
                                "UNCONDITIONAL_FINAL",
                            ],
                            "description": "Statutory waiver form type",
                        },
                        "notary_execution_date": {
                            "type": ["string", "null"],
                            "description": "Date the waiver was notarized, ISO 8601 (YYYY-MM-DD); null if illegible",
                        },
                        "associated_line_item_id": {
                            "type": ["string", "null"],
                            "description": "Line item this waiver corresponds to, if determinable",
                        },
                    },
                    "required": ["waiver_id", "waiver_type", "notary_execution_date", "associated_line_item_id"],
                    "additionalProperties": False,
                },
            },
            "check_date": {
                "type": "string",
                "description": "Date of the payment/check this draw corresponds to, ISO 8601 (YYYY-MM-DD)",
            },
        },
        "required": ["waivers", "check_date"],
        "additionalProperties": False,
    },
}

STATUTORY_PROMPT_PAY_CLOCK_SCHEMA: dict[str, Any] = {
    "name": "statutory_prompt_pay_clock",
    "description": "Statutory deadline tracker: calculates the prompt-payment countdown, deadline, and applicable penalty interest rate for a given jurisdiction, invoice date, and rider clause classification.",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "state_jurisdiction": {
                "type": "string",
                "description": "Two-letter US state postal code governing the project (e.g. 'TX', 'CA')",
            },
            "invoice_receipt_date": {
                "type": "string",
                "description": "Date the payment application/invoice was received, ISO 8601 (YYYY-MM-DD)",
            },
            "contract_clause": {
                "type": "string",
                "enum": ["pay-if-paid", "pay-when-paid"],
                "description": "Classified rider clause type, from RiderClauseClassification — never guessed",
            },
        },
        "required": ["state_jurisdiction", "invoice_receipt_date", "contract_clause"],
        "additionalProperties": False,
    },
}

DISPATCH_DECISION_NOTIFICATION_SCHEMA: dict[str, Any] = {
    "name": "dispatch_decision_notification",
    "description": "Sends the finalized zero-chat decision card or an urgent statutory-deadline escalation alert to General Contractor, Owner, and/or Subcontractor notification channels.",
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "notification_type": {
                "type": "string",
                "enum": ["DECISION_CARD_READY", "URGENT_STATUTORY_ESCALATION"],
                "description": "Which notification template to send",
            },
            "project_id": {
                "type": "string",
                "description": "Project this notification relates to",
            },
            "draw_number": {
                "type": "integer",
                "minimum": 1,
                "description": "Draw number this notification relates to",
            },
            "recipients": {
                "type": "array",
                "description": "Which stakeholder roles receive this notification",
                "items": {
                    "type": "string",
                    "enum": ["GENERAL_CONTRACTOR", "OWNER", "SUBCONTRACTOR"],
                },
                "minItems": 1,
            },
        },
        "required": ["notification_type", "project_id", "draw_number", "recipients"],
        "additionalProperties": False,
    },
}
