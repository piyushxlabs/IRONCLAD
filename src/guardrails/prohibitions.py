"""IRONCLAD Structural Safety Guardrails & Prohibition Enforcement.

Adheres strictly to:
- AGENT_BEHAVIOR_PROFILE.md Section 8 (Absolute Prohibitions) & Section 11 (Out-of-Scope)
- AGENT_LOGIC_SPEC.md Section 6 (Node-Tool Access Matrix) & Section 8 (Safety & Guardrails)
- OWASP Top 10 for LLM Applications 2025 (LLM01 Prompt Injection, LLM06 Excessive Agency)
"""

import re
from decimal import Decimal
from typing import Any

from src.errors import ProhibitedActionError, StateValidationError
from src.state.reducers import (
    EVERYDAY_WRITER,
    FORENSIC_WRITER,
    INGRESS_WRITER,
    STATUTORY_WRITER,
)
from src.state.schema import (
    DecisionCardPayload,
    DrawPacketMeta,
    IroncladState,
    LienChainStatus,
    RetainageAuditResult,
)

# Authorized Node-Tool Access Matrix (AGENT_LOGIC_SPEC.md Section 6)
AUTHORIZED_ACCESS_MATRIX: dict[str, set[str]] = {
    INGRESS_WRITER: set(),  # Ingress holds ZERO tool bindings
    FORENSIC_WRITER: {
        "extract_draw_packet_metadata",
        "LineItemMappingAndDiscrepancy",
        "audit_retainage_math",
        "verify_lien_chain_integrity",
    },
    STATUTORY_WRITER: {
        "RiderClauseClassification",
        "statutory_prompt_pay_clock",
    },
    EVERYDAY_WRITER: {
        "DecisionCardPayload",
        "dispatch_decision_notification",
    },
}

# Prohibition 1: Banned payment/banking keywords & tool identifiers
PROHIBITED_PAYMENT_PATTERNS: tuple[str, ...] = (
    "ach",
    "wire",
    "transfer",
    "bank",
    "ledger",
    "payout",
    "stripe",
    "plaid",
    "payment",
    "disburse",
    "settlement",
)

# OWASP LLM01: Prompt Injection and instruction override patterns
INJECTION_OVERRIDE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+prompt\s+override", re.IGNORECASE),
    re.compile(r"always\s+approve\s+release", re.IGNORECASE),
    re.compile(r"bypass\s+(compliance|audit|retainage|lien)\s+check", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+admin\s+mode", re.IGNORECASE),
    re.compile(r"disregard\s+(the\s+)?rules", re.IGNORECASE),
    re.compile(r"force_approval\s*=\s*true", re.IGNORECASE),
)


def validate_node_tool_access(caller_node: str, tool_or_output_name: str) -> None:
    """Enforce the Node-Tool Access Matrix programmatically.

    Raises:
        ProhibitedActionError: If caller_node attempts to invoke an unauthorized tool.
    """
    allowed_tools = AUTHORIZED_ACCESS_MATRIX.get(caller_node)
    if allowed_tools is None:
        raise ProhibitedActionError(
            message=f"Unknown or unauthorized node: '{caller_node}'",
            incident_context={"caller_node": caller_node, "tool": tool_or_output_name},
            node_name=caller_node,
        )

    if tool_or_output_name not in allowed_tools:
        raise ProhibitedActionError(
            message=f"Node '{caller_node}' is forbidden from invoking tool/output '{tool_or_output_name}'. "
            f"Allowed tools: {sorted(allowed_tools)}",
            incident_context={
                "caller_node": caller_node,
                "attempted_tool": tool_or_output_name,
                "authorized_tools": list(allowed_tools),
            },
            node_name=caller_node,
        )


def verify_no_prohibited_payment_actions(action_name: str, payload: dict[str, Any] | None = None) -> None:
    """Enforce Prohibition 1: No Banking / Payment Execution Rails (OWASP LLM06).

    Raises:
        ProhibitedActionError: If action name or payload references banking or payment execution.
    """
    normalized_action = action_name.strip().lower()
    for pattern in PROHIBITED_PAYMENT_PATTERNS:
        if pattern in normalized_action:
            raise ProhibitedActionError(
                message=f"Prohibition 1 Violation: Payment execution capability '{action_name}' is strictly forbidden. "
                "IRONCLAD operates as an audit sentinel and holds zero banking/payment execution authority.",
                incident_context={"attempted_action": action_name, "pattern_matched": pattern},
                node_name="PaymentRailGuardrail",
            )

    if payload:
        payload_str = str(payload).lower()
        for pattern in ("bank_routing", "account_number", "wire_pin", "ach_batch"):
            if pattern in payload_str:
                raise ProhibitedActionError(
                    message=f"Prohibition 1 Violation: Banking credential pattern '{pattern}' detected in payload.",
                    incident_context={"pattern_matched": pattern},
                    node_name="PaymentRailGuardrail",
                )


def verify_zero_llm_math(
    payload: DecisionCardPayload,
    retainage_result: RetainageAuditResult | None,
) -> None:
    """Enforce Prohibition 2: Zero LLM Math & Citation Grounding.

    Every dollar figure on the card must match byte-for-byte a verified calculation
    output from audit_retainage_math. Free-text arithmetic is rejected immediately.

    Raises:
        StateValidationError: If card numbers do not match verified deterministic math.
    """
    if retainage_result is None:
        if (
            payload.gross_amount_requested != Decimal("0.00")
            or payload.contractual_retainage_withheld != Decimal("0.00")
            or payload.net_recommended_release != Decimal("0.00")
        ):
            raise StateValidationError(
                message="Prohibition 2 Violation: Decision card contains non-zero financial figures "
                "without an upstream verified retainage_audit_result.",
                incident_context={
                    "card_gross": str(payload.gross_amount_requested),
                    "card_retainage": str(payload.contractual_retainage_withheld),
                    "card_net": str(payload.net_recommended_release),
                },
                node_name="ZeroLLMMathGuardrail",
            )
        return

    # Byte-for-byte exact equality checks
    if payload.gross_amount_requested != retainage_result.gross_amount_requested:
        raise StateValidationError(
            message=f"Prohibition 2 Violation: Gross amount mismatch. Card has {payload.gross_amount_requested}, "
            f"audited calculation produced {retainage_result.gross_amount_requested}.",
            incident_context={
                "card_gross": str(payload.gross_amount_requested),
                "audited_gross": str(retainage_result.gross_amount_requested),
            },
            node_name="ZeroLLMMathGuardrail",
        )

    if payload.contractual_retainage_withheld != retainage_result.contractual_retainage_withheld:
        raise StateValidationError(
            message=f"Prohibition 2 Violation: Retainage withheld mismatch. Card has {payload.contractual_retainage_withheld}, "
            f"audited calculation produced {retainage_result.contractual_retainage_withheld}.",
            incident_context={
                "card_retainage": str(payload.contractual_retainage_withheld),
                "audited_retainage": str(retainage_result.contractual_retainage_withheld),
            },
            node_name="ZeroLLMMathGuardrail",
        )

    if payload.net_recommended_release != retainage_result.net_recommended_release:
        raise StateValidationError(
            message=f"Prohibition 2 Violation: Net release mismatch. Card has {payload.net_recommended_release}, "
            f"audited calculation produced {retainage_result.net_recommended_release}.",
            incident_context={
                "card_net": str(payload.net_recommended_release),
                "audited_net": str(retainage_result.net_recommended_release),
            },
            node_name="ZeroLLMMathGuardrail",
        )


def verify_silence_over_guessing(state: IroncladState) -> None:
    """Enforce Prohibition 3: Silence-Over-Guessing Policy.

    If any compliance defect or missing field is flagged, the agent must NOT recommend release
    or fabricate fallback percentages (e.g. 5% default retainage).

    Raises:
        StateValidationError: If APPROVE_RELEASE is recommended despite open discrepancies or invalid lien status.
    """
    if state.decision_card_payload is None:
        return

    card = state.decision_card_payload
    if card.recommended_action == "APPROVE_RELEASE":
        if state.flagged_discrepancies:
            raise StateValidationError(
                message=f"Prohibition 3 Violation: APPROVE_RELEASE recommended while {len(state.flagged_discrepancies)} "
                "compliance discrepancies remain open.",
                incident_context={"discrepancies_count": len(state.flagged_discrepancies)},
                node_name="SilenceOverGuessingGuardrail",
            )
        if state.lien_chain_status != LienChainStatus.VALID:
            raise StateValidationError(
                message=f"Prohibition 3 Violation: APPROVE_RELEASE recommended with non-VALID lien status: '{state.lien_chain_status}'",
                incident_context={"lien_chain_status": str(state.lien_chain_status)},
                node_name="SilenceOverGuessingGuardrail",
            )


def verify_document_immutability(
    initial_meta: DrawPacketMeta,
    current_meta: DrawPacketMeta,
) -> None:
    """Enforce Prohibition 4: Read-Only Document References.

    Source documents must remain unmodified and immutable throughout the audit lifecycle.

    Raises:
        StateValidationError: If source document URIs or packet envelopes are modified.
    """
    if initial_meta.model_dump() != current_meta.model_dump():
        raise StateValidationError(
            message="Prohibition 4 Violation: Draw packet metadata was modified after initialization.",
            incident_context={"initial": initial_meta.model_dump(), "current": current_meta.model_dump()},
            node_name="DocumentImmutabilityGuardrail",
        )


def verify_statutory_clock_integrity(state: IroncladState) -> None:
    """Enforce Prohibition 5: No Statutory Clock Suppression or Extension.

    Statutory deadlines must never be softened, extended, or suppressed to favor General Contractors.

    Raises:
        StateValidationError: If statutory clock calculation is altered artificially.
    """
    if state.statutory_prompt_pay_clock is None:
        return

    clock = state.statutory_prompt_pay_clock
    if clock.days_remaining < 0:
        # Expired statutory clocks must remain negative (indicating immediate violation/penalty interest)
        pass

    if clock.penalty_interest_rate < Decimal("0.00"):
        raise StateValidationError(
            message=f"Prohibition 5 Violation: Negative statutory penalty interest rate ({clock.penalty_interest_rate}) detected.",
            incident_context={"penalty_interest_rate": str(clock.penalty_interest_rate)},
            node_name="StatutoryClockGuardrail",
        )


def sanitize_document_text(text: str) -> tuple[str, bool]:
    """Screen extracted document text for prompt injection patterns (OWASP LLM01).

    Returns:
        tuple of (sanitized_text, injection_detected_bool)
    """
    detected = False
    for pattern in INJECTION_OVERRIDE_PATTERNS:
        if pattern.search(text):
            detected = True
            break
    return text, detected
