"""IRONCLAD Provider Abstraction Layer.

Exposes a unified factory `get_runtime()` to select between Bedrock (production),
Staging (Google GenAI Gemini 3.8 Flash), and Mock (offline hermetic fixtures) runtimes.
"""

import os

from src.errors import StateValidationError
from src.providers.base_runtime import BaseRuntimeProtocol
from src.providers.bedrock_runtime import BedrockRuntime
from src.providers.mock_runtime import MockRuntime
from src.providers.staging_runtime import StagingRuntime

_RUNTIME_INSTANCE: BaseRuntimeProtocol | None = None


def get_runtime(mode: str | None = None, force_new: bool = False) -> BaseRuntimeProtocol:

    """Factory creating or returning the configured runtime provider instance."""
    global _RUNTIME_INSTANCE

    if _RUNTIME_INSTANCE is not None and not force_new and mode is None:
        return _RUNTIME_INSTANCE

    resolved_mode = (mode or os.getenv("IRONCLAD_RUNTIME_MODE", "staging")).strip().lower()

    if resolved_mode == "mock":
        instance = MockRuntime()
    elif resolved_mode == "staging":
        instance = StagingRuntime()
    elif resolved_mode == "bedrock":
        instance = BedrockRuntime()
    else:
        raise StateValidationError(
            message=f"Invalid IRONCLAD_RUNTIME_MODE: '{resolved_mode}'. Must be 'staging', 'bedrock', or 'mock'.",
            incident_context={"resolved_mode": resolved_mode},
            node_name="get_runtime",
        )

    if mode is None and not force_new:
        _RUNTIME_INSTANCE = instance

    return instance


__all__ = [
    "BaseRuntimeProtocol",
    "BedrockRuntime",
    "MockRuntime",
    "StagingRuntime",
    "get_runtime",
]
