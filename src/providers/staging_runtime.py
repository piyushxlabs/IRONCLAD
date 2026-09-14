"""Live Staging Runtime Provider powered by Google GenAI (Gemini 3.8 Flash).

Enables live multimodal inference, PDF document processing, and structured output
reasoning with zero AWS IAM credential dependencies for staging and demo hosting.
"""

import asyncio
import os
import uuid
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel

from src.errors import StateValidationError, ToolExecutionError
from src.providers.base_runtime import BaseRuntimeProtocol


def _clean_schema_for_gemini(schema: Any) -> Any:
    """Recursively strip unsupported JSON Schema keys (additionalProperties, title, $defs) for Gemini API."""
    if isinstance(schema, dict):
        return {
            k: _clean_schema_for_gemini(v)
            for k, v in schema.items()
            if k not in ("additionalProperties", "additional_properties", "title", "$defs")
        }
    if isinstance(schema, list):
        return [_clean_schema_for_gemini(item) for item in schema]
    return schema


class StagingRuntime(BaseRuntimeProtocol):
    """Zero-cost live staging runtime powered by Google Gemini 3.8 Flash via official google-genai SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "gemini-3.8-flash",
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.default_model = default_model
        self._checkpoints: dict[str, dict[str, Any]] = {}
        self._session_to_latest_cp: dict[str, str] = {}
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        """Lazily initialize Google GenAI client."""
        if self._client is None:
            if not self.api_key:
                raise StateValidationError(
                    message="GEMINI_API_KEY environment variable is missing for staging runtime.",
                    incident_context={"runtime": "staging"},
                    node_name="StagingRuntime",
                )
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def invoke_model(
        self,
        model_id: str,
        prompt: str,
        system_prompt: str | None = None,
        structured_output_schema: type[BaseModel] | None = None,
        temperature: float = 0.0,
        media_paths: list[str] | None = None,
    ) -> Any:
        """Execute non-blocking async inference using Gemini with optional schema constraint."""
        client = self._get_client()
        target_model = model_id or self.default_model

        # Normalize model identifier if Bedrock format was passed
        if "sonnet" in target_model.lower() or "haiku" in target_model.lower():
            target_model = self.default_model

        contents: list[Any] = []

        # Attach multimodal assets if provided (PDFs, images)
        if media_paths:
            for path in media_paths:
                if os.path.exists(path):
                    def _read_bytes(file_path: str) -> bytes:
                        with open(file_path, "rb") as f:
                            return f.read()

                    file_bytes = await asyncio.to_thread(_read_bytes, path)
                    mime = "application/pdf" if path.lower().endswith(".pdf") else "image/png"
                    contents.append(types.Part.from_bytes(data=file_bytes, mime_type=mime))

        contents.append(prompt)

        # Build execution configuration
        config_kwargs: dict[str, Any] = {
            "temperature": temperature,
        }
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt

        if structured_output_schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = _clean_schema_for_gemini(structured_output_schema.model_json_schema())

        config = types.GenerateContentConfig(**config_kwargs)

        try:
            response = await client.aio.models.generate_content(
                model=target_model,
                contents=contents,
                config=config,
            )

            if structured_output_schema is not None:
                if response.text:
                    return structured_output_schema.model_validate_json(response.text)
                raise ToolExecutionError(
                    message="Empty response text returned for structured output request.",
                    incident_context={"model": target_model, "schema": structured_output_schema.__name__},
                    node_name="StagingRuntime",
                )

            return response.text or ""

        except Exception as e:
            raise ToolExecutionError(
                message=f"Gemini staging inference failed: {e!s}",
                incident_context={"model": target_model, "error": str(e)},
                node_name="StagingRuntime",
            ) from e

    async def call_mcp_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute MCP or synthetic tool call in staging environment."""
        if tool_name == "extract_draw_packet_metadata":
            uri = str(tool_input.get("pdf_uri", ""))
            if "defect" in uri or "draw_2" in uri:
                return {
                    "success": True,
                    "document_type_detected": "G703_CONTINUATION",
                    "line_items": [
                        {
                            "line_item_id": "LI-001",
                            "description": "Electrical Conduit & Rough-in",
                            "contract_retainage_pct": None,
                            "current_billed": 25000.00,
                            "stored_materials": 0.00,
                            "prior_payments": 0.00,
                        }
                    ],
                    "waiver_records": [
                        {
                            "waiver_id": "W-002",
                            "waiver_type": "CONDITIONAL_PROGRESS",
                            "notary_execution_date": "2026-08-01",
                            "associated_line_item_id": "LI-001",
                        }
                    ],
                    "low_confidence_fields": [],
                    "error": None,
                }
            if "edge" in uri or "draw_3" in uri:
                return {
                    "success": True,
                    "document_type_detected": "G703_CONTINUATION",
                    "line_items": [
                        {
                            "line_item_id": "LI-001",
                            "description": "Plumbing Rough-in & Underground",
                            "contract_retainage_pct": 0.10,
                            "current_billed": 18500.00,
                            "stored_materials": 2500.00,
                            "prior_payments": 0.00,
                        }
                    ],
                    "waiver_records": [],
                    "low_confidence_fields": ["contract_retainage_pct"],
                    "error": None,
                }
            return {
                "success": True,
                "document_type_detected": "G703_CONTINUATION",
                "line_items": [
                    {
                        "line_item_id": "LI-001",
                        "description": "Concrete foundation pour",
                        "contract_retainage_pct": 0.05,
                        "current_billed": 12000.00,
                        "stored_materials": 0.00,
                        "prior_payments": 36000.00,
                    }
                ],
                "waiver_records": [
                    {
                        "waiver_id": "W-001",
                        "waiver_type": "CONDITIONAL_PROGRESS",
                        "notary_execution_date": "2026-09-02",
                        "associated_line_item_id": "LI-001",
                    }
                ],
                "low_confidence_fields": [],
                "error": None,
            }
        if tool_name == "dispatch_decision_notification":
            recipients = tool_input.get("recipients", ["GENERAL_CONTRACTOR", "OWNER", "SUBCONTRACTOR"])
            return {
                "success": True,
                "dispatched_to": recipients,
                "error": None,
            }

        return {
            "success": True,
            "tool_name": tool_name,
            "status": "STAGING_SIMULATED",
            "data": tool_input,
        }

    async def read_checkpoint(
        self,
        session_id: str,
    ) -> dict[str, Any] | None:
        """Retrieve persisted in-memory session checkpoint."""
        checkpoint_id = self._session_to_latest_cp.get(session_id)
        if not checkpoint_id:
            return None
        return self._checkpoints.get(checkpoint_id)

    async def write_checkpoint(
        self,
        session_id: str,
        state: dict[str, Any],
    ) -> str:
        """Persist state snapshot and return checkpoint identifier."""
        checkpoint_id = f"cp_stage_{uuid.uuid4().hex[:8]}"
        self._checkpoints[checkpoint_id] = state.copy()
        self._session_to_latest_cp[session_id] = checkpoint_id
        return checkpoint_id

    async def resume_from_checkpoint(
        self,
        checkpoint_id: str,
        resumption_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Resume state from checkpoint applying decision payload."""
        state = self._checkpoints.get(checkpoint_id)
        if state is None:
            raise StateValidationError(
                message=f"Checkpoint {checkpoint_id} not found in staging store.",
                incident_context={"checkpoint_id": checkpoint_id},
                node_name="StagingRuntime",
            )
        updated_state = state.copy()
        updated_state["approval_state"] = resumption_payload
        return updated_state
