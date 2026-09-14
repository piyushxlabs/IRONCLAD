"""FastAPI Enterprise Bridge for IRONCLAD Sentinel.

Provides high-performance, non-blocking asynchronous endpoints:
- GET /api/health: Health check, runtime mode, and version telemetry.
- POST /api/audit/stream: Real-time Server-Sent Events (SSE) streaming of multi-agent DAG.
- POST /api/hitl/decide: Resumes paused execution from HITL interrupt checkpoints.
- GET /api/snapshot/{checkpoint_id}: Retrieves state snapshot for instantaneous UI rehydration.
- Permissive CORS for Next.js 15 dashboard (http://localhost:3000).

Conforms strictly to:
- INTERFACE_OBSERVABILITY_SYSTEM.md
- AGENT_ORCHESTRATION_BLUEPRINT.md
- .agents/rules/ui-non-goals-interface-boundaries.md
- .agents/rules/async-io-and-pydantic-validation-mandate.md
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any

import fastapi
import pydantic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from src.agents.graph import build_ironclad_graph
from src.errors import ApprovalTimeoutError, StateValidationError
from src.state.checkpointing import get_checkpoint_manager
from src.state.schema import (
    ApprovalStatus,
    DrawPacketMeta,
    IroncladState,
    RuntimeConfig,
)
from src.ui.app import get_preset_packet
from src.ui.event_types import (
    ApprovalRequiredEvent,
    ErrorEvent,
    StateUpdateEvent,
    StreamEndEvent,
    TextDeltaEvent,
    format_sse_event,
)
from src.ui.hitl_resumption import submit_decision

app = FastAPI(
    title="IRONCLAD Sentinel API Bridge",
    description="Autonomous Retainage & Lien-Discharge Sentinel FastAPI Backend",
    version="0.1.0",
)

# Configure CORS middleware for Next.js development and local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SCENARIO_MAP: dict[str, str] = {
    "simple_clean": "Simple Clean Case (Texas Commercial Masonry)",
    "clean": "Simple Clean Case (Texas Commercial Masonry)",
    "complex_defect": "Complex Defect Case (Pre-Dated Notary Fraud)",
    "defect": "Complex Defect Case (Pre-Dated Notary Fraud)",
    "edge_case": "Edge Case (Ambiguous Pay-if-Paid Rider Clause)",
    "edge": "Edge Case (Ambiguous Pay-if-Paid Rider Clause)",
}


class AuditStreamRequest(BaseModel):
    """Payload for initiating a progressive audit execution stream."""

    model_config = ConfigDict(extra="ignore")

    scenario: str | None = Field(
        default=None,
        description="Preset scenario key: 'simple_clean', 'complex_defect', or 'edge_case'",
    )
    draw_packet_meta: DrawPacketMeta | None = Field(
        default=None,
        description="Explicit draw packet envelope metadata",
    )
    runtime_mode: str | None = Field(
        default=None,
        description="Runtime mode override ('mock', 'staging', 'bedrock')",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional custom session identifier",
    )


class HitlDecisionRequest(BaseModel):
    """Payload for submitting an authenticated Human-in-the-Loop decision."""

    model_config = ConfigDict(extra="ignore")

    checkpoint_id: str = Field(
        ...,
        description="Durable session/checkpoint identifier paused at HITL gate",
    )
    action: str = Field(
        ...,
        description="Approval decision: 'APPROVE_RELEASE', 'HOLD_REQUEST_CORRECTION', or 'ESCALATE_LEGAL'",
    )
    reason: str | None = Field(
        default=None,
        description="Reviewer justification or audit note",
    )
    reviewer_id: str = Field(
        default="executive_reviewer",
        description="Authenticated reviewer identity",
    )
    runtime_mode: str | None = Field(
        default=None,
        description="Runtime mode for checkpoint manager lookup",
    )
    modified_inputs: dict[str, Any] | None = Field(
        default=None,
        description="MUST be None to preserve financial immutability",
    )


@app.get("/api/health")
async def get_health() -> dict[str, Any]:
    """Health check endpoint returning service status, runtime mode, and versioning."""
    return {
        "status": "Healthy",
        "service": "ironclad-sentinel-fastapi",
        "runtime_mode": os.getenv("IRONCLAD_RUNTIME_MODE", "mock"),
        "version": "0.1.0",
        "fastapi_version": fastapi.__version__,
        "pydantic_version": pydantic.__version__,
    }


@app.post("/api/audit/stream")
async def stream_audit(request: AuditStreamRequest) -> StreamingResponse:
    """Executes the Tri-Track multi-agent DAG and streams Server-Sent Events (SSE).

    Ingests preset scenario keys or custom DrawPacketMeta, initializes IroncladState,
    and returns a non-blocking SSE stream conforming to INTERFACE_OBSERVABILITY_SYSTEM.md.
    """
    active_mode = (request.runtime_mode or os.getenv("IRONCLAD_RUNTIME_MODE", "mock")).lower()

    # Resolve input state from preset or explicit payload
    initial_state: IroncladState
    if request.scenario:
        scenario_key = request.scenario.lower().strip()
        preset_title = SCENARIO_MAP.get(scenario_key, "Simple Clean Case (Texas Commercial Masonry)")
        initial_state, _ = get_preset_packet(preset_title, runtime_mode=active_mode)
    elif request.draw_packet_meta:
        initial_state = IroncladState(
            draw_packet_meta=request.draw_packet_meta,
            runtime_config=RuntimeConfig(
                runtime_mode=active_mode,  # type: ignore[arg-type]
                otel_enabled=os.getenv("OPENTELEMETRY_ENABLED", "false").lower() == "true",
            ),
        )
    else:
        # Default fallback to clean case
        initial_state, _ = get_preset_packet(
            "Simple Clean Case (Texas Commercial Masonry)", runtime_mode=active_mode
        )

    session_id = (
        request.session_id
        or f"session_{initial_state.draw_packet_meta.project_id}_{initial_state.draw_packet_meta.draw_number}"
    )

    checkpoint_manager = get_checkpoint_manager(active_mode)

    async def sse_event_generator() -> AsyncGenerator[str, None]:
        try:
            # Emit ingress banner transition
            yield format_sse_event(
                TextDeltaEvent(
                    node="Ingress",
                    content=f"Ingesting draw packet for {initial_state.draw_packet_meta.project_id} (Draw #{initial_state.draw_packet_meta.draw_number})...",
                )
            )

            yield format_sse_event(
                TextDeltaEvent(
                    node="OrchestrationDAG",
                    content="Launching concurrent Fan-Out: ForensicAuditSentinel || FairPayStatutoryGuardian...",
                )
            )

            graph = build_ironclad_graph()
            final_state = await graph.execute(
                initial_state=initial_state,
                checkpoint_manager=checkpoint_manager,
                session_id=session_id,
            )

            # Progressive state snapshot updates
            if final_state.extracted_line_items:
                yield format_sse_event(
                    StateUpdateEvent(
                        field_name="extracted_line_items",
                        reducer="single-writer",
                        value=[item.model_dump(mode="json") for item in final_state.extracted_line_items],
                        caller_node="ForensicAuditSentinel",
                    )
                )

            if final_state.retainage_audit_result:
                yield format_sse_event(
                    StateUpdateEvent(
                        field_name="retainage_audit_result",
                        reducer="single-writer",
                        value=final_state.retainage_audit_result.model_dump(mode="json"),
                        caller_node="ForensicAuditSentinel",
                    )
                )

            if final_state.lien_chain_status:
                yield format_sse_event(
                    StateUpdateEvent(
                        field_name="lien_chain_status",
                        reducer="single-writer",
                        value=final_state.lien_chain_status.value,
                        caller_node="ForensicAuditSentinel",
                    )
                )

            if final_state.statutory_prompt_pay_clock:
                yield format_sse_event(
                    StateUpdateEvent(
                        field_name="statutory_prompt_pay_clock",
                        reducer="single-writer",
                        value=final_state.statutory_prompt_pay_clock.model_dump(mode="json"),
                        caller_node="FairPayStatutoryGuardian",
                    )
                )

            if final_state.flagged_discrepancies:
                yield format_sse_event(
                    StateUpdateEvent(
                        field_name="flagged_discrepancies",
                        reducer="append-only",
                        value=[d.model_dump(mode="json") for d in final_state.flagged_discrepancies],
                        caller_node="ForensicAuditSentinel",
                    )
                )

            if final_state.decision_card_payload:
                yield format_sse_event(
                    StateUpdateEvent(
                        field_name="decision_card_payload",
                        reducer="single-writer",
                        value=final_state.decision_card_payload.model_dump(mode="json"),
                        caller_node="EverydayDecisionCardEmitter",
                    )
                )

            # HITL Interrupt Gate boundary
            if final_state.decision_card_payload and final_state.approval_state is None:
                yield format_sse_event(
                    ApprovalRequiredEvent(
                        checkpoint_id=session_id,
                        action_preview=final_state.decision_card_payload,
                    )
                )
                yield format_sse_event(StreamEndEvent(reason="interrupted"))
            else:
                yield format_sse_event(StreamEndEvent(reason="completed"))

        except Exception as exc:  # noqa: BLE001
            yield format_sse_event(
                ErrorEvent(
                    code=type(exc).__name__,
                    message=f"Audit stream encountered error: {exc}",
                )
            )
            yield format_sse_event(StreamEndEvent(reason="error"))

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/hitl/decide")
async def hitl_decide(request: HitlDecisionRequest) -> dict[str, Any]:
    """Submits an authenticated human decision to resume graph execution from an interrupt checkpoint."""
    if request.modified_inputs is not None:
        raise HTTPException(
            status_code=400,
            detail="Financial immutability violation: modified_inputs must be None during HITL resumption.",
        )

    # Validate action string against ApprovalStatus enum
    valid_actions = {e.value: e for e in ApprovalStatus}
    normalized_action = request.action.strip().upper() if isinstance(request.action, str) else ""

    if normalized_action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid HITL action: '{request.action}'. Action must be strictly one of: {list(valid_actions.keys())}.",
        )

    active_mode = (request.runtime_mode or os.getenv("IRONCLAD_RUNTIME_MODE", "mock")).lower()
    checkpoint_manager = get_checkpoint_manager(active_mode)

    try:
        terminal_state = await submit_decision(
            checkpoint_id=request.checkpoint_id,
            action=normalized_action,
            reviewer_id=request.reviewer_id,
            notes=request.reason,
            checkpoint_manager=checkpoint_manager,
            modified_inputs=None,
        )
        return {
            "status": "Resumed",
            "checkpoint_id": request.checkpoint_id,
            "approval_state": (
                terminal_state.approval_state.model_dump(mode="json")
                if terminal_state.approval_state
                else None
            ),
            "state": terminal_state.model_dump(mode="json"),
        }
    except StateValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ApprovalTimeoutError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Resumption failure: {exc}") from exc


@app.get("/api/snapshot/{checkpoint_id}")
async def get_snapshot(
    checkpoint_id: str,
    runtime_mode: str | None = None,
) -> dict[str, Any]:
    """Retrieves durable checkpointed state snapshot for instantaneous UI rehydration."""
    active_mode = (runtime_mode or os.getenv("IRONCLAD_RUNTIME_MODE", "mock")).lower()
    checkpoint_manager = get_checkpoint_manager(active_mode)

    try:
        state = await checkpoint_manager.read_checkpoint(session_id=checkpoint_id)
        if state is None:
            state = await checkpoint_manager.get_checkpoint(checkpoint_id=checkpoint_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read checkpoint snapshot: {exc}",
        ) from exc

    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Checkpoint '{checkpoint_id}' not found or session has expired.",
        )

    return state.model_dump(mode="json")


def run_server(port: int = 8000, host: str = "0.0.0.0", reload: bool = False) -> None:
    """Entrypoint for running the FastAPI application via uvicorn."""
    import uvicorn

    uvicorn.run("src.server:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    run_server()
