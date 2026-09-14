"""Three-Button HITL Resumption Payload Builder and Execution Controller.

Implements the authenticated Human-in-the-Loop decision gateway conforming to:
- INTERFACE_OBSERVABILITY_SYSTEM.md Section 5
- AGENT_ORCHESTRATION_BLUEPRINT.md Section 4 Step 5 & Section 10
- .agents/rules/code-level-verification-over-model-discretion.md
"""

from __future__ import annotations

import logging
from typing import Any

from src.agents.graph import build_ironclad_graph
from src.errors import ApprovalTimeoutError, StateValidationError
from src.state.checkpointing import BaseCheckpointManager, get_checkpoint_manager
from src.state.reducers import HITL_WRITER
from src.state.schema import ApprovalDecision, ApprovalStatus, IroncladState

logger = logging.getLogger("ironclad.ui.hitl_resumption")


async def submit_decision(
    checkpoint_id: str,
    action: str,
    reviewer_id: str = "executive_reviewer",
    notes: str | None = None,
    modified_inputs: dict[str, Any] | None = None,
    checkpoint_manager: BaseCheckpointManager | None = None,
) -> IroncladState:
    """Submits an authenticated human decision to resume graph execution from an interrupt checkpoint.

    Args:
        checkpoint_id: Unique session / checkpoint identifier.
        action: Valid action string ('APPROVE_RELEASE', 'HOLD_REQUEST_CORRECTION', 'ESCALATE_LEGAL').
        reviewer_id: Identifier of authenticated reviewer.
        notes: Optional audit explanation or reason.
        modified_inputs: MUST be None to preserve financial immutability.
        checkpoint_manager: Optional checkpoint store manager.

    Returns:
        Resolved IroncladState at the terminal state.

    Raises:
        StateValidationError: On invalid action enum or non-null modified_inputs.
        ApprovalTimeoutError: If checkpoint cannot be located or is unreadable.
    """
    normalized_action = action.strip().upper() if isinstance(action, str) else ""

    # Validate action enum strictly
    valid_actions = {
        ApprovalStatus.APPROVE_RELEASE.value: ApprovalStatus.APPROVE_RELEASE,
        ApprovalStatus.HOLD_REQUEST_CORRECTION.value: ApprovalStatus.HOLD_REQUEST_CORRECTION,
        ApprovalStatus.ESCALATE_LEGAL.value: ApprovalStatus.ESCALATE_LEGAL,
    }

    if normalized_action not in valid_actions:
        raise StateValidationError(
            message=(
                f"Invalid HITL action: '{action}'. Action must be strictly one of: "
                f"{', '.join(valid_actions.keys())}."
            ),
            incident_context={"action": action, "checkpoint_id": checkpoint_id},
            node_name=HITL_WRITER,
        )

    # Invariant: Financial inputs are strictly immutable after audit
    if modified_inputs is not None:
        raise StateValidationError(
            message="Financial immutability violation: modified_inputs must be None during HITL resumption.",
            incident_context={"modified_inputs": modified_inputs, "checkpoint_id": checkpoint_id},
            node_name=HITL_WRITER,
        )

    manager = checkpoint_manager or get_checkpoint_manager()

    # Load suspended state snapshot from checkpoint
    try:
        paused_state = await manager.read_checkpoint(session_id=checkpoint_id)
    except Exception as exc:
        raise ApprovalTimeoutError(
            message=f"Failed to retrieve checkpoint '{checkpoint_id}': {exc}",
            incident_context={"checkpoint_id": checkpoint_id},
            node_name=HITL_WRITER,
        ) from exc

    if paused_state is None:
        raise ApprovalTimeoutError(
            message=f"Checkpoint '{checkpoint_id}' not found or session has expired.",
            incident_context={"checkpoint_id": checkpoint_id},
            node_name=HITL_WRITER,
        )

    decision = ApprovalDecision(
        action=valid_actions[normalized_action],
        reviewer_id=reviewer_id,
        notes=notes,
        modified_inputs=None,
    )

    graph = build_ironclad_graph()
    terminal_state = await graph.resume_hitl(
        current_state=paused_state,
        decision=decision,
        checkpoint_manager=manager,
        session_id=checkpoint_id,
    )

    logger.info(
        f"[HITL_RESUMPTION_SUCCESS] Checkpoint '{checkpoint_id}' resolved with action "
        f"'{normalized_action}' by reviewer '{reviewer_id}'"
    )
    return terminal_state


async def handle_approve_release(
    checkpoint_id: str,
    reviewer_id: str = "executive_reviewer",
    notes: str | None = None,
    checkpoint_manager: BaseCheckpointManager | None = None,
) -> IroncladState:
    """Button handler for 'Approve Release' action."""
    return await submit_decision(
        checkpoint_id=checkpoint_id,
        action=ApprovalStatus.APPROVE_RELEASE.value,
        reviewer_id=reviewer_id,
        notes=notes,
        checkpoint_manager=checkpoint_manager,
    )


async def handle_hold_request_correction(
    checkpoint_id: str,
    reviewer_id: str = "executive_reviewer",
    notes: str | None = None,
    checkpoint_manager: BaseCheckpointManager | None = None,
) -> IroncladState:
    """Button handler for 'Hold — Request Correction' action."""
    return await submit_decision(
        checkpoint_id=checkpoint_id,
        action=ApprovalStatus.HOLD_REQUEST_CORRECTION.value,
        reviewer_id=reviewer_id,
        notes=notes,
        checkpoint_manager=checkpoint_manager,
    )


async def handle_escalate_legal(
    checkpoint_id: str,
    reviewer_id: str = "executive_reviewer",
    notes: str | None = None,
    checkpoint_manager: BaseCheckpointManager | None = None,
) -> IroncladState:
    """Button handler for 'Escalate to Legal' action."""
    return await submit_decision(
        checkpoint_id=checkpoint_id,
        action=ApprovalStatus.ESCALATE_LEGAL.value,
        reviewer_id=reviewer_id,
        notes=notes,
        checkpoint_manager=checkpoint_manager,
    )
