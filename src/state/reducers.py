"""IroncladState Reducer Implementations.

Adheres strictly to AGENT_ORCHESTRATION_BLUEPRINT.md Section 3 and Section 4.
Programmatically enforces single-writer boundaries, append-only integrity,
merge-by-key artifact isolation, and immutable input contracts.
"""

from typing import Any

from src.errors import StateValidationError
from src.state.schema import (
    ApprovalDecision,
    DecisionCardPayload,
    Discrepancy,
    DrawPacketMeta,
    ErrorRecord,
    IroncladState,
    LienChainStatus,
    LineItem,
    RetainageAuditResult,
    RuntimeConfig,
    StatutoryClock,
    ToolArtifact,
)

# Authorized writer node mappings
FORENSIC_WRITER = "ForensicAuditSentinel"
STATUTORY_WRITER = "FairPayStatutoryGuardian"
EVERYDAY_WRITER = "EverydayDecisionCardEmitter"
HITL_WRITER = "HITLInterruptHandler"
INGRESS_WRITER = "IngressNode"


def reduce_draw_packet_meta(
    current: DrawPacketMeta,
    update: DrawPacketMeta,
    caller_node: str,
) -> DrawPacketMeta:
    """Reducer for draw_packet_meta (immutable-after-init)."""
    raise StateValidationError(
        message="draw_packet_meta is strictly immutable after graph initialization.",
        incident_context={"caller_node": caller_node, "field": "draw_packet_meta"},
        node_name=caller_node,
    )


def reduce_runtime_config(
    current: RuntimeConfig,
    update: RuntimeConfig,
    caller_node: str,
) -> RuntimeConfig:
    """Reducer for runtime_config (immutable-after-init)."""
    raise StateValidationError(
        message="runtime_config is strictly immutable after initialization.",
        incident_context={"caller_node": caller_node, "field": "runtime_config"},
        node_name=caller_node,
    )


def reduce_extracted_line_items(
    current: list[LineItem],
    update: list[LineItem],
    caller_node: str,
) -> list[LineItem]:
    """Reducer for extracted_line_items (last-write-wins, ForensicAuditSentinel only)."""
    if caller_node != FORENSIC_WRITER:
        raise StateValidationError(
            message=f"Only {FORENSIC_WRITER} may write to extracted_line_items. Caller '{caller_node}' rejected.",
            incident_context={"caller_node": caller_node, "field": "extracted_line_items"},
            node_name=caller_node,
        )
    return list(update)


def reduce_retainage_audit_result(
    current: RetainageAuditResult | None,
    update: RetainageAuditResult | None,
    caller_node: str,
) -> RetainageAuditResult | None:
    """Reducer for retainage_audit_result (last-write-wins, ForensicAuditSentinel only)."""
    if caller_node != FORENSIC_WRITER:
        raise StateValidationError(
            message=f"Only {FORENSIC_WRITER} may write to retainage_audit_result. Caller '{caller_node}' rejected.",
            incident_context={"caller_node": caller_node, "field": "retainage_audit_result"},
            node_name=caller_node,
        )
    return update


def reduce_lien_chain_status(
    current: LienChainStatus | None,
    update: LienChainStatus | None,
    caller_node: str,
) -> LienChainStatus | None:
    """Reducer for lien_chain_status (last-write-wins, ForensicAuditSentinel only)."""
    if caller_node != FORENSIC_WRITER:
        raise StateValidationError(
            message=f"Only {FORENSIC_WRITER} may write to lien_chain_status. Caller '{caller_node}' rejected.",
            incident_context={"caller_node": caller_node, "field": "lien_chain_status"},
            node_name=caller_node,
        )
    return update


def reduce_statutory_prompt_pay_clock(
    current: StatutoryClock | None,
    update: StatutoryClock | None,
    caller_node: str,
) -> StatutoryClock | None:
    """Reducer for statutory_prompt_pay_clock (last-write-wins, FairPayStatutoryGuardian only)."""
    if caller_node != STATUTORY_WRITER:
        raise StateValidationError(
            message=f"Only {STATUTORY_WRITER} may write to statutory_prompt_pay_clock. Caller '{caller_node}' rejected.",
            incident_context={"caller_node": caller_node, "field": "statutory_prompt_pay_clock"},
            node_name=caller_node,
        )
    return update


def reduce_flagged_discrepancies(
    current: list[Discrepancy],
    update: list[Discrepancy] | Discrepancy,
    caller_node: str,
) -> list[Discrepancy]:
    """Reducer for flagged_discrepancies (append-only across authorized nodes)."""
    allowed_nodes = {FORENSIC_WRITER, STATUTORY_WRITER, EVERYDAY_WRITER, INGRESS_WRITER}
    if caller_node not in allowed_nodes:
        raise StateValidationError(
            message=f"Caller '{caller_node}' not permitted to append to flagged_discrepancies.",
            incident_context={"caller_node": caller_node, "field": "flagged_discrepancies"},
            node_name=caller_node,
        )
    result = list(current)
    if isinstance(update, list):
        result.extend(update)
    elif isinstance(update, Discrepancy):
        result.append(update)
    return result


def reduce_decision_card_payload(
    current: DecisionCardPayload | None,
    update: DecisionCardPayload | None,
    caller_node: str,
) -> DecisionCardPayload | None:
    """Reducer for decision_card_payload (last-write-wins, EverydayDecisionCardEmitter only)."""
    if caller_node != EVERYDAY_WRITER:
        raise StateValidationError(
            message=f"Only {EVERYDAY_WRITER} may write to decision_card_payload. Caller '{caller_node}' rejected.",
            incident_context={"caller_node": caller_node, "field": "decision_card_payload"},
            node_name=caller_node,
        )
    return update


def reduce_approval_state(
    current: ApprovalDecision | None,
    update: ApprovalDecision | None,
    caller_node: str,
) -> ApprovalDecision | None:
    """Reducer for approval_state (last-write-wins, HITLInterruptHandler only)."""
    if caller_node not in {HITL_WRITER, "human_reviewer"}:
        raise StateValidationError(
            message=f"Only {HITL_WRITER} may write to approval_state. Caller '{caller_node}' rejected.",
            incident_context={"caller_node": caller_node, "field": "approval_state"},
            node_name=caller_node,
        )
    return update


def reduce_tool_artifacts(
    current: dict[str, ToolArtifact],
    update: dict[str, ToolArtifact] | ToolArtifact,
    caller_node: str,
) -> dict[str, ToolArtifact]:
    """Reducer for tool_artifacts (merge-by-key, keyed by tool_call_id)."""
    result = current.copy()
    if isinstance(update, ToolArtifact):
        result[update.tool_call_id] = update
    elif isinstance(update, dict):
        for k, v in update.items():
            if isinstance(v, ToolArtifact):
                result[k] = v
            else:
                result[k] = ToolArtifact.model_validate(v)
    return result


def reduce_error_logs(
    current: list[ErrorRecord],
    update: list[ErrorRecord] | ErrorRecord,
    caller_node: str,
) -> list[ErrorRecord]:
    """Reducer for error_logs (append-only, universally writable)."""
    result = list(current)
    if isinstance(update, list):
        result.extend(update)
    elif isinstance(update, ErrorRecord):
        result.append(update)
    return result


def apply_state_update(
    state: IroncladState,
    updates: dict[str, Any],
    caller_node: str,
) -> IroncladState:
    """Apply partial state mutations through the declared reducer boundary."""
    state_dict = state.model_dump()

    for key, value in updates.items():
        if key == "draw_packet_meta":
            reduce_draw_packet_meta(state.draw_packet_meta, value, caller_node)
        elif key == "runtime_config":
            reduce_runtime_config(state.runtime_config, value, caller_node)
        elif key == "extracted_line_items":
            state_dict["extracted_line_items"] = reduce_extracted_line_items(
                state.extracted_line_items, value, caller_node
            )
        elif key == "retainage_audit_result":
            state_dict["retainage_audit_result"] = reduce_retainage_audit_result(
                state.retainage_audit_result, value, caller_node
            )
        elif key == "lien_chain_status":
            state_dict["lien_chain_status"] = reduce_lien_chain_status(
                state.lien_chain_status, value, caller_node
            )
        elif key == "statutory_prompt_pay_clock":
            state_dict["statutory_prompt_pay_clock"] = reduce_statutory_prompt_pay_clock(
                state.statutory_prompt_pay_clock, value, caller_node
            )
        elif key == "flagged_discrepancies":
            state_dict["flagged_discrepancies"] = reduce_flagged_discrepancies(
                state.flagged_discrepancies, value, caller_node
            )
        elif key == "decision_card_payload":
            state_dict["decision_card_payload"] = reduce_decision_card_payload(
                state.decision_card_payload, value, caller_node
            )
        elif key == "approval_state":
            state_dict["approval_state"] = reduce_approval_state(
                state.approval_state, value, caller_node
            )
        elif key == "tool_artifacts":
            state_dict["tool_artifacts"] = reduce_tool_artifacts(
                state.tool_artifacts, value, caller_node
            )
        elif key == "error_logs":
            state_dict["error_logs"] = reduce_error_logs(
                state.error_logs, value, caller_node
            )
        else:
            raise StateValidationError(
                message=f"Attempted write to unknown state field: '{key}'",
                incident_context={"caller_node": caller_node, "field": key},
                node_name=caller_node,
            )

    return IroncladState.model_validate(state_dict)
