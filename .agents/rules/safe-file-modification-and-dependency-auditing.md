---
trigger: always_on
---

Before modifying any existing file:

* Read the entire file first to maintain full architectural context.

* Identify every other module that imports from it (specifically `src/state/schema.py`, `src/state/reducers.py`, `src/tools/schemas/`, `src/providers/`, and `src/statutory_reference/lookup.py`).

* Never blindly overwrite — merge new functionality cleanly into the existing module structure while preserving Pydantic V2 strict type hints, single-writer state boundaries, and `async`/`await` signatures.

* Runtime & Provider Boundary Isolation:
  - `src/providers/bedrock_runtime.py` must maintain lazy client initializations so importing it in non-AWS environments never crashes due to missing `boto3` credentials.
  - `src/providers/staging_runtime.py` must use the official `google-genai` SDK (`from google import genai`) targeting `gemini-3.8-flash` for live multimodal extraction with zero AWS dependencies.
  - `src/providers/mock_runtime.py` must remain hermetic and load deterministic responses strictly from `tests/mocks/`.
  - All providers must implement `BaseRuntimeProtocol` identically.

* If a conflict is found between instructions and the 5 locked specification documents (`AGENT_BEHAVIOR_PROFILE.md`, `AGENT_ORCHESTRATION_BLUEPRINT.md`, `AGENT_LOGIC_SPEC.md`, `INTERFACE_OBSERVABILITY_SYSTEM.md`, `AGENT_MASTER_PLAN.md`), STOP and report the discrepancy before proceeding.