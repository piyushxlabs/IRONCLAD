"""Base Runtime Protocol for IRONCLAD Sentinel.

Declares the standard asynchronous execution contract required across Bedrock, Staging,
and Mock runtime providers.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class BaseRuntimeProtocol(ABC):
    """Abstract protocol for model invocation, tool calling, and session checkpointing."""

    @abstractmethod
    async def invoke_model(
        self,
        model_id: str,
        prompt: str,
        system_prompt: str | None = None,
        structured_output_schema: type[BaseModel] | None = None,
        temperature: float = 0.0,
        media_paths: list[str] | None = None,
    ) -> Any:
        """Invoke LLM inference with optional structured output parsing and multimodal context."""

    @abstractmethod
    async def call_mcp_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool/MCP call asynchronously."""

    @abstractmethod
    async def read_checkpoint(
        self,
        session_id: str,
    ) -> dict[str, Any] | None:
        """Retrieve persisted session state snapshot."""

    @abstractmethod
    async def write_checkpoint(
        self,
        session_id: str,
        state: dict[str, Any],
    ) -> str:
        """Persist session state snapshot and return checkpoint identifier."""

    @abstractmethod
    async def resume_from_checkpoint(
        self,
        checkpoint_id: str,
        resumption_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Resume execution from an interrupted HITL gate checkpoint."""
