"""Unit tests for Amazon Bedrock AgentCore Runtime main.py entrypoint."""

from __future__ import annotations

import asyncio

import pytest
from starlette.testclient import TestClient

from src.main import app
from src.state.checkpointing import MockCheckpointManager
from src.state.schema import DrawPacketMeta, IroncladState


@pytest.fixture
def client() -> TestClient:
    """TestClient fixture for BedrockAgentCoreApp."""
    return TestClient(app)


def test_ping_endpoint(client: TestClient) -> None:
    """Verify standard GET /ping returns 200 Healthy."""
    response = client.get("/ping")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Healthy"


def test_invocation_ping_action(client: TestClient) -> None:
    """Verify POST /invocations with action='ping'."""
    response = client.post("/invocations", json={"action": "ping"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Healthy"
    assert data["service"] == "ironclad-sentinel"


def test_invocation_batch_run_clean_packet(client: TestClient) -> None:
    """Verify synchronous batch execution against clean mock draw packet."""
    payload = {
        "action": "run",
        "runtime_mode": "mock",
        "draw_packet_meta": {
            "project_id": "PRJ-TEXAS-001",
            "subcontractor_id": "SUB-HVAC-101",
            "draw_number": 4,
            "source_uris": ["tests/mocks/fixtures/draw_4_hvac_invoice.pdf"],
        },
    }
    response = client.post("/invocations", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["draw_packet_meta"]["project_id"] == "PRJ-TEXAS-001"
    assert data["retainage_audit_result"] is not None
    assert data["decision_card_payload"] is not None
    assert data["decision_card_payload"]["recommended_action"] == "APPROVE_RELEASE"
    assert data["approval_state"] is None


def test_invocation_streaming_run(client: TestClient) -> None:
    """Verify streaming execution returning SSE event stream."""
    payload = {
        "action": "run",
        "runtime_mode": "mock",
        "streaming": True,
        "draw_packet_meta": {
            "project_id": "PRJ-TEXAS-001",
            "subcontractor_id": "SUB-HVAC-101",
            "draw_number": 4,
            "source_uris": ["tests/mocks/fixtures/draw_4_hvac_invoice.pdf"],
        },
    }
    response = client.post("/invocations", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")

    content = response.text
    assert "event: state-update" in content
    assert "event: approval-required" in content
    assert "event: stream-end" in content


def test_invocation_resume_action(client: TestClient) -> None:
    """Verify resumption of a paused checkpoint via POST /invocations."""
    # Pre-populate a checkpoint in mock manager
    mock_mgr = MockCheckpointManager()
    session_id = "test-session-resume-101"
    initial_state = IroncladState(
        draw_packet_meta=DrawPacketMeta(
            project_id="PRJ-TEST",
            subcontractor_id="SUB-TEST",
            draw_number=1,
            source_uris=["tests/mocks/fixtures/draw_4_hvac_invoice.pdf"],
        ),
    )
    asyncio.run(mock_mgr.write_checkpoint(session_id, initial_state))

    payload = {
        "action": "resume",
        "runtime_mode": "mock",
        "checkpoint_id": session_id,
        "decision": "APPROVE_RELEASE",
        "reviewer_notes": "All compliance items verified.",
    }
    response = client.post("/invocations", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "Resumed"
    assert data["approval_state"]["action"] == "APPROVE_RELEASE"


def test_invocation_resume_financial_tampering_rejection(client: TestClient) -> None:
    """Verify resumption rejects modified_inputs (financial immutability)."""
    mock_mgr = MockCheckpointManager()
    session_id = "test-session-tamper-101"
    initial_state = IroncladState(
        draw_packet_meta=DrawPacketMeta(
            project_id="PRJ-TEST",
            subcontractor_id="SUB-TEST",
            draw_number=1,
            source_uris=["tests/mocks/fixtures/draw_4_hvac_invoice.pdf"],
        ),
    )
    asyncio.run(mock_mgr.write_checkpoint(session_id, initial_state))

    payload = {
        "action": "resume",
        "runtime_mode": "mock",
        "checkpoint_id": session_id,
        "decision": "APPROVE_RELEASE",
        "modified_inputs": {"net_recommended_release": 999999.00},
    }
    response = client.post("/invocations", json=payload)
    assert response.status_code == 400
    assert "Financial immutability violation" in response.json()["error"]


def test_invocation_unsupported_action(client: TestClient) -> None:
    """Verify unsupported action returns 400."""
    response = client.post("/invocations", json={"action": "unknown_action"})
    assert response.status_code == 400
    assert "Unsupported action" in response.json()["error"]


def test_invocation_invalid_draw_packet(client: TestClient) -> None:
    """Verify invalid draw packet metadata returns 400."""
    response = client.post("/invocations", json={"action": "run", "draw_packet_meta": {}})
    assert response.status_code == 400
    assert "Invalid draw packet metadata" in response.json()["error"]
