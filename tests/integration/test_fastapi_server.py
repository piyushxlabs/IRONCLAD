"""Integration Tests for IRONCLAD FastAPI Sentinel Server Bridge.

Validates:
- GET /api/health endpoint
- POST /api/audit/stream with Server-Sent Events (SSE) parsing
- POST /api/hitl/decide authenticated decision resumption
- GET /api/snapshot/{checkpoint_id} rehydration
- Invariant & security enforcement (immutability of financial inputs, invalid actions)
- CORS headers for Next.js frontend origin (http://localhost:3000)
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from src.server import app
from src.ui.event_types import (
    ApprovalRequiredEvent,
    StateUpdateEvent,
    parse_sse_event,
)


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a Starlette TestClient configured for FastAPI app."""
    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    """Validate /api/health returns service status and runtime mode."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Healthy"
    assert data["service"] == "ironclad-sentinel-fastapi"
    assert "fastapi_version" in data
    assert "pydantic_version" in data


def test_audit_stream_clean_preset_sse(client: TestClient) -> None:
    """Validate POST /api/audit/stream produces valid typed SSE events for clean scenario."""
    session_id = "test_fastapi_clean_session_01"
    payload = {
        "scenario": "simple_clean",
        "runtime_mode": "mock",
        "session_id": session_id,
    }

    response = client.post("/api/audit/stream", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    raw_text = response.text
    assert "event: text-delta" in raw_text
    assert "event: state-update" in raw_text
    assert "event: approval-required" in raw_text
    assert "event: stream-end" in raw_text

    # Parse individual chunks into typed event models
    chunks = [c.strip() for c in raw_text.strip().split("\n\n") if c.strip()]
    parsed_events = [parse_sse_event(c) for c in chunks]

    event_types = [e.event_type.value for e in parsed_events]
    assert "text-delta" in event_types
    assert "state-update" in event_types
    assert "approval-required" in event_types
    assert "stream-end" in event_types

    # Validate approval required event contents
    approval_event = next(e for e in parsed_events if isinstance(e, ApprovalRequiredEvent))
    assert approval_event.checkpoint_id == session_id
    assert approval_event.action_preview.recommended_action == "APPROVE_RELEASE"


def test_audit_stream_defect_preset_sse(client: TestClient) -> None:
    """Validate POST /api/audit/stream handles complex defect scenario with discrepancy flags."""
    session_id = "test_fastapi_defect_session_02"
    payload = {
        "scenario": "complex_defect",
        "runtime_mode": "mock",
        "session_id": session_id,
    }

    response = client.post("/api/audit/stream", json=payload)
    assert response.status_code == 200

    raw_text = response.text
    chunks = [c.strip() for c in raw_text.strip().split("\n\n") if c.strip()]
    parsed_events = [parse_sse_event(c) for c in chunks]

    # Verify flagged discrepancies state update was emitted
    state_updates = [e for e in parsed_events if isinstance(e, StateUpdateEvent)]
    discrepancy_updates = [u for u in state_updates if u.field_name == "flagged_discrepancies"]
    assert len(discrepancy_updates) > 0

    approval_event = next(e for e in parsed_events if isinstance(e, ApprovalRequiredEvent))
    assert approval_event.action_preview.recommended_action in [
        "HOLD_REQUEST_CORRECTED_WAIVER",
        "ESCALATE_LEGAL",
    ]


def test_hitl_decide_and_snapshot_lifecycle(client: TestClient) -> None:
    """Validate end-to-end flow: stream audit -> inspect snapshot -> submit HITL decision."""
    session_id = "test_fastapi_lifecycle_03"

    # Step 1: Run audit stream to pause at HITL interrupt
    stream_resp = client.post(
        "/api/audit/stream",
        json={"scenario": "simple_clean", "runtime_mode": "mock", "session_id": session_id},
    )
    assert stream_resp.status_code == 200

    # Step 2: Retrieve checkpointed snapshot
    snap_resp = client.get(f"/api/snapshot/{session_id}?runtime_mode=mock")
    assert snap_resp.status_code == 200
    snap_data = snap_resp.json()
    assert snap_data["draw_packet_meta"]["project_id"] == "PROJ-SKYLINE-04"
    assert snap_data["approval_state"] is None

    # Step 3: Submit valid HITL decision
    decision_resp = client.post(
        "/api/hitl/decide",
        json={
            "checkpoint_id": session_id,
            "action": "APPROVE_RELEASE",
            "reason": "Verified unconditional lien waiver chain and mathematical calculations.",
            "reviewer_id": "cfo_executive",
            "runtime_mode": "mock",
        },
    )
    assert decision_resp.status_code == 200
    decision_data = decision_resp.json()
    assert decision_data["status"] == "Resumed"
    assert decision_data["checkpoint_id"] == session_id
    assert decision_data["approval_state"]["action"] == "APPROVE_RELEASE"
    assert decision_data["approval_state"]["reviewer_id"] == "cfo_executive"

    # Step 4: Re-read snapshot to confirm terminal resolved state
    snap_post_resp = client.get(f"/api/snapshot/{session_id}?runtime_mode=mock")
    assert snap_post_resp.status_code == 200
    post_data = snap_post_resp.json()
    assert post_data["approval_state"]["action"] == "APPROVE_RELEASE"


def test_hitl_decide_invalid_action(client: TestClient) -> None:
    """Validate that invalid action names return 400 Bad Request."""
    response = client.post(
        "/api/hitl/decide",
        json={
            "checkpoint_id": "any_session",
            "action": "UNAUTHORIZED_PAYMENT_RELEASE",
            "runtime_mode": "mock",
        },
    )
    assert response.status_code == 400
    assert "Invalid HITL action" in response.json()["detail"]


def test_hitl_decide_rejects_financial_mutations(client: TestClient) -> None:
    """Validate that modified_inputs is strictly rejected with 400 Bad Request."""
    response = client.post(
        "/api/hitl/decide",
        json={
            "checkpoint_id": "any_session",
            "action": "APPROVE_RELEASE",
            "modified_inputs": {"net_amount": 50000.00},
            "runtime_mode": "mock",
        },
    )
    assert response.status_code == 400
    assert "Financial immutability violation" in response.json()["detail"]


def test_snapshot_not_found(client: TestClient) -> None:
    """Validate that non-existent checkpoint returns 404 Not Found."""
    response = client.get("/api/snapshot/non_existent_random_id_999?runtime_mode=mock")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_cors_headers(client: TestClient) -> None:
    """Validate CORS preflight and headers for Next.js origin http://localhost:3000."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    response = client.options("/api/audit/stream", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
