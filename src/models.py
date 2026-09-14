"""IRONCLAD Model Allocation & Invocation Service.

Adheres strictly to AGENT_ORCHESTRATION_BLUEPRINT.md Section 8 and AGENT_LOGIC_SPEC.md.
Configures Primary (Reasoning) and Secondary (Execution) model bindings routed
dynamically through the active runtime provider with strict zero-temperature determinism
and bounded 1-retry fallback escalation.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.errors import ToolExecutionError
from src.providers import BaseRuntimeProtocol, get_runtime


class ModelRole(str, Enum):
    """Functional role allocations for models within the Tri-Track topology."""

    PRIMARY_REASONING = "PRIMARY_REASONING"
    SECONDARY_EXECUTION = "SECONDARY_EXECUTION"


class ModelCatalog(BaseModel):
    """Configured model identifiers across production, staging, and mock runtimes."""

    model_config = ConfigDict(extra="forbid")

    # Production AWS Bedrock model IDs
    bedrock_primary: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_secondary: str = "anthropic.claude-3-5-haiku-20241022-v1:0"

    # Staging Google GenAI model IDs
    staging_primary: str = "gemini-2.5-flash"
    staging_secondary: str = "gemini-2.5-flash"

    # Mock identifiers
    mock_primary: str = "mock-sonnet-5"
    mock_secondary: str = "mock-haiku-4.5"


DEFAULT_CATALOG = ModelCatalog()


class ModelInvoker:
    """Unified service for invoking reasoning and execution models."""

    def __init__(
        self,
        catalog: ModelCatalog | None = None,
        default_temperature: float = 0.0,
    ) -> None:
        self.catalog = catalog or DEFAULT_CATALOG
        self.default_temperature = default_temperature

    def resolve_model_id(
        self,
        role: ModelRole,
        runtime_mode: str = "staging",
    ) -> str:
        """Resolve exact model identifier for a given role and runtime."""
        mode = runtime_mode.strip().lower()
        if mode == "bedrock":
            return (
                self.catalog.bedrock_primary
                if role == ModelRole.PRIMARY_REASONING
                else self.catalog.bedrock_secondary
            )
        if mode == "staging":
            return (
                self.catalog.staging_primary
                if role == ModelRole.PRIMARY_REASONING
                else self.catalog.staging_secondary
            )
        return (
            self.catalog.mock_primary
            if role == ModelRole.PRIMARY_REASONING
            else self.catalog.mock_secondary
        )

    async def invoke_reasoning(
        self,
        prompt: str,
        system_prompt: str | None = None,
        structured_output_schema: type[BaseModel] | None = None,
        media_paths: list[str] | None = None,
        runtime: BaseRuntimeProtocol | None = None,
    ) -> Any:
        """Invoke primary reasoning model with 1-retry fallback on transient failure."""
        rt = runtime or get_runtime()
        model_id = self.resolve_model_id(
            ModelRole.PRIMARY_REASONING,
            runtime_mode=rt.__class__.__name__.replace("Runtime", "").lower(),
        )

        attempts = 0
        last_error: Exception | None = None

        while attempts < 2:
            attempts += 1
            try:
                return await rt.invoke_model(
                    model_id=model_id,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    structured_output_schema=structured_output_schema,
                    temperature=self.default_temperature,
                    media_paths=media_paths,
                )
            except Exception as e:  # noqa: BLE001
                last_error = e
                if attempts >= 2:
                    break

        raise ToolExecutionError(
            message=f"Primary reasoning model invocation failed after {attempts} attempts: {last_error!s}",
            incident_context={"model_id": model_id, "role": ModelRole.PRIMARY_REASONING.value},
            node_name="ModelInvoker",
        ) from last_error

    async def invoke_execution(
        self,
        prompt: str,
        system_prompt: str | None = None,
        structured_output_schema: type[BaseModel] | None = None,
        media_paths: list[str] | None = None,
        runtime: BaseRuntimeProtocol | None = None,
    ) -> Any:
        """Invoke secondary execution model for synthesis and formatting."""
        rt = runtime or get_runtime()
        model_id = self.resolve_model_id(
            ModelRole.SECONDARY_EXECUTION,
            runtime_mode=rt.__class__.__name__.replace("Runtime", "").lower(),
        )

        try:
            return await rt.invoke_model(
                model_id=model_id,
                prompt=prompt,
                system_prompt=system_prompt,
                structured_output_schema=structured_output_schema,
                temperature=self.default_temperature,
                media_paths=media_paths,
            )
        except Exception as e:
            raise ToolExecutionError(
                message=f"Secondary execution model invocation failed: {e!s}",
                incident_context={"model_id": model_id, "role": ModelRole.SECONDARY_EXECUTION.value},
                node_name="ModelInvoker",
            ) from e


# Global invoker instance
default_invoker = ModelInvoker()


def get_model_invoker(runtime_mode: str = "staging") -> ModelInvoker:
    """Retrieve or create a ModelInvoker instance for the active runtime."""
    return default_invoker

