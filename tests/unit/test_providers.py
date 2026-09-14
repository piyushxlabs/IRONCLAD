"""Unit tests for the Provider Abstraction Layer."""

import pytest

from src.errors import StateValidationError
from src.providers import (
    BaseRuntimeProtocol,
    BedrockRuntime,
    MockRuntime,
    StagingRuntime,
    get_runtime,
)


def test_provider_protocol_inheritance() -> None:
    """Verify all runtime classes implement BaseRuntimeProtocol."""
    assert issubclass(MockRuntime, BaseRuntimeProtocol)
    assert issubclass(StagingRuntime, BaseRuntimeProtocol)
    assert issubclass(BedrockRuntime, BaseRuntimeProtocol)


def test_get_runtime_factory() -> None:
    """Verify get_runtime correctly instantiates each runtime mode."""
    mock_rt = get_runtime("mock", force_new=True)
    assert isinstance(mock_rt, MockRuntime)

    staging_rt = get_runtime("staging", force_new=True)
    assert isinstance(staging_rt, StagingRuntime)

    bedrock_rt = get_runtime("bedrock", force_new=True)
    assert isinstance(bedrock_rt, BedrockRuntime)


def test_get_runtime_invalid_mode() -> None:
    """Verify invalid runtime mode raises StateValidationError."""
    with pytest.raises(StateValidationError):
        get_runtime("unsupported_cloud_mode", force_new=True)


@pytest.mark.asyncio
async def test_mock_runtime_checkpoint_roundtrip() -> None:
    """Verify MockRuntime checkpoint write, read, and resumption flow."""
    runtime = MockRuntime()
    session_id = "sess_test_123"
    initial_state = {"draw_number": 4, "subcontractor_trade": "Drywall"}

    # Write checkpoint
    cp_id = await runtime.write_checkpoint(session_id, initial_state)
    assert cp_id.startswith("cp_mock_")

    # Read checkpoint
    read_state = await runtime.read_checkpoint(session_id)
    assert read_state == initial_state

    # Resume from checkpoint
    resumption_payload = {"action": "APPROVE_RELEASE", "modified_inputs": None}
    resumed_state = await runtime.resume_from_checkpoint(cp_id, resumption_payload)
    assert resumed_state["approval_state"] == resumption_payload
    assert resumed_state["draw_number"] == 4


@pytest.mark.asyncio
async def test_mock_runtime_invoke_model() -> None:
    """Verify MockRuntime invoke_model execution."""
    runtime = MockRuntime()
    result = await runtime.invoke_model("anthropic.claude-3-5-sonnet-20241022-v2:0", "Audit retainage")
    assert "MOCK_RESPONSE" in result


@pytest.mark.asyncio
async def test_mock_runtime_call_mcp_tool() -> None:
    """Verify MockRuntime tool call returns deterministic structure."""
    runtime = MockRuntime()
    result = await runtime.call_mcp_tool("extract_draw_packet_metadata", {"source_uris": ["s3://test/doc.pdf"]})
    assert result["success"] is True
    assert result["document_type_detected"] == "G703_CONTINUATION"


def test_bedrock_runtime_lazy_initialization() -> None:
    """Verify BedrockRuntime does not initialize AWS clients on construction."""
    runtime = BedrockRuntime(region_name="us-east-1")
    assert runtime._bedrock_runtime_client is None
    assert runtime._agentcore_runtime_client is None
