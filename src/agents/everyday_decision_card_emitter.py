"""EverydayDecisionCardEmitter Node — Everyday Track.

Synthesizes audited upstream state into the zero-chat 1-click Executive Decision Card,
enforces deterministic release recommendation logic in code, and dispatches stakeholder notifications.

Adheres strictly to:
- AGENT_LOGIC_SPEC.md Section 1, 2 & 6
- AGENT_BEHAVIOR_PROFILE.md Section 4 (Deliverable Contract) & Section 9
- .agents/rules/code-level-verification-over-model-discretion.md
- .agents/rules/ui-non-goals-interface-boundaries.md
"""

from decimal import Decimal
import hashlib
from typing import Any
import uuid

from src.models import ModelInvoker, get_model_invoker
from src.state.reducers import EVERYDAY_WRITER
from src.state.schema import (
    DecisionCardPayload,
    ErrorRecord,
    IroncladState,
    LienChainStatus,
    ToolArtifact,
)
from src.tools.dispatch_decision_notification import dispatch_decision_notification

MAX_NODE_CALLS = 4

EVERYDAY_DECISION_CARD_EMITTER_SYSTEM_PROMPT = """<identity_and_role>
You are EverydayDecisionCardEmitter, the everyday-track node of the IRONCLAD Strands GraphBuilder graph.
You run only after both ForensicAuditSentinel and FairPayStatutoryGuardian have completed.
Your purpose is to collapse their verified outputs into the single zero-chat DecisionCardPayload and hand
the graph to the mandatory human-approval interrupt.
</identity_and_role>

<primary_objective>
Read the completed audit and statutory state, apply the fixed recommended_action rule (never inferred),
and emit a DecisionCardPayload via structured output. Think step-by-step: check for any blocking error or
open discrepancy before assembling the card — a card must never present numbers as clean when either
upstream track flagged a problem.
</primary_objective>

<context_and_state_access>
You have read access to (read-only for you):
- draw_packet_meta, extracted_line_items, retainage_audit_result, lien_chain_status,
  statutory_prompt_pay_clock, flagged_discrepancies, error_logs

You may write to, using its declared reducer:
- decision_card_payload: DecisionCardPayload | None — reducer: last-write-wins (you are the sole writer)
- tool_artifacts: dict[str, ToolArtifact] — reducer: merge-by-key, keyed by tool_call_id (notification dispatch only)
- error_logs: list[ErrorRecord] — reducer: append-only (shared writer)

You have NO write access to any audit-origin field (extracted_line_items, retainage_audit_result,
lien_chain_status, statutory_prompt_pay_clock) — these are read-only inputs to you.
</context_and_state_access>

<available_tools_and_triggers>
- DecisionCardPayload (structured output): invoke once, after confirming both upstream tracks completed without a blocking error
- dispatch_decision_notification: invoke once, after DecisionCardPayload is written, to notify GC/Owner/Subcontractor
</available_tools_and_triggers>

<hard_constraints_and_prohibitions>
You must NEVER:
- Recompute, adjust, or "round" any figure from retainage_audit_result or statutory_prompt_pay_clock — copy verified values only.
- Call any math, date-math, or OCR tool — none is bound to you.
- Set recommended_action to APPROVE_RELEASE if flagged_discrepancies is non-empty or lien_chain_status is not VALID — the rule is fixed, not a judgment call: any open discrepancy or non-VALID lien status forces HOLD_REQUEST_CORRECTED_WAIVER or ESCALATE_LEGAL per severity.
- Call dispatch_decision_notification before decision_card_payload has been written in this same turn.
You must STOP (write a blocking error_logs entry, do not write decision_card_payload) when:
- Either upstream track wrote a blocking error_logs entry instead of completing its audit fields.
</hard_constraints_and_prohibitions>
"""


async def everyday_decision_card_emitter_node(
    state: IroncladState,
    invoker: ModelInvoker | None = None,
    dispatch_alert: bool = True,
) -> dict[str, Any]:
    """Execute the EverydayDecisionCardEmitter Everyday Track node micro-loop.

    Reasoning Steps:
    1. Upstream circuit-breaker screening: If blocking errors exist, halt with INCOMPLETE_MANUAL_AUDIT_REQUIRED.
    2. Deterministic Code-Level Release Gating:
       - APPROVE_RELEASE ONLY if len(flagged_discrepancies) == 0 AND lien_chain_status == VALID.
       - ESCALATE_LEGAL if SUSPECT_PRE_DATED_NOTARY detected.
       - HOLD_REQUEST_CORRECTED_WAIVER for all other compliance defects.
    3. Exact Citation Grounding: Copy verified Decimal figures from retainage_audit_result.
    4. Notification Dispatch: Notify GC/Owner/Subcontractor channels.

    Args:
        state: Immutable snapshot of current IroncladState with merged upstream outputs.
        invoker: Optional model invocation double.
        dispatch_alert: Whether to trigger stakeholder notification dispatch.

    Returns:
        Dictionary of state updates conforming to EverydayDecisionCardEmitter write permissions.
    """
    if invoker is None:
        invoker = get_model_invoker(state.runtime_config.runtime_mode)

    call_count = 0
    executed_call_signatures: set[str] = set()

    new_artifacts: dict[str, ToolArtifact] = {}
    new_errors: list[ErrorRecord] = []

    # 1. Circuit Breaker Check: Halt if blocking upstream errors exist
    blocking_errors = [e for e in state.error_logs if e.blocking]
    if blocking_errors:
        new_errors.append(
            ErrorRecord(
                error_id=str(uuid.uuid4()),
                node_name=EVERYDAY_WRITER,
                error_type="CircuitBreakerTripped",
                message="Blocking errors present in upstream tracks. Routing to INCOMPLETE_MANUAL_AUDIT_REQUIRED without emitting release figures.",
                blocking=True,
            )
        )
        return {"error_logs": new_errors}

    # 2. Fixed Decision Logic for Fund Release (Deterministic Python Code, Zero LLM Discretion)
    if len(state.flagged_discrepancies) == 0 and state.lien_chain_status == LienChainStatus.VALID:
        recommended_action = "APPROVE_RELEASE"
    elif (
        state.lien_chain_status == LienChainStatus.SUSPECT_PRE_DATED_NOTARY
        or any(d.discrepancy_type == "SUSPECT_PRE_DATED_NOTARY" for d in state.flagged_discrepancies)
    ):
        recommended_action = "ESCALATE_LEGAL"
    else:
        recommended_action = "HOLD_REQUEST_CORRECTED_WAIVER"

    # 3. Citation Grounding & Zero LLM Math: Exact reflection of audited numbers
    if state.retainage_audit_result is not None:
        gross_amt = state.retainage_audit_result.gross_amount_requested
        retainage_held = state.retainage_audit_result.contractual_retainage_withheld
        net_release = state.retainage_audit_result.net_recommended_release
    else:
        gross_amt = Decimal("0.00")
        retainage_held = Decimal("0.00")
        net_release = Decimal("0.00")

    lien_status = state.lien_chain_status or LienChainStatus.MISSING_WAIVER

    # 4. Construct DecisionCardPayload
    payload = DecisionCardPayload(
        draw_number=state.draw_packet_meta.draw_number,
        project_name=f"Project {state.draw_packet_meta.project_id}",
        subcontractor_trade=f"Subcontractor {state.draw_packet_meta.subcontractor_id}",
        gross_amount_requested=gross_amt,
        contractual_retainage_withheld=retainage_held,
        net_recommended_release=net_release,
        lien_chain_status=lien_status,
        statutory_prompt_pay_clock=state.statutory_prompt_pay_clock,
        recommended_action=recommended_action,
        blocking_discrepancies=list(state.flagged_discrepancies),
        confidence_score=1.0 if not state.flagged_discrepancies else 0.85,
    )

    # 5. Dispatch Decision Notification (Notification MCP)
    if dispatch_alert and call_count < MAX_NODE_CALLS:
        sig = hashlib.sha256(
            f"notify:{state.draw_packet_meta.project_id}:{state.draw_packet_meta.draw_number}:{recommended_action}".encode()
        ).hexdigest()

        if sig not in executed_call_signatures:
            executed_call_signatures.add(sig)
            call_count += 1
            call_id = f"notify_{uuid.uuid4().hex[:8]}"
            try:
                notification_output = await dispatch_decision_notification(
                    notification_type="DECISION_CARD_READY",
                    project_id=state.draw_packet_meta.project_id,
                    draw_number=state.draw_packet_meta.draw_number,
                    recipients=["GENERAL_CONTRACTOR", "OWNER", "SUBCONTRACTOR"],
                    summary=f"IRONCLAD Audit Complete: Recommendation is {recommended_action} (Net: ${net_release:,.2f})",
                )
                new_artifacts[call_id] = ToolArtifact(
                    tool_call_id=call_id,
                    tool_name="dispatch_decision_notification",
                    output=notification_output.model_dump(mode="json"),
                )
            except Exception as e:
                new_errors.append(
                    ErrorRecord(
                        error_id=str(uuid.uuid4()),
                        node_name=EVERYDAY_WRITER,
                        error_type=type(e).__name__,
                        message=f"Failed to dispatch decision notification: {e}",
                        blocking=False,
                    )
                )

    # Return mutations for fields owned by EverydayDecisionCardEmitter
    return {
        "decision_card_payload": payload,
        "tool_artifacts": new_artifacts,
        "error_logs": new_errors,
    }
