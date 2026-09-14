---
trigger: always_on
---

Before writing or modifying any code for any step in `AGENT_MASTER_PLAN.md` Section 10, you must output this structured plan:

PLAN:

* Files to read: [list all foundational docs in workspace, schemas in `src/tools/schemas/`, or provider protocols needed for context]

* Files to create: [list full file paths under `src/`, `tests/`, or `.env`]

* Files to modify: [list full paths]

* Dependencies needed: [verify required packages in `pyproject.toml` via `uv` — e.g., `strands-agents`, `bedrock-agentcore`, `google-genai`, `streamlit`, `pydantic`]

* State & Reducer impact: [specify which `IroncladState` fields are read/written and their exact reducer semantics: `immutable-after-init`, `last-write-wins`, `append-only`, `merge-by-key`]

* Potential risks: [e.g., eager `boto3` import crashing without AWS credentials, `pydantic` version conflicts, floating-point inaccuracies in retainage math, Streamlit SSE connection drops]

Then write:

"Shall I proceed with this plan?"

Wait for explicit user confirmation before creating or modifying any codebase file.