"""Hermetic Offline Mock Runtime Provider.

Consumes offline JSON fixtures with zero network calls and zero credentials required.
"""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.errors import ToolExecutionError
from src.providers.base_runtime import BaseRuntimeProtocol


class MockRuntime(BaseRuntimeProtocol):
    """Offline hermetic test double simulating Bedrock/Staging execution."""

    def __init__(self, fixtures_root: Path | None = None) -> None:
        self.fixtures_root = fixtures_root or (Path(__file__).resolve().parent.parent.parent / "tests" / "mocks")
        self._checkpoints: dict[str, dict[str, Any]] = {}
        self._session_to_latest_cp: dict[str, str] = {}

    async def invoke_model(
        self,
        model_id: str,
        prompt: str,
        system_prompt: str | None = None,
        structured_output_schema: type[BaseModel] | None = None,
        temperature: float = 0.0,
        media_paths: list[str] | None = None,
    ) -> Any:
        """Return deterministic mock response matching requested model and schema."""
        if structured_output_schema is not None:
            # Return a default-constructed or mock-populated instance
            schema_name = structured_output_schema.__name__
            mock_data = self._get_mock_structured_output(schema_name)
            if mock_data is not None:
                return structured_output_schema.model_validate(mock_data)
            try:
                return structured_output_schema.model_validate({})
            except (ValueError, TypeError):
                # If required fields exist, construct with fallback data
                return structured_output_schema.model_construct()

        return f"[MOCK_RESPONSE from {model_id}]: Processed input successfully."

    def _get_mock_structured_output(self, schema_name: str) -> dict[str, Any] | None:
        """Resolve mock structured output fixtures."""
        fixtures = {
            "LineItemMappingAndDiscrepancy": {
                "mapped_items": [
                    {
                        "line_item_id": "LI-001",
                        "description": "Concrete foundation pour",
                        "contract_retainage_pct": 0.05,
                        "current_billed": 12000.00,
                        "stored_materials": 0.00,
                        "prior_payments": 36000.00,
                    }
                ],
                "confidence_score": 0.98,
                "extraction_notes": "All figures match G703 continuation sheet clearly.",
            },
            "RiderClauseClassification": {
                "detected_clause_type": "pay-if-paid",
                "confidence_score": 0.95,
                "clause_text_excerpt": "Payment by Owner to Contractor shall be an express condition precedent...",
                "statutory_override_risk": "MEDIUM",
            },
            "DecisionCardPayload": {
                "draw_number": 4,
                "project_name": "Skyline Tower Phase II",
                "subcontractor_trade": "Cast-in-Place Concrete",
                "gross_amount_requested": 12000.00,
                "contractual_retainage_withheld": 600.00,
                "net_recommended_release": 11400.00,
                "lien_chain_status": "VALID",
                "statutory_prompt_pay_clock": {
                    "days_remaining": 21,
                    "deadline_timestamp": "2026-10-04T00:00:00Z",
                    "penalty_interest_rate": "0.015",
                    "statute_reference": "Tex. Prop. Code ch. 28",
                },
                "recommended_action": "APPROVE_RELEASE",
                "blocking_discrepancies": [],
            },
        }
        return fixtures.get(schema_name)

    async def call_mcp_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> dict[str, Any]:
        """Load deterministic tool fixture or return simulated successful output."""
        fixture_path = self.fixtures_root / "tool_responses" / f"{tool_name}.json"
        if fixture_path.exists():
            try:
                def _load_json() -> dict[str, Any]:
                    with open(fixture_path, encoding="utf-8") as f:
                        return json.load(f)

                return await asyncio.to_thread(_load_json)
            except Exception as e:
                raise ToolExecutionError(
                    message=f"Failed loading mock tool fixture for {tool_name}: {e!s}",
                    incident_context={"tool_name": tool_name, "path": str(fixture_path)},
                    node_name="MockRuntime",
                ) from e

        # Built-in fallback tool responses
        defaults = {
            "extract_draw_packet_metadata": {
                "success": True,
                "document_type_detected": "G703_CONTINUATION",
                "line_items": [
                    {
                        "line_item_id": "LI-001",
                        "description": "Concrete foundation",
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
                        "claim_amount": 11400.00,
                        "through_date": "2026-09-01",
                        "notary_date": "2026-09-02",
                        "signatory_name": "Jane Doe",
                    }
                ],
                "low_confidence_fields": [],
                "error": None,
            },
            "dispatch_decision_notification": {
                "success": True,
                "dispatched_to": ["GENERAL_CONTRACTOR", "OWNER", "SUBCONTRACTOR"],
                "error": None,
            },
        }
        if tool_name in defaults:
            return defaults[tool_name]

        return {"success": True, "tool_name": tool_name, "input_echo": tool_input}

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
        """Persist snapshot in-memory and return generated checkpoint ID."""
        checkpoint_id = f"cp_mock_{uuid.uuid4().hex[:8]}"
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
            raise ToolExecutionError(
                message=f"Checkpoint {checkpoint_id} not found in mock store.",
                incident_context={"checkpoint_id": checkpoint_id},
                node_name="MockRuntime",
            )
        updated_state = state.copy()
        updated_state["approval_state"] = resumption_payload
        return updated_state
