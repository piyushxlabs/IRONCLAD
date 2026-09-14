"""Amazon Bedrock AgentCore Runtime Entrypoint for IRONCLAD Sentinel.

Wires the Tri-Track multi-agent DAG into BedrockAgentCoreApp with native
support for:
- Event-driven draw packet audit execution (POST /invocations)
- Streaming Server-Sent Events (SSE) back to client processes
- Resumable Human-in-the-Loop (HITL) gate resolution
- Standardized health check ping endpoints (GET /ping)
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any

from bedrock_agentcore import BedrockAgentCoreApp
from pydantic import ValidationError
from starlette.responses import JSONResponse

from src.agents.graph import build_ironclad_graph
from src.errors import ApprovalTimeoutError, StateValidationError
from src.state.checkpointing import get_checkpoint_manager
from src.state.schema import (
    ApprovalStatus,
    DrawPacketMeta,
    IroncladState,
    RuntimeConfig,
)
from src.ui.event_types import (
    ApprovalRequiredEvent,
    ErrorEvent,
    StateUpdateEvent,
    StreamEndEvent,
    format_sse_event,
)
from src.ui.hitl_resumption import submit_decision

app = BedrockAgentCoreApp(debug=False)


@app.entrypoint
async def entrypoint_handler(
    payload: dict[str, Any],
    context: Any = None,
) -> dict[str, Any] | AsyncGenerator[str, None] | JSONResponse:
    """Primary invocation handler for Amazon Bedrock AgentCore Runtime.

    Args:
        payload: Inbound JSON payload containing action and packet or decision parameters.
        context: BedrockAgentCore RequestContext metadata.

    Returns:
        Serialized state dictionary, async SSE generator, or Starlette JSONResponse.
    """
    if not isinstance(payload, dict):
        return JSONResponse(
            {"error": "Invalid payload format. Expected JSON object."},
            status_code=400,
        )

    action = payload.get("action", "run")

    if action == "ping":
        return {
            "status": "Healthy",
            "service": "ironclad-sentinel",
            "runtime_mode": os.getenv("IRONCLAD_RUNTIME_MODE", "mock"),
        }

    if action == "resume":
        return await _handle_resume_action(payload)

    if action == "run":
        if payload.get("streaming", False):
            return _handle_streaming_run(payload)
        return await _handle_batch_run(payload)

    return JSONResponse(
        {"error": f"Unsupported action: '{action}'. Valid actions: 'run', 'resume', 'ping'."},
        status_code=400,
    )


async def _handle_batch_run(payload: dict[str, Any]) -> dict[str, Any] | JSONResponse:
    """Handles synchronous batch execution of the Tri-Track multi-agent DAG."""
    try:
        raw_meta = payload.get("draw_packet_meta", payload)
        meta = DrawPacketMeta.model_validate(raw_meta)
    except ValidationError as exc:
        return JSONResponse(
            {"error": f"Invalid draw packet metadata: {exc}"},
            status_code=400,
        )
    except (TypeError, KeyError, ValueError) as exc:
        return JSONResponse(
            {"error": f"Malformed packet schema: {exc}"},
            status_code=400,
        )

    runtime_mode = payload.get("runtime_mode", os.getenv("IRONCLAD_RUNTIME_MODE", "mock"))
    runtime_config = RuntimeConfig(
        runtime_mode=runtime_mode,  # type: ignore[arg-type]
        otel_enabled=os.getenv("OPENTELEMETRY_ENABLED", "false").lower() == "true",
    )

    session_id = payload.get("session_id")
    state = IroncladState(
        draw_packet_meta=meta,
        runtime_config=runtime_config,
    )

    try:
        graph = build_ironclad_graph()
        final_state = await graph.execute(state, session_id=session_id)
        return final_state.model_dump(mode="json")
    except StateValidationError as exc:
        return JSONResponse(
            {"error": str(exc), "error_type": "StateValidationError"},
            status_code=400,
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            {"error": f"Internal execution failure: {exc}", "error_type": type(exc).__name__},
            status_code=500,
        )


async def _handle_streaming_run(payload: dict[str, Any]) -> AsyncGenerator[str, None]:
    """Streams SSE events during execution of the Tri-Track multi-agent DAG."""
    try:
        raw_meta = payload.get("draw_packet_meta", payload)
        meta = DrawPacketMeta.model_validate(raw_meta)
    except Exception as exc:  # noqa: BLE001
        yield format_sse_event(
            ErrorEvent(
                message=f"Invalid draw packet metadata: {exc}",
                code="INVALID_PAYLOAD",
            )
        )
        yield format_sse_event(StreamEndEvent(reason="error"))
        return

    runtime_mode = payload.get("runtime_mode", os.getenv("IRONCLAD_RUNTIME_MODE", "mock"))
    runtime_config = RuntimeConfig(
        runtime_mode=runtime_mode,  # type: ignore[arg-type]
        otel_enabled=os.getenv("OPENTELEMETRY_ENABLED", "false").lower() == "true",
    )

    session_id = payload.get("session_id")
    state = IroncladState(
        draw_packet_meta=meta,
        runtime_config=runtime_config,
    )

    try:
        graph = build_ironclad_graph()
        final_state = await graph.execute(state, session_id=session_id)

        # Emit progressive state update snapshot
        if final_state.decision_card_payload:
            yield format_sse_event(
                StateUpdateEvent(
                    field_name="decision_card_payload",
                    reducer="single-writer",
                    value=final_state.decision_card_payload.model_dump(mode="json"),
                    caller_node="EverydayDecisionCardEmitter",
                )
            )

        # Emit approval required event if paused at HITL gate
        if final_state.decision_card_payload and final_state.approval_state is None:
            effective_session_id = session_id or f"session_{final_state.draw_packet_meta.project_id}_{final_state.draw_packet_meta.draw_number}"
            yield format_sse_event(
                ApprovalRequiredEvent(
                    checkpoint_id=effective_session_id,
                    action_preview=final_state.decision_card_payload,
                )
            )
            yield format_sse_event(StreamEndEvent(reason="interrupted"))
        else:
            yield format_sse_event(StreamEndEvent(reason="completed"))

    except Exception as exc:  # noqa: BLE001
        yield format_sse_event(
            ErrorEvent(
                message=str(exc),
                code=type(exc).__name__,
            )
        )
        yield format_sse_event(StreamEndEvent(reason="error"))


async def _handle_resume_action(payload: dict[str, Any]) -> dict[str, Any] | JSONResponse:
    """Handles resumption of a paused execution at the HITL gate."""
    checkpoint_id = payload.get("checkpoint_id") or payload.get("session_id")
    if not checkpoint_id:
        return JSONResponse(
            {"error": "Missing required 'checkpoint_id' or 'session_id' for resumption."},
            status_code=400,
        )

    decision_str = payload.get("decision") or payload.get("approval_status")
    if not decision_str:
        return JSONResponse(
            {"error": "Missing required 'decision' field (APPROVE_RELEASE, HOLD_REQUEST_CORRECTION, ESCALATE_LEGAL)."},
            status_code=400,
        )

    try:
        ApprovalStatus(decision_str)
    except ValueError:
        return JSONResponse(
            {
                "error": f"Invalid decision: '{decision_str}'. Must be one of: {[e.value for e in ApprovalStatus]}."
            },
            status_code=400,
        )

    reviewer_notes = payload.get("reviewer_notes")
    modified_inputs = payload.get("modified_inputs")

    runtime_mode = payload.get("runtime_mode", os.getenv("IRONCLAD_RUNTIME_MODE", "mock"))
    checkpoint_manager = get_checkpoint_manager(runtime_mode)

    try:
        updated_state = await submit_decision(
            checkpoint_id=checkpoint_id,
            action=decision_str,
            notes=reviewer_notes,
            checkpoint_manager=checkpoint_manager,
            modified_inputs=modified_inputs,
        )
        return {
            "status": "Resumed",
            "session_id": checkpoint_id,
            "approval_state": (
                updated_state.approval_state.model_dump(mode="json")
                if updated_state.approval_state
                else None
            ),
            "state": updated_state.model_dump(mode="json"),
        }
    except StateValidationError as exc:
        return JSONResponse(
            {"error": str(exc), "error_type": "StateValidationError"},
            status_code=400,
        )
    except ApprovalTimeoutError as exc:
        return JSONResponse(
            {"error": str(exc), "error_type": "ApprovalTimeoutError"},
            status_code=404,
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            {"error": f"Resumption failure: {exc}", "error_type": type(exc).__name__},
            status_code=500,
        )


def serve(port: int = 8080, host: str | None = None) -> None:
    """Runs the Bedrock AgentCore server."""
    app.run(port=port, host=host or "0.0.0.0")


if __name__ == "__main__":
    serve()
