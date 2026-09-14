"""Unit tests for Model Allocation and Invoker Service."""

import pytest
from pydantic import BaseModel, Field

from src.models import (
    ModelCatalog,
    ModelInvoker,
    ModelRole,
    default_invoker,
)
from src.providers.mock_runtime import MockRuntime


class SampleStructuredOutput(BaseModel):
    summary: str = Field(default="test summary")
    score: float = Field(default=1.0)


def test_model_catalog_resolution() -> None:
    """Verify model ID resolution across roles and runtimes."""
    catalog = ModelCatalog()
    invoker = ModelInvoker(catalog=catalog)

    # Bedrock
    assert (
        invoker.resolve_model_id(ModelRole.PRIMARY_REASONING, runtime_mode="bedrock")
        == "anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    assert (
        invoker.resolve_model_id(ModelRole.SECONDARY_EXECUTION, runtime_mode="bedrock")
        == "anthropic.claude-3-5-haiku-20241022-v1:0"
    )

    # Staging
    assert (
        invoker.resolve_model_id(ModelRole.PRIMARY_REASONING, runtime_mode="staging")
        == "gemini-3.8-flash"
    )
    assert (
        invoker.resolve_model_id(ModelRole.SECONDARY_EXECUTION, runtime_mode="staging")
        == "gemini-3.8-flash"
    )

    # Mock
    assert (
        invoker.resolve_model_id(ModelRole.PRIMARY_REASONING, runtime_mode="mock")
        == "mock-sonnet-5"
    )
    assert (
        invoker.resolve_model_id(ModelRole.SECONDARY_EXECUTION, runtime_mode="mock")
        == "mock-haiku-4.5"
    )


@pytest.mark.asyncio
async def test_invoke_reasoning_mock() -> None:
    """Verify primary reasoning invocation through MockRuntime."""
    mock_rt = MockRuntime()
    result = await default_invoker.invoke_reasoning(
        prompt="Audit draw packet",
        system_prompt="You are a compliance auditor",
        runtime=mock_rt,
    )
    assert "MOCK_RESPONSE" in result


@pytest.mark.asyncio
async def test_invoke_execution_mock() -> None:
    """Verify secondary execution invocation through MockRuntime."""
    mock_rt = MockRuntime()
    result = await default_invoker.invoke_execution(
        prompt="Format decision card",
        system_prompt="You are an everyday synthesizer",
        runtime=mock_rt,
    )
    assert "MOCK_RESPONSE" in result


@pytest.mark.asyncio
async def test_invoke_structured_output_mock() -> None:
    """Verify structured output parsing through MockRuntime."""
    mock_rt = MockRuntime()
    result = await default_invoker.invoke_reasoning(
        prompt="Extract line items",
        structured_output_schema=SampleStructuredOutput,
        runtime=mock_rt,
    )
    assert isinstance(result, SampleStructuredOutput)
