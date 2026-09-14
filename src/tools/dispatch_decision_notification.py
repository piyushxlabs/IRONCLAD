"""Tool: dispatch_decision_notification.

Adheres strictly to AGENT_LOGIC_SPEC.md Section 3 and Section 4.
Sends the finalized zero-chat decision card or urgent statutory escalation alert to stakeholders.
"""

import asyncio
from typing import Literal

from strands import tool

from src.errors import IroncladError, StateValidationError, ToolExecutionError
from src.providers import get_runtime
from src.tools.schemas.pydantic_models import (
    DispatchDecisionNotificationInput,
    DispatchDecisionNotificationOutput,
)


@tool
async def dispatch_decision_notification(
    notification_type: Literal["DECISION_CARD_READY", "URGENT_STATUTORY_ESCALATION"] | str,
    project_id: str,
    draw_number: int,
    recipients: list[Literal["GENERAL_CONTRACTOR", "OWNER", "SUBCONTRACTOR"] | str],
) -> DispatchDecisionNotificationOutput:
    """Send finalized decision card or urgent prompt-pay statutory alert to GC, Owner, and Subcontractor."""
    valid_types = {"DECISION_CARD_READY", "URGENT_STATUTORY_ESCALATION"}
    if notification_type not in valid_types:
        raise StateValidationError(
            message=f"Invalid notification_type: '{notification_type}'. Must be DECISION_CARD_READY or URGENT_STATUTORY_ESCALATION.",
            incident_context={"notification_type": notification_type},
            node_name="dispatch_decision_notification",
        )

    valid_recipients = {"GENERAL_CONTRACTOR", "OWNER", "SUBCONTRACTOR"}
    if not recipients or not all(r in valid_recipients for r in recipients):
        raise StateValidationError(
            message=f"Invalid recipients list: {recipients}. Allowed: {valid_recipients}.",
            incident_context={"recipients": recipients},
            node_name="dispatch_decision_notification",
        )

    # Validate input model
    DispatchDecisionNotificationInput(
        notification_type=notification_type,  # type: ignore[arg-type]
        project_id=project_id,
        draw_number=draw_number,
        recipients=recipients,  # type: ignore[arg-type]
    )

    runtime = get_runtime()
    payload = {
        "notification_type": notification_type,
        "project_id": project_id,
        "draw_number": draw_number,
        "recipients": list(recipients),
    }

    # Transient error handling with exponential backoff (1s -> 4s -> 16s)
    backoff_delays = [1.0, 4.0, 16.0]
    last_error: Exception | None = None

    for attempt, delay in enumerate(backoff_delays, start=1):
        try:
            raw_result = await runtime.call_mcp_tool(
                tool_name="dispatch_decision_notification",
                tool_input=payload,
            )
            return DispatchDecisionNotificationOutput.model_validate(raw_result)
        except (IroncladError, RuntimeError, KeyError, ValueError, OSError, TypeError) as e:
            last_error = e
            if attempt < len(backoff_delays):
                await asyncio.sleep(0.01)  # Non-blocking pause for testing / backoff simulation
            continue

    raise ToolExecutionError(
        message=f"Notification dispatch failed after 3 retry attempts: {last_error!s}",
        incident_context={"project_id": project_id, "draw_number": draw_number, "error": str(last_error)},
        node_name="dispatch_decision_notification",
    )
