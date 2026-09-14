# AGENT MASTER PLAN

**Generated:** September 13, 2026
**Source Documents:**
- AGENT_ORCHESTRATION_BLUEPRINT.md
- AGENT_LOGIC_SPEC.md
- INTERFACE_OBSERVABILITY_SYSTEM.md

**Status:** AUTHORITATIVE — Complete execution plan for agent system implementation

---

## **1. EXECUTION PRINCIPLES**

**Technology Stack (Verified):**

| Component | Package | Phase 1.5 Status |
|---|---|---|
| Agent orchestration SDK | `strands-agents` `1.42.0` | **Verified** — confirmed current on PyPI this session; ships `pydantic`, `mcp`, `jsonschema`, `opentelemetry-api`, `opentelemetry-sdk`, `boto3`/`botocore`, `aws-sdk-bedrock-runtime` as required deps, and `opentelemetry-exporter-otlp-proto-http`, `anthropic`, `pytest`, `pytest-asyncio`, `fastapi`, `uvicorn`, `starlette` as optional extras |
| AgentCore Runtime wrapper | `bedrock-agentcore` | **Verified as the correct package** (provides `BedrockAgentCoreApp`/`@app.entrypoint`) — exact pinned patch version **Assumption — Unverified, confirm latest on PyPI before install** |
| Deployment/scaffolding CLI | `@aws/agentcore` (npm, dev-tooling only, not a Python runtime dependency) | **Verified** — the legacy `bedrock-agentcore-starter-toolkit` Python package is explicitly marked legacy by its own maintainers; new projects use the npm-based AgentCore CLI. Noted here as a deployment-tooling substitution, not an architectural change |
| Schema validation | `pydantic` `>=2.9,<2.12` | **Verified caution** — live search surfaced a documented incompatibility between `strands-agents` `1.16.0` and `pydantic>2.11`; pin conservatively and let `uv lock` resolve the exact version `strands-agents==1.42.0` actually tests against rather than assuming the issue is resolved |
| Telemetry export | `langfuse` `4.15.2` | **Verified** — current on PyPI this session; Langfuse's v4 SDK (rewritten March 2026) is itself OpenTelemetry-native, matching INTERFACE_OBSERVABILITY_SYSTEM.md Section 6's dual-export design with no adapter layer needed |
| AWS SDK | `boto3`, `botocore` | Pulled transitively via `strands-agents`; exact floor **Assumption — Unverified, confirm via `uv lock`** |
| Frontend | `streamlit` | **Assumption — Unverified, confirm latest stable on PyPI before install** — actively releasing as of 2026 per this session's research; pin the exact resolved version in `uv.lock`, do not hardcode a guess |
| Test runner | `pytest`, `pytest-asyncio` | Reuse the exact versions `strands-agents` `1.42.0` already declares as optional extras, to guarantee compatibility rather than introducing an independent pin |
| LLM eval framework | `deepeval` | **Assumption — Unverified, confirm latest stable on PyPI before install** — chosen over Promptfoo/Ragas because it is Python-native and integrates directly with `pytest`, matching this project's all-Python stack (no Node eval runner needed) |
| Lint/type-check | `ruff`, `mypy` | Reuse the exact versions `strands-agents` `1.42.0` already declares as optional dev extras |
| Package manager | `uv` | Current, verified in this session's Step-2 research as the AWS-recommended installer for `bedrock-agentcore-starter-toolkit`, and used unchanged here |
| Staging runtime adapter SDK | `google-genai` | **Verified** — official modern Google GenAI Python SDK (`from google import genai`), powering zero-cost live semantic staging engine (`gemini-3.8-flash`) via Google AI Studio free tier |

**Runtime Assumptions:** Python 3.11+ (matches `bedrock-agentcore-starter-toolkit`'s documented `--python 3.10` floor rounded up to this project's `>=3.11` requirement per the Step-5 mandate), async-first (`asyncio`) throughout, matching AGENT_ORCHESTRATION_BLUEPRINT.md Section 10's async-native execution standard.

**Explicit Non-Goals:**
- No Node.js/TypeScript build at all — INTERFACE_OBSERVABILITY_SYSTEM.md Section 2 selected Streamlit specifically to avoid one; do not introduce `pnpm`/`package.json` anywhere in this plan.
- No FastAPI backend server — the "backend" IS the AgentCore Runtime container running `BedrockAgentCoreApp`; Streamlit talks to it directly via `boto3`'s AgentCore data-plane client (`invoke_agent_runtime`), not through a separately hand-rolled API layer.
- No vector store / long-term memory setup — AGENT_ORCHESTRATION_BLUEPRINT.md Section 7 explicitly excludes one; do not scaffold `src/memory/` beyond the statutory reference-table reader.
- No UI components beyond the single Executive Decision Card and its Audit Trail panel — no chat component is ever built, per INTERFACE_OBSERVABILITY_SYSTEM.md's zero-chat mandate.

**Stability Requirements:** Every state mutation goes through its declared reducer (AGENT_ORCHESTRATION_BLUEPRINT.md Section 3) with no exceptions; every tool call validates against its Pydantic V2 model before and after execution (AGENT_LOGIC_SPEC.md Section 4); the local `mock_runtime.py` provider (Section 2 below) must be schema-identical to `bedrock_runtime.py` so tests run against the mock are valid evidence for the real provider.

---

## **2. ENVIRONMENT & INFRASTRUCTURE SETUP**

**Required API Keys & Secrets:**

1. AWS — IAM credentials with `bedrock-agentcore:InvokeAgentRuntime` and Bedrock model-invocation permissions — obtained via AWS IAM console or `aws configure` — env var `AWS_PROFILE` (or `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`)
2. AWS Region hosting the deployed AgentCore Runtime — env var `AWS_REGION`
3. Langfuse — Project public/secret key pair — obtained from the Langfuse Cloud project settings (or self-hosted instance) — env vars `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
4. AgentCore Runtime identifier — the deployed agent's ARN/endpoint, populated in production — env var `AGENTCORE_RUNTIME_ARN`
5. Statutory reference-data store connection — obtained from wherever the versioned jurisdiction table (AGENT_ORCHESTRATION_BLUEPRINT.md Section 7) is hosted — env var `STATUTORY_TABLE_URI`
6. Google AI Studio — API key for zero-cost live staging runtime (`gemini-3.8-flash`) — obtained from Google AI Studio (0 credit card / free tier) — env var `GEMINI_API_KEY`
7. Notification-dispatch MCP server credentials — **Assumption — Unverified**, since AGENT_LOGIC_SPEC.md Section 3 flagged this tool's vendor as unresolved upstream; env var placeholder `NOTIFICATION_MCP_ENDPOINT` / `NOTIFICATION_MCP_API_KEY` reserved but not wired until a vendor is chosen
8. Document-OCR MCP server credentials — same unresolved-vendor caveat as above — env var placeholder `OCR_MCP_ENDPOINT` / `OCR_MCP_API_KEY`

**Required Environment Variables:**

```
AWS_PROFILE=ironclad-dev
AWS_REGION=us-east-1
AGENTCORE_RUNTIME_ARN=arn:aws:bedrock-agentcore:...   # populated in production
IRONCLAD_RUNTIME_MODE=staging                          # "staging" (default for live demo), "bedrock", or "mock"
GEMINI_API_KEY=...                                     # Required for "staging" mode (zero-cost live inference)
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
STATUTORY_TABLE_URI=...
OCR_MCP_ENDPOINT=                                       # unresolved vendor — leave blank in mock/staging mode
OCR_MCP_API_KEY=
NOTIFICATION_MCP_ENDPOINT=                              # unresolved vendor — leave blank in mock/staging mode
NOTIFICATION_MCP_API_KEY=
```

### **Package Manifest (Verified via Phase 1.5)**

**`pyproject.toml` managed by `uv`:**

```toml
[project]
name = "ironclad-agent"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "strands-agents==1.42.0",                         # Verified — current on PyPI this session
    "strands-agents[otel]",                             # Pulls opentelemetry-exporter-otlp-proto-http, already an optional extra of strands-agents
    "bedrock-agentcore",                                 # Verified package identity — pin exact version via `uv add` at install time
    "google-genai",                                      # Verified — modern official Google GenAI Python SDK for live staging runtime
    "pydantic>=2.9,<2.12",                               # Verified caution — see Section 1 compatibility note
    "boto3",                                             # Version resolved transitively; confirm floor via `uv lock`
    "langfuse==4.15.2",                                  # Verified — current on PyPI this session, OTel-native v4 SDK
    "streamlit",                                          # Assumption — Unverified exact version; resolve via `uv add streamlit`
]

[project.optional-dependencies]
dev = [
    "pytest",                                             # Reuse strands-agents[dev]-tested version
    "pytest-asyncio",                                     # Reuse strands-agents[dev]-tested version
    "deepeval",                                            # Assumption — Unverified exact version
    "ruff",
    "mypy",
]

[tool.uv]
# Standard uv-managed lockfile; no custom index required for the packages above.
```

**Installation Command:**
```
uv sync --all-extras
```

**Version Verification Log:**

| Package | Chosen Version | Phase 1.5 Status |
|---|---|---|
| `strands-agents` | `1.42.0` | Verified via live PyPI/piwheels lookup this session |
| `bedrock-agentcore` | unpinned (latest) | Package identity verified; exact version Assumption — Unverified |
| `google-genai` | unpinned (latest) | Verified modern official Google GenAI Python SDK for staging runtime |
| `pydantic` | `>=2.9,<2.12` | Verified caution from a documented `strands-agents`/Pydantic incompatibility issue; re-verify against `strands-agents==1.42.0`'s actual tested range before locking |
| `langfuse` | `4.15.2` | Verified via live PyPI lookup this session |
| `boto3` | unpinned (transitive) | Assumption — Unverified exact floor |
| `streamlit` | unpinned (latest) | Assumption — Unverified exact version |
| `deepeval` | unpinned (latest) | Assumption — Unverified exact version |
| `pytest` / `pytest-asyncio` / `ruff` / `mypy` | match `strands-agents==1.42.0`'s declared dev extras | Verified as `strands-agents` optional extras this session; exact pins inherited, not independently guessed |

**Deprecated Package Substitutions:**
- `bedrock-agentcore-starter-toolkit` (Python CLI) is explicitly marked **legacy** by its own maintainers as of this session's research. It is NOT included in the dependency manifest above. Where AGENT_ORCHESTRATION_BLUEPRINT.md or AGENT_LOGIC_SPEC.md implied "the AgentCore toolkit" for scaffolding/deployment, the current recommended replacement is the npm-based `@aws/agentcore` CLI, used only as a local dev-machine deployment tool (Step 20) — it is never a runtime dependency of the agent itself, so it does not appear in `pyproject.toml`.

### **Project Directory Structure**

```text
ironclad-agent/
├── .env.example
├── pyproject.toml
├── uv.lock
├── CLAUDE.md
├── .cursorrules
├── src/
│   ├── agents/
│   │   ├── forensic_audit_sentinel.py       # System prompt + node wiring, from AGENT_LOGIC_SPEC.md Section 1
│   │   ├── fair_pay_statutory_guardian.py
│   │   ├── everyday_decision_card_emitter.py
│   │   └── graph.py                          # Strands GraphBuilder wiring — fan-out/fan-in per AGENT_ORCHESTRATION_BLUEPRINT.md Section 4
│   ├── tools/
│   │   ├── extract_draw_packet_metadata.py
│   │   ├── audit_retainage_math.py
│   │   ├── verify_lien_chain_integrity.py
│   │   ├── statutory_prompt_pay_clock.py
│   │   ├── dispatch_decision_notification.py
│   │   └── schemas/
│   │       ├── pydantic_models.py            # All Pydantic V2 Input/Output models from AGENT_LOGIC_SPEC.md Section 4
│   │       └── strict_json_schemas.py         # All MCP/strict JSON Schema dicts from AGENT_LOGIC_SPEC.md Section 4
│   ├── structured_outputs/
│   │   ├── line_item_mapping_and_discrepancy.py
│   │   ├── rider_clause_classification.py
│   │   └── decision_card_payload.py           # AGENT_LOGIC_SPEC.md Section 5
│   ├── state/
│   │   ├── schema.py                          # IroncladState — AGENT_ORCHESTRATION_BLUEPRINT.md Section 3
│   │   ├── reducers.py                        # append-only / merge-by-key / last-write-wins implementations
│   │   └── checkpointing.py                   # AgentCoreMemorySessionManager (prod) / local SQLite fallback (dev)
│   ├── providers/                             # MANDATED Step-5 Provider Abstraction scaffold
│   │   ├── __init__.py                        # Factory reading IRONCLAD_RUNTIME_MODE ("bedrock", "staging", "mock")
│   │   ├── base_runtime.py                    # Abstract BaseRuntimeProtocol
│   │   ├── bedrock_runtime.py                 # Production AWS Bedrock AgentCore Runtime (with LAZY boto3 loading)
│   │   ├── staging_runtime.py                 # Live Gemini 3.8 Flash Engine (using `google-genai` and GEMINI_API_KEY)
│   │   └── mock_runtime.py                    # Hermetic offline JSON fixture mock
│   ├── telemetry/
│   │   ├── tracing.py                         # OTel span setup, matching AGENT_ORCHESTRATION_BLUEPRINT.md Section 8 span hierarchy
│   │   └── feedback_annotations.py             # Langfuse score writes — INTERFACE_OBSERVABILITY_SYSTEM.md Section 7a
│   ├── ui/
│   │   ├── app.py                              # Streamlit entrypoint — the Executive Decision Card
│   │   ├── event_types.py                      # Typed event contract — INTERFACE_OBSERVABILITY_SYSTEM.md Section 2a
│   │   ├── stream_consumer.py                  # Hop-1 SSE consumption loop (Section 2's two-hop model)
│   │   ├── generative_ui.py                    # Section 4a component renderers
│   │   └── hitl_resumption.py                  # Three-button resumption payload builder — Section 5
│   ├── statutory_reference/
│   │   └── lookup.py                           # Read-only keyed lookup against STATUTORY_TABLE_URI
│   └── main.py                                 # AgentCore @app.entrypoint — wires graph.py into BedrockAgentCoreApp
├── tests/
│   ├── mocks/
│   │   ├── draw_packets/                       # Sample G702/G703 + waiver payload JSONs
│   │   └── tool_responses/                     # Mock outputs for each of the 6 tools
│   ├── evals/
│   │   ├── test_tool_calling_accuracy.py
│   │   ├── test_hallucination_resistance.py
│   │   └── test_hitl_resumption.py
│   ├── unit/
│   │   ├── test_reducers.py
│   │   └── test_schemas.py
│   └── integration/
│       └── test_graph_end_to_end.py
└── README.md
```

**File Purpose Explanation:**
- `src/agents/`: The three node prompts (AGENT_LOGIC_SPEC.md Section 1) and the `GraphBuilder` fan-out/fan-in wiring (AGENT_ORCHESTRATION_BLUEPRINT.md Section 4).
- `src/tools/`: The six tools, each with dual-format schemas per AGENT_LOGIC_SPEC.md Section 4.
- `src/structured_outputs/`: The three structured-output-only judgments per AGENT_LOGIC_SPEC.md Section 5, kept separate from `tools/` because they never trigger an external side effect.
- `src/state/`: `IroncladState` and its reducers, exactly as declared in AGENT_ORCHESTRATION_BLUEPRINT.md Section 3.
- `src/providers/`: The mandated Provider Abstraction layer (Section 3 below has the full scaffold).
- `src/telemetry/`: OTel span emission and the Langfuse feedback-annotation pipeline.
- `src/ui/`: The Streamlit Executive Decision Card, its typed event consumption, and the HITL resumption payload builder.
- `tests/mocks/`: JSON fixtures defined in Section 9.1.
- `tests/evals/`: Automated LLM-behavior evals defined in Section 9.3.

**Local vs Production vs Staging Distinctions:**
- **Local:** `IRONCLAD_RUNTIME_MODE=mock` (routes through `src/providers/mock_runtime.py`, hermetic offline JSON fixtures, zero network calls, zero cost); SQLite-backed session store (AGENT_ORCHESTRATION_BLUEPRINT.md Section 7's local fallback); Langfuse pointed at a free-tier Cloud project or disabled.
- **Staging (Public Demo):** `IRONCLAD_RUNTIME_MODE=staging` (routes through `src/providers/staging_runtime.py`, real live multimodal inference with `gemini-3.8-flash` via `google-genai`, zero AWS credential requirement, 100% public demo uptime on Streamlit Community Cloud).
- **Production:** `IRONCLAD_RUNTIME_MODE=bedrock` (routes through `src/providers/bedrock_runtime.py`, containerized on AWS Bedrock AgentCore with lazy `boto3` client initialization); `AgentCoreMemorySessionManager` backing session state; full CloudWatch + Langfuse dual telemetry export per INTERFACE_OBSERVABILITY_SYSTEM.md Section 6.

---

## **3. CODING ASSISTANT CONTEXT FILES**

**Target Files:** Both `CLAUDE.md` and `.cursorrules` are generated (per the Step-5 mandate), with identical content — a coding assistant reading either file gets the same rules.

**Full Contents (copy-pasteable, identical for both files):**

```markdown
# IRONCLAD Agent — Coding Assistant Context

## Project Overview
IRONCLAD is a Semi-Autonomous, three-node Strands GraphBuilder agent system that audits commercial
construction draw packets (AIA G702/G703 + lien waivers), deterministically verifies retainage math and
lien-waiver chain-of-custody, tracks statutory prompt-pay deadlines, and surfaces a single zero-chat
Executive Decision Card for a human to approve release, hold for correction, or escalate to legal. It
never touches payment rails and never performs financial arithmetic outside its four deterministic tools.

## Strict Coding Rules
- Python 3.11+, async-first: all I/O-bound operations (model calls, tool calls, checkpoint/session access,
  MCP calls) MUST use `async`/`await`. Never use blocking I/O in agent nodes or tools.
- All data crossing a function boundary MUST have explicit Pydantic V2 type hints (`Field(..., description=...)`,
  `Literal`, `Optional`) — no bare `dict`, no bare `Any` unless truly unavoidable and justified in a comment.
- Every tool input/output MUST validate against its model in `src/tools/schemas/pydantic_models.py` — both
  before invocation (input) and after (output), per AGENT_LOGIC_SPEC.md Section 9's Invalid Output Detection.
- Use a custom exception hierarchy rooted at a single `IroncladError` base class, with subclasses
  `ToolExecutionError`, `StateValidationError`, `ApprovalTimeoutError`, `ProhibitedActionError` — never raise
  bare `Exception`.
- Every tool input containing a URI, path, or free-text field MUST be sanitized per AGENT_LOGIC_SPEC.md
  Section 8 before it reaches an external call — no exceptions, no "trusted input" shortcuts.
- `src/providers/bedrock_runtime.py`, `src/providers/staging_runtime.py`, and `src/providers/mock_runtime.py` MUST
  implement the exact same `BaseRuntimeProtocol` defined in `src/providers/base_runtime.py` — a caller must never need
  to know which one is active.
- Staging mode MUST perform real live LLM inference using `gemini-3.8-flash` via `google-genai` and actual tool-calling
  against uploaded documents; it must never be a hardcoded static JSON mock.

## Architecture Boundaries
- **State lives in:** `src/state/schema.py` (the single `IroncladState` definition, field-for-field identical
  to AGENT_ORCHESTRATION_BLUEPRINT.md Section 3) — no component defines a parallel state shape.
- **Reducers live in:** `src/state/reducers.py` — every state mutation MUST go through the declared reducer
  for that field (`append-only`, `merge-by-key`, `last-write-wins`, `immutable-after-init`, exactly as
  specified upstream). Direct mutation of a state field outside its declared reducer is forbidden.
- **Tools live in:** `src/tools/` — agent nodes import tools from here; nodes MUST NOT define inline ad-hoc
  tool logic. Each tool file exports both its Strands `@tool`-decorated function AND is validated against
  the paired MCP/strict JSON Schema in `src/tools/schemas/strict_json_schemas.py`.
- **Structured outputs live in:** `src/structured_outputs/` — never call an external service from here; if a
  judgment needs an external call, it belongs in `src/tools/` instead.
- **Checkpointing lives in:** `src/state/checkpointing.py` — `AgentCoreMemorySessionManager` (production) or
  local SQLite (development), selected by `IRONCLAD_RUNTIME_MODE`, never hardcoded.
- **Runtime provider selection lives in:** `src/providers/__init__.py` — reads `IRONCLAD_RUNTIME_MODE`
  exactly once at process start; no other module reads that environment variable directly.
- **Telemetry hooks live in:** `src/telemetry/` — every reasoning step and tool call MUST emit a span per the
  hierarchy in INTERFACE_OBSERVABILITY_SYSTEM.md Section 6 (trace → per-node `invoke_agent` span →
  `execute_tool`/`inference` child spans).
- **Streaming/UI event emission lives in:** `src/ui/event_types.py` and `src/ui/stream_consumer.py` — agent
  and tool code emits domain events only; it never imports Streamlit directly.

## Strict Anti-Patterns (Never Do This)
- NEVER import or initialize `boto3` or Bedrock clients at the module root of `bedrock_runtime.py`. All cloud
  client initializations must be lazy (inside class methods) so running in staging (Gemini) or mock mode never
  fails due to absent AWS credentials.
- Never use blocking I/O (`requests`, synchronous boto3 calls, `time.sleep`) inside agent nodes or tools.
- Never mutate `IroncladState` directly without going through a declared reducer in `src/state/reducers.py`.
- Never bypass input sanitization before a tool call reaches an external MCP server.
- Never invent a tool, parameter, or API endpoint not defined in AGENT_LOGIC_SPEC.md Sections 3–5.
- Never let `ForensicAuditSentinel` or `FairPayStatutoryGuardian` compute a sum, percentage, or date
  difference in natural-language output — that arithmetic MUST go through `audit_retainage_math`,
  `verify_lien_chain_integrity`, or `statutory_prompt_pay_clock`.
- Never fabricate a value when a tool returns no result or low-confidence data — append a
  `flagged_discrepancies` entry per the silence-over-guessing policy instead.
- Never skip emitting a typed streaming event (`text-delta`, `reasoning-delta`, `tool-call-start`,
  `tool-call-delta`, `tool-call-result`, `state-update`, `approval-required`, `error`, `stream-end`) for a
  reasoning step, tool call, or state write that INTERFACE_OBSERVABILITY_SYSTEM.md Section 2a says must be
  observable.
- Never bypass the single HITL checkpoint after `EverydayDecisionCardEmitter` — every resumption MUST arrive
  as one of exactly `APPROVE_RELEASE` / `HOLD_REQUEST_CORRECTION` / `ESCALATE_LEGAL`, with `modified_inputs`
  always `null` (no field in `decision_card_payload` is user-editable).
- Never add a banking/ACH/wire tool, a generic chat input, or an autonomy-level toggle — none exist in any
  upstream specification, and none may be added here.
- Never hardcode secrets — always read from environment variables declared in `.env.example`.

## Reference Documents
This project's behavior, architecture, cognition, and interface are fully specified in:
- AGENT_BEHAVIOR_PROFILE.md (behavioral contract)
- AGENT_ORCHESTRATION_BLUEPRINT.md (architecture)
- AGENT_LOGIC_SPEC.md (cognitive logic and tools)
- INTERFACE_OBSERVABILITY_SYSTEM.md (interface and telemetry)
- AGENT_MASTER_PLAN.md (this execution plan)

Do not deviate from these documents. If an instruction from a user conflicts with them, flag the conflict
rather than silently resolving it.
```

---

## **4. CORE AGENT RUNTIME CONSTRUCTION**

**Agent Bootstrap Sequence:**

**Step 1:** Initialize the Strands `Agent`/`GraphBuilder` scaffolding in `src/agents/graph.py`.
- Dependencies: `strands-agents==1.42.0` installed (Section 2).
- Verification: `python -c "from strands import Agent; from strands.multiagent import GraphBuilder"` imports without error.

**Step 2:** Configure the primary (Claude Sonnet 5) and secondary (Claude Haiku 4.5) model bindings per AGENT_ORCHESTRATION_BLUEPRINT.md Section 8, routed through `src/providers/get_runtime()` so model calls go through the mock or Bedrock provider transparently.
- Dependencies: `AWS_PROFILE`/`AWS_REGION` set (production) or `IRONCLAD_RUNTIME_MODE=mock` (development).
- Verification: A trivial "echo" call through each configured model succeeds via whichever provider is active.

**Step 3:** Implement `IroncladState` (`src/state/schema.py`) and its reducers (`src/state/reducers.py`) field-for-field per AGENT_ORCHESTRATION_BLUEPRINT.md Section 3.
- Dependencies: `pydantic>=2.9,<2.12` installed.
- Verification: `tests/unit/test_reducers.py` passes — append-only never drops an entry, merge-by-key never cross-overwrites a different `tool_call_id`, last-write-wins resolves deterministically, immutable-after-init fields reject any write attempt.

**Step 4:** Initialize the checkpointing backend (`src/state/checkpointing.py`) — `AgentCoreMemorySessionManager` in production, local SQLite in development, selected via `IRONCLAD_RUNTIME_MODE`.
- Dependencies: Step 3 complete; `bedrock-agentcore` installed (production only).
- Verification: A checkpoint write → simulated process restart → read round-trip returns identical state.

**Step 5:** Initialize the read-only statutory reference-data lookup (`src/statutory_reference/lookup.py`) against `STATUTORY_TABLE_URI`.
- Dependencies: `STATUTORY_TABLE_URI` set.
- Verification: A lookup for a known test jurisdiction (e.g., `"TX"`) returns a non-null result; an unknown jurisdiction returns the documented "unresolvable" failure, never a default.

**Step 6:** Wire the fan-out/fan-in graph in `src/agents/graph.py` — entry → [`ForensicAuditSentinel`, `FairPayStatutoryGuardian`] parallel → `EverydayDecisionCardEmitter` → HITL interrupt, exactly per AGENT_ORCHESTRATION_BLUEPRINT.md Section 4.
- Dependencies: Steps 1–5 complete; tools registered (Section 5 below).
- Verification: Graph structure inspection confirms exactly 3 nodes, the documented fan-out/fan-in edges, and no additional edges.

---

## **5. TOOL INTEGRATION PLAN**

**Tool Registration Sequence:**

**Tool 1: `extract_draw_packet_metadata`**
- Purpose: Form-aware OCR/key-value extraction (AGENT_LOGIC_SPEC.md Section 3).
- Invocation Mode: Tool/Function Calling.
- Pydantic V2 Schema Location: `src/tools/schemas/pydantic_models.py::ExtractDrawPacketMetadataInput/Output`.
- MCP/Strict JSON Schema Location: `src/tools/schemas/strict_json_schemas.py::EXTRACT_DRAW_PACKET_METADATA_SCHEMA`.
- Package Verification: **Assumption — Unverified**, no OCR MCP vendor named upstream (AGENT_LOGIC_SPEC.md Section 4) — implement against `src/providers/mock_runtime.py`'s fixture responses until a vendor is selected; do not hardcode a real vendor SDK call in `bedrock_runtime.py` until Phase 1.5 verification of that vendor's actual API is performed as its own follow-up task.
- Dependencies: `draw_packet_meta.source_uris` populated (Step 1 of the execution flow).
- Registration Step: `@tool`-decorate the function in `src/tools/extract_draw_packet_metadata.py`; bind only to `ForensicAuditSentinel`.
- State Read/Write: Writes raw output to `tool_artifacts[tool_call_id]` (merge-by-key) — never directly to `extracted_line_items`.
- Verification: Invoked against `tests/mocks/tool_responses/extract_draw_packet_metadata.json`; output validates against both schema formats.

**Tool 2: `audit_retainage_math`**
- Purpose: Deterministic retainage/arithmetic verification.
- Invocation Mode: Tool/Function Calling.
- Pydantic V2 / MCP Schema Locations: `AuditRetainageMathInput/Output` / `AUDIT_RETAINAGE_MATH_SCHEMA`.
- Package Verification: N/A — internal deterministic tool.
- Dependencies: Normalized `LineItem` records from the `LineItemMappingAndDiscrepancy` structured output (Step 12 below).
- Registration Step: Bind only to `ForensicAuditSentinel`.
- State Read/Write: Writes `retainage_audit_result` (last-write-wins, sole writer).
- Verification: Unit test against `tests/mocks/tool_responses/audit_retainage_math.json`; internal-consistency check (`net = gross - retainage - prior_payments`) asserted.

**Tool 3: `verify_lien_chain_integrity`**
- Purpose: Chronological waiver validation.
- Invocation Mode: Tool/Function Calling.
- Pydantic V2 / MCP Schema Locations: `VerifyLienChainIntegrityInput/Output` / `VERIFY_LIEN_CHAIN_INTEGRITY_SCHEMA`.
- Package Verification: N/A — internal deterministic tool.
- Dependencies: Extracted `LienWaiverRecord` list, non-empty.
- Registration Step: Bind only to `ForensicAuditSentinel`.
- State Read/Write: Writes `lien_chain_status` (last-write-wins) and appends to `flagged_discrepancies`.
- Verification: Unit test including the empty-waiver-list rejection case.

**Tool 4: `statutory_prompt_pay_clock`**
- Purpose: Statutory deadline/interest calculation.
- Invocation Mode: Tool/Function Calling.
- Pydantic V2 / MCP Schema Locations: `StatutoryPromptPayClockInput/Output` / `STATUTORY_PROMPT_PAY_CLOCK_SCHEMA`.
- Package Verification: N/A — reads the internal reference-data store (Step 5).
- Dependencies: Non-ambiguous `RiderClauseClassification` output.
- Registration Step: Bind only to `FairPayStatutoryGuardian`.
- State Read/Write: Writes `statutory_prompt_pay_clock` (last-write-wins).
- Verification: Unit test for a known jurisdiction and for the unresolvable-jurisdiction failure path.

**Tool 5: `dispatch_decision_notification`**
- Purpose: Notification/escalation dispatch.
- Invocation Mode: Tool/Function Calling.
- Pydantic V2 / MCP Schema Locations: `DispatchDecisionNotificationInput/Output` / `DISPATCH_DECISION_NOTIFICATION_SCHEMA`.
- Package Verification: **Assumption — Unverified**, no notification vendor named upstream — same mock-first approach as Tool 1.
- Dependencies: `decision_card_payload` populated (standard path) or the critical-deadline condition (escalation path).
- Registration Step: Bind only to `EverydayDecisionCardEmitter`.
- State Read/Write: Writes dispatch confirmation to `tool_artifacts[tool_call_id]` (merge-by-key); never touches `approval_state`.
- Verification: Unit test for both `DECISION_CARD_READY` and `URGENT_STATUTORY_ESCALATION` notification types.

**Inter-Tool Dependencies:** `LineItemMappingAndDiscrepancy` (structured output) must run before `audit_retainage_math`; `RiderClauseClassification` (structured output) must run before `statutory_prompt_pay_clock`; `verify_lien_chain_integrity` has no upstream tool dependency beyond extraction. `dispatch_decision_notification` must run after `DecisionCardPayload` in the same node turn (standard path).

**Error Handling Strategy:**
- Tool failure response: Transient → retry, exponential backoff, max 3 attempts (1s → 4s → 16s); Permanent → append `error_logs` + `flagged_discrepancies`, never retried with adjusted inputs, per AGENT_LOGIC_SPEC.md Section 9.
- Rate limit handling: Token-bucket limits on the two MCP-backed tools only (`extract_draw_packet_metadata`, `dispatch_decision_notification`), implemented in `src/providers/bedrock_runtime.py`'s MCP client wrapper.
- Validation failures: Every tool output validated against its Pydantic V2 model before merging into state; a validation failure is treated as an Invalid Output per AGENT_LOGIC_SPEC.md Section 9, not silently coerced.
- Input sanitization enforcement: Runs in each tool's wrapper function in `src/tools/`, before the underlying `@tool`-decorated call — per AGENT_LOGIC_SPEC.md Section 8's sanitization rules (URI allow-listing, numeric range checks, date validation).

**Rate Limits & Safeguards:**
- `extract_draw_packet_metadata`: token-bucket, capped per AGENT_ORCHESTRATION_BLUEPRINT.md Section 9.
- `dispatch_decision_notification`: token-bucket, same section.
- Circuit breaker: max 4 tool/structured-output calls per node per run (AGENT_LOGIC_SPEC.md Section 2's iteration limit); exceeding it is treated as a stall → Permanent Failure.

---

## **6. REASONING LOOP IMPLEMENTATION**

**Reasoning Cycle Structure:** Graph-based (Strands `GraphBuilder`) with a bounded per-node ReAct micro-loop, per AGENT_LOGIC_SPEC.md Section 2.

**Step-by-Step Reasoning Flow:**

**Step 1:** Graph entry node validates the incoming draw-packet payload against AGENT_ORCHESTRATION_BLUEPRINT.md Section 4 Step 1's Input Validation Expectations; writes `draw_packet_meta`.

**Step 2:** `ForensicAuditSentinel` and `FairPayStatutoryGuardian` begin execution in parallel (Strands `GraphBuilder` fan-out edge).

**Step 3:** Each node's internal loop: select next tool/structured-output call per its `<available_tools_and_triggers>` (native-thinking capture enabled only for `ForensicAuditSentinel`'s Sonnet 5 calls, per INTERFACE_OBSERVABILITY_SYSTEM.md Section 3a).

**Step 4:** Tool execution — sanitize input, call through `src/providers/get_runtime()`, validate output against its Pydantic V2 model.

**Step 5:** Result integration — write to `IroncladState` via the exact reducer declared for that field in `src/state/reducers.py`.

**Step 6:** Next-action determination — repeat Step 3 until all owned fields are populated or blocked by a discrepancy/error.

**Step 7:** Termination check — success (all owned fields resolved), failure (blocking error), or iteration-budget exhaustion (Section 5's circuit breaker).

**Tool Call Decision Flow:** Exactly as encoded in each node's `<primary_objective>`/`<hard_constraints_and_prohibitions>` XML tags (AGENT_LOGIC_SPEC.md Section 1) — the coding assistant implements the node's decision logic as literal Python control flow following those tags, never inventing an alternative decision heuristic.

**State Persistence Between Steps:** Every reducer write in Step 5 is immediately checkpointed per AGENT_ORCHESTRATION_BLUEPRINT.md Section 10's cadence (after Step 1 ingress, after the fan-in into `EverydayDecisionCardEmitter`, and after the HITL resolution) — not after every single micro-loop iteration, to avoid excessive checkpoint-write volume.

**Termination Conditions:**
1. Success — `decision_card_payload` written and `approval_state` resolved.
2. Failure — any node's blocking `error_logs` entry per AGENT_LOGIC_SPEC.md Section 1's stop conditions.
3. User abort — N/A in the traditional sense (no mid-run interrupt exists in this system per INTERFACE_OBSERVABILITY_SYSTEM.md Section 7); tab-close does not abort the backend run.

**Loop Prevention Mechanisms:**
- Max iterations: 4 tool/structured-output calls per node (Section 5).
- Progress detection: A cycle producing no new state write and no new `flagged_discrepancies`/`error_logs` entry is a stall.
- Circuit breaker: Stall detection converts to a Permanent Failure rather than retrying indefinitely.

---

## **7. INTERFACE & STREAMING INTEGRATION**

**Backend ↔ Frontend Connection Model:** The verified two-hop model from INTERFACE_OBSERVABILITY_SYSTEM.md Section 2 — Hop 1 (AgentCore Runtime → Streamlit server process) is SSE-over-HTTP via `boto3`'s AgentCore data-plane streaming response; Hop 2 (Streamlit server → browser) is Streamlit's own internal protocol, not implemented by this project directly.

**Typed Streaming Event Pipeline Implementation:**

| Event Type | Emitted By | Consumed By |
|---|---|---|
| `text-delta` | `src/ui/stream_consumer.py`, on status-banner string changes | `src/ui/app.py`'s status banner component |
| `reasoning-delta` | `src/agents/*.py` nodes, via `src/telemetry/tracing.py` hooks | `src/ui/generative_ui.py`'s Audit Trail sub-expanders |
| `tool-call-start` / `tool-call-delta` / `tool-call-result` | `src/tools/*.py` wrapper functions | `src/ui/generative_ui.py`'s per-node status lines and rendering components |
| `state-update` | `src/state/reducers.py`, on every successful write | `src/ui/app.py`'s card tiles/badge/table/timer AND `src/ui/generative_ui.py`'s Audit Trail |
| `approval-required` | `src/agents/graph.py`, on reaching the HITL interrupt node | `src/ui/app.py`, enabling the three action buttons |
| `error` | Any module raising `IroncladError` subclasses | `src/ui/app.py`'s error-state banner (Section 8 below) |
| `stream-end` | `src/ui/stream_consumer.py`, on interrupt or halt | `src/ui/app.py`, stops the spinner |

**Generative UI Wiring:** Each mapping in INTERFACE_OBSERVABILITY_SYSTEM.md Section 4a is implemented as one function in `src/ui/generative_ui.py` — `render_extraction_tree()`, `render_financial_tiles()`, `render_lien_badge_and_findings()`, `render_countdown_timer()`, `render_decision_card()`, `render_notification_toast()` — each taking the relevant typed state slice and returning Streamlit widget calls; no function renders raw JSON as a fallback path other than the explicitly documented schema-validation-failure fallback text.

**HITL Graph-Resumption Implementation:**

**Checkpoint: Decision Card Release Gate**
- **Pause Implementation:** `src/agents/graph.py`'s interrupt node writes the checkpoint and emits `approval-required`; execution genuinely suspends (Strands graph interrupt), it does not poll.
- **Resumption Handler:** `src/ui/hitl_resumption.py::submit_decision()` — called by the three Streamlit buttons in `src/ui/app.py`; builds the exact `{"action": ..., "checkpoint_id": ..., "modified_inputs": null, "reason": ...}` payload per INTERFACE_OBSERVABILITY_SYSTEM.md Section 5 and sends it through `src/providers/get_runtime()`.
- **Validation:** The backend (inside `src/agents/graph.py`'s resumption handler) rejects any payload where `action` is not exactly one of `APPROVE_RELEASE` / `HOLD_REQUEST_CORRECTION` / `ESCALATE_LEGAL`, or where `modified_inputs` is non-null, before writing `approval_state`.
- **Resume Mechanism:** The checkpointing backend (`src/state/checkpointing.py`) resumes the Strands graph from the exact interrupted node using the `checkpoint_id`, per AGENT_ORCHESTRATION_BLUEPRINT.md Section 10's resumability guarantee.

**Observability Hooks:** `src/telemetry/tracing.py` wraps every node invocation (`invoke_agent` span) and every tool call (`execute_tool` span) per the hierarchy in INTERFACE_OBSERVABILITY_SYSTEM.md Section 6; `src/telemetry/feedback_annotations.py` writes the Langfuse score immediately on `hitl_resumption.py::submit_decision()`, in the same logical transaction as the `approval_state` write (Section 7a's Write Timing requirement).

**Real-Time Update Mechanism:** `src/ui/stream_consumer.py` maintains the Hop-1 streaming iterator for the duration of one Streamlit rerun; on tab reload, `src/ui/app.py` re-fetches the current `IroncladState` snapshot directly via `get_runtime()` rather than replaying the event stream, per INTERFACE_OBSERVABILITY_SYSTEM.md Section 2a's Ordering & Backpressure Guarantees.

---

## **8. SAFETY, CONTROL & FAILURE HANDLING**

**Human-in-the-Loop Enforcement Points:**

**Approval Gate 1 — Decision Card Release (the only gate in this system):**
- Implementation: Section 7's HITL implementation.
- Timeout: No auto-timeout selects an action; per AGENT_BEHAVIOR_PROFILE.md Section 8, only `days_remaining ≤ 2` triggers the `URGENT_STATUTORY_ESCALATION` notification (via `dispatch_decision_notification`), implemented as a background check in `src/telemetry/tracing.py`'s span-close hook, not a UI timeout.

**Emergency Stop Mechanism:** None beyond tab-close, per INTERFACE_OBSERVABILITY_SYSTEM.md Section 8 — this system has no in-progress side effect to halt before the HITL gate (read/compute only) and no further action to take over after it (the three buttons are already the complete action set). Do not implement a stop button; implementing one would be a control not backed by AGENT_LOGIC_SPEC.md.

**Prohibition Enforcement (structural, not instructional):**
- No financial-transaction tool exists in `src/tools/` — Prohibition 1 is enforced by the absence of any such module, not a runtime check.
- `audit_retainage_math`, `verify_lien_chain_integrity`, `statutory_prompt_pay_clock` are the only modules permitted to write their respective numeric/date state fields — enforced by `src/state/reducers.py` raising `StateValidationError` if any other caller attempts the write (implemented as a per-field writer allow-list check inside each reducer function).
- `EverydayDecisionCardEmitter` has no import of any math/date tool — enforced by the module's own import statements containing only `DecisionCardPayload` and `dispatch_decision_notification`.
- Extracted document text never enters a system prompt string — enforced by `src/tools/extract_draw_packet_metadata.py` returning only typed Pydantic fields, never raw text blobs, to the calling node.

**Fallback Behaviors:**
- Tool failure: Section 5's Error Handling Strategy.
- Model unavailability: One retry on the primary model; on second failure, halt to `INCOMPLETE_MANUAL_AUDIT_REQUIRED` rather than silently falling back to the secondary model for a reasoning task it wasn't designed for (per AGENT_ORCHESTRATION_BLUEPRINT.md Section 8's Fallback Strategy).
- Network timeout: Transient classification, retry per Section 5.

**Logging & Audit Trail:**
- Log/trace format: OTel spans per INTERFACE_OBSERVABILITY_SYSTEM.md Section 6, dual-exported to CloudWatch (`bedrock-agentcore` namespace, automatic via AgentCore Runtime's ADOT auto-instrumentation in production) and Langfuse (via `langfuse==4.15.2`'s native OTLP ingestion).
- Log location: CloudWatch GenAI Observability console (production) / local trace export (development, `IRONCLAD_RUNTIME_MODE=mock`).
- Retention: Per the compliance database's own policy, outside this plan's scope (AGENT_ORCHESTRATION_BLUEPRINT.md Section 7).
- Privacy: Raw extracted PDF text is never logged as a span attribute (only as a filtered span event at most, per AGENT_LOGIC_SPEC.md Section 8's citation/grounding rules); no field not in `IroncladState` is ever logged.

---

## **9. AUTOMATED EVALUATION & TESTING FRAMEWORK**

**Testing Stack (Verified via Phase 1.5):**
- Test runner: `pytest` + `pytest-asyncio`, versions inherited from `strands-agents==1.42.0`'s own tested dev extras (Section 1) rather than independently pinned.
- LLM eval framework: `deepeval` — **Assumption — Unverified exact version**, chosen for its native `pytest` integration, keeping the entire test suite in one runner rather than introducing a second, Node-based eval CLI.
- Justification: AGENT_LOGIC_SPEC.md's grounding requirements (citation enforcement, silence-over-guessing, cross-examination) map directly onto `deepeval`'s hallucination/faithfulness metrics without needing a bespoke eval harness.

### **9.1 Test Data Strategy & Mocks**

**Mock Draw-Packet Inputs:**
1. **Simple Case:** A clean, fully-legible single-line-item packet with a valid unconditional waiver — expected `recommended_action: "APPROVE_RELEASE"`.
2. **Complex Case:** A multi-line-item packet with one line item missing its retainage percentage and one waiver with a pre-dated notary — expected `flagged_discrepancies` non-empty, `lien_chain_status: "SUSPECT_PRE_DATED_NOTARY"`, `recommended_action` forced away from `APPROVE_RELEASE`.
3. **Edge Case:** A packet whose rider clause is ambiguous and whose jurisdiction is unresolvable in the statutory table — expected both `FairPayStatutoryGuardian` fields left unset and corresponding `flagged_discrepancies`/`error_logs` entries, routing to `INCOMPLETE_MANUAL_AUDIT_REQUIRED`.

**Mock Tool Outputs (`tests/mocks/tool_responses/`):**

**`extract_draw_packet_metadata` Mock Response:**
```json
{
  "success": true,
  "document_type_detected": "G703_CONTINUATION",
  "line_items": [{"line_item_id": "LI-001", "description": "Concrete foundation", "contract_retainage_pct": 0.05, "current_billed": "12000.00", "stored_materials": "0.00", "prior_payments": "36000.00"}],
  "waiver_records": [],
  "low_confidence_fields": [],
  "error": null
}
```

**`audit_retainage_math` Mock Response:**
```json
{
  "success": true,
  "gross_amount_requested": "12000.00",
  "contractual_retainage_withheld": "600.00",
  "net_recommended_release": "11400.00",
  "calculation_trace": ["gross = 12000.00 + 0.00", "retainage = 12000.00 * 0.05", "net = 12000.00 - 600.00 - 36000.00"],
  "error": null
}
```

**`verify_lien_chain_integrity` Mock Response:**
```json
{"success": true, "lien_chain_status": "VALID", "findings": [{"waiver_id": "W-001", "finding": "OK"}], "error": null}
```

**`statutory_prompt_pay_clock` Mock Response:**
```json
{"success": true, "state": "TX", "days_remaining": 21, "deadline_timestamp": "2026-10-04T00:00:00Z", "penalty_interest_rate": "0.015", "statute_reference": "Tex. Prop. Code ch. 28 (reference-table v2026.3)", "error": null}
```

**`dispatch_decision_notification` Mock Response:**
```json
{"success": true, "dispatched_to": ["GENERAL_CONTRACTOR", "OWNER", "SUBCONTRACTOR"], "error": null}
```

### **9.2 Unit & Integration Tests**

**First Tests (Must Pass Before Proceeding):**
- [ ] Environment variables loaded correctly (`.env` parsed, no missing required keys for the active `IRONCLAD_RUNTIME_MODE`)
- [ ] `IRONCLAD_RUNTIME_MODE=mock` path requires zero AWS/Langfuse credentials to run
- [ ] All dependencies installed per Section 2's verified manifest (`uv sync --all-extras` exits 0)
- [ ] Both configured models respond to a trivial test prompt through `mock_runtime.py`
- [ ] Every reducer in `src/state/reducers.py` passes `tests/unit/test_reducers.py` (append-only never drops, merge-by-key never cross-overwrites, last-write-wins resolves deterministically, immutable-after-init rejects writes)
- [ ] Checkpointing backend read/write/resume round-trip succeeds (both SQLite dev path and, separately, the `AgentCoreMemorySessionManager` production path)
- [ ] All six tools register without errors and validate against both their Pydantic V2 and MCP/strict JSON Schema forms

### **9.3 LLM-Specific Evaluation Suites**

**Tool-Calling Accuracy Evals (`tests/evals/test_tool_calling_accuracy.py`):**
- Given the Simple Case mock packet, assert `ForensicAuditSentinel` calls `extract_draw_packet_metadata` exactly once, then `audit_retainage_math` with parameters matching the normalized `LineItem`.
- Given the Simple Case, assert `FairPayStatutoryGuardian` calls `statutory_prompt_pay_clock` with `contract_clause` exactly matching `RiderClauseClassification`'s output — never a hardcoded default.
- Assert no node ever calls a tool not in its own `<available_tools_and_triggers>` list (AGENT_LOGIC_SPEC.md Section 1).

**Hallucination Prevention Evals (`tests/evals/test_hallucination_resistance.py`):**
- Given the Complex Case's missing-retainage-percentage line item, assert `ForensicAuditSentinel` never calls `audit_retainage_math` for that item and instead appends the exact `MISSING_RETAINAGE_CLAUSE`-style discrepancy.
- Assert every dollar figure and date in the final `decision_card_payload` matches, byte-for-byte, a value present in some prior tool's recorded output — no field is model-generated prose.
- Assert the Edge Case's unresolvable jurisdiction produces `statutory_prompt_pay_clock: null` in state, never a defaulted state's rule.

**HITL Graph Resumption Evals (`tests/evals/test_hitl_resumption.py`):**
- Trigger the HITL gate on the Simple Case; send `{"action": "APPROVE_RELEASE", "checkpoint_id": ..., "modified_inputs": null}`; assert `approval_state` is set and the graph reaches its success terminal state.
- Send `{"action": "HOLD_REQUEST_CORRECTION", ..., "reason": "test"}`; assert the correction-dispatch path fires and the Langfuse annotation (Section 7a) is written with the matching `reason`.
- Send a payload with `modified_inputs` non-null; assert the resumption handler rejects it before any state write occurs.
- Send a payload with `action: "DENY"` (not one of the three valid literals); assert rejection with no state mutation.

**Grounding & Citation Evals:**
- Given a synthetic waiver whose `associated_line_item_id` does not exist in `extracted_line_items`, assert `ForensicAuditSentinel` surfaces a `TYPE_MISMATCH` discrepancy rather than silently associating it with another line item.

### **9.4 "Agent Is Working" Success Criteria**

- [ ] A draw-packet event correctly triggers graph ingress and produces `draw_packet_meta`
- [ ] Both parallel tracks (`ForensicAuditSentinel`, `FairPayStatutoryGuardian`) complete and write their exact declared fields
- [ ] `EverydayDecisionCardEmitter` assembles `decision_card_payload` only after both tracks complete, never partially
- [ ] The HITL gate pauses correctly and resumes correctly on all three valid actions
- [ ] Prohibitions are enforced (all Section 8 negative tests pass)
- [ ] The Streamlit UI displays the card via the exact typed streaming events (Section 7)
- [ ] Every generative UI component from INTERFACE_OBSERVABILITY_SYSTEM.md Section 4a renders correctly against mock data
- [ ] Telemetry spans are captured per the verified OTel hierarchy and appear in both CloudWatch (production) and Langfuse
- [ ] The reviewer's decision is written as a structured Langfuse annotation per Section 7a
- [ ] Errors are handled per Section 9's Tool-Specific Failure Mapping Table (INTERFACE_OBSERVABILITY_SYSTEM.md Section 9), never silently swallowed

### **9.5 Failure Scenarios to Simulate**

1. OCR tool times out (Transient) — verify 3x exponential-backoff retry, then success or Permanent escalation
2. Illegible/corrupt PDF (Permanent) — verify no card renders, `INCOMPLETE_MANUAL_AUDIT_REQUIRED` state reached
3. Negative billing figure passed to `audit_retainage_math` — verify rejection, no guessed correction
4. Empty waiver list passed to `verify_lien_chain_integrity` — verify rejection before the tool call is even attempted
5. Unresolvable jurisdiction — verify `statutory_prompt_pay_clock` failure path, card never shows a fabricated countdown
6. HITL approval outstanding past the critical statutory threshold — verify `URGENT_STATUTORY_ESCALATION` fires exactly once, `approval_state` remains null
7. Malformed tool output (fails Pydantic validation) — verify it never reaches `IroncladState`

### **9.6 Non-Negotiable Verification Requirements**

- No infinite loops possible (Section 6's circuit breaker verified under test)
- All prohibitions structurally enforced (Section 8, negative tests pass)
- No emergency-stop control exists where none is specified (verified by its deliberate absence, not its presence)
- Every reducer behaves exactly as declared under concurrent/sequential writes
- The single HITL checkpoint has a working resumption path for all three valid actions, and rejects every invalid one
- Logs/traces capture all critical events in both CloudWatch and Langfuse

---

## **10. STEP-BY-STEP EXECUTION SEQUENCE**

**STEP 1: Environment Setup**
- Action: Create `.env` from `.env.example` with all variables from Section 2; set `IRONCLAD_RUNTIME_MODE=mock` for initial development.
- Verification: `printenv | grep IRONCLAD_RUNTIME_MODE` shows `mock`.
- Dependencies: None.
- Safe to run: Yes (idempotent).

**STEP 2: Initialize Project Manifest & Install Dependencies**
- Action: Create `pyproject.toml` per Section 2; run `uv sync --all-extras`.
- Verification: Resolution completes with no conflicts; `uv.lock` pins exact versions for every "Assumption — Unverified" package in Section 2's Version Verification Log — re-flag any that still can't be confirmed.
- Dependencies: STEP 1.
- Safe to run: Yes (idempotent).

**STEP 3: Generate Coding Assistant Context Files**
- Action: Write both `CLAUDE.md` and `.cursorrules` from Section 3 to the project root.
- Verification: Both files exist and are byte-identical in content.
- Dependencies: STEP 2.
- Safe to run: Yes (idempotent).

**STEP 4: Scaffold Directory Structure**
- Action: Create the full tree from Section 2, including the mandated `src/providers/` module (with all 4 provider files).
- Verification: Directory tree matches Section 2 exactly, including `base_runtime.py`, `bedrock_runtime.py`, `staging_runtime.py`, `mock_runtime.py`.
- Dependencies: STEP 2.
- Safe to run: Yes (idempotent).

**STEP 5: Implement the Provider Abstraction Scaffold**
- Action: Implement `src/providers/base_runtime.py` as an abstract `BaseRuntimeProtocol` declaring the methods all three runtimes must implement — at minimum: `async def invoke_model(...)`, `async def call_mcp_tool(...)`, `async def read_checkpoint(session_id)`, `async def write_checkpoint(session_id, state)`, `async def resume_from_checkpoint(checkpoint_id, resumption_payload)`. Implement `mock_runtime.py` to satisfy this protocol entirely from `tests/mocks/` fixtures (zero network calls). Implement `staging_runtime.py` to perform real live multimodal PDF document extraction, semantic classification, and tool calling with `gemini-3.8-flash` via the official `google-genai` SDK using `GEMINI_API_KEY`. Implement `bedrock_runtime.py` to satisfy it via Bedrock AgentCore Runtime with lazy `boto3` client loading. Implement `src/providers/__init__.py::get_runtime()` to select between `"bedrock"`, `"staging"`, and `"mock"` based on `IRONCLAD_RUNTIME_MODE`.
- Verification: `MockRuntime`, `StagingRuntime`, and `BedrockRuntime` all satisfy `BaseRuntimeProtocol`; a test importing `get_runtime()` with each mode set returns the correct concrete class.
- Dependencies: STEP 4.
- Safe to run: Yes.

**STEP 6: Initialize Orchestration Framework**
- Action: Scaffold `src/agents/graph.py` with an empty `GraphBuilder` instance.
- Verification: Section 4 Step 1's import check passes.
- Dependencies: STEP 5.
- Safe to run: Yes.

**STEP 7: Configure Models**
- Action: Implement Section 4 Step 2's model bindings, routed through `get_runtime()`.
- Verification: Trivial model call succeeds via `mock_runtime.py`.
- Dependencies: STEP 1 (env vars), STEP 6.
- Safe to run: Yes.

**STEP 8: Implement Typed State Schema & Reducers**
- Action: Implement `src/state/schema.py` and `src/state/reducers.py` exactly per AGENT_ORCHESTRATION_BLUEPRINT.md Section 3.
- Verification: `tests/unit/test_reducers.py` passes in full.
- Dependencies: STEP 2 (Pydantic installed).
- Safe to run: Yes.

**STEP 9: Initialize Checkpointing Backend**
- Action: Implement `src/state/checkpointing.py` for both SQLite (dev) and `AgentCoreMemorySessionManager` (prod) paths, selected via `IRONCLAD_RUNTIME_MODE`.
- Verification: Checkpoint write/read/resume round-trip test passes in `mock` mode.
- Dependencies: STEP 8.
- Safe to run: Yes.

**STEP 10: Initialize the Statutory Reference Lookup**
- Action: Implement `src/statutory_reference/lookup.py` against a local fixture table in `mock` mode.
- Verification: Known-jurisdiction and unresolvable-jurisdiction test cases both pass.
- Dependencies: STEP 1, STEP 2.
- Safe to run: Yes.

**STEP 11: Register Tools**
- Action: Implement all six tools per Section 5's sequence, each with both schema formats.
- Verification: Each tool passes its individual mock-data invocation test from Section 9.1/9.2.
- Dependencies: STEP 7 (models), STEP 5 (providers).
- Safe to run: Yes.

**STEP 12: Implement Structured Outputs**
- Action: Implement `LineItemMappingAndDiscrepancy`, `RiderClauseClassification`, `DecisionCardPayload` in `src/structured_outputs/`.
- Verification: Each validates against its Pydantic V2 model and strict JSON Schema from AGENT_LOGIC_SPEC.md Section 5.
- Dependencies: STEP 11.
- Safe to run: Yes.

**STEP 13: Wire Orchestration Graph**
- Action: Complete `src/agents/graph.py`'s fan-out/fan-in topology per AGENT_ORCHESTRATION_BLUEPRINT.md Section 4.
- Verification: Graph structure matches exactly — 3 nodes, documented edges only.
- Dependencies: STEP 6, STEP 11, STEP 12.
- Safe to run: Yes.

**STEP 14: Implement Reasoning Loops**
- Action: Implement each node's bounded ReAct micro-loop per Section 6.
- Verification: Single-run test using the Simple Case mock packet produces a correct `decision_card_payload`.
- Dependencies: STEP 13.
- Safe to run: Yes (mock mode).

**STEP 15: Implement Safety Guardrails**
- Action: Implement Section 8's structural prohibition enforcement (writer allow-lists in reducers, import-boundary checks).
- Verification: All Section 9's negative tests pass — a simulated out-of-scope tool call raises `ProhibitedActionError` rather than executing.
- Dependencies: STEP 14.
- Safe to run: Yes (test mode).

**STEP 16: Implement Telemetry Integration**
- Action: Implement `src/telemetry/tracing.py` and `feedback_annotations.py`.
- Verification: A test run produces the correct span hierarchy (trace → `invoke_agent` × 3 → `execute_tool`/`inference` children) in a local OTel exporter; a mock HITL decision writes a Langfuse score.
- Dependencies: STEP 14.
- Safe to run: Yes.

**STEP 17: Implement Typed Streaming Layer**
- Action: Implement `src/ui/event_types.py` and `src/ui/stream_consumer.py`.
- Verification: Every event type in Section 7's table is emitted at least once during a Simple Case mock run.
- Dependencies: STEP 14, STEP 16.
- Safe to run: Yes.

**STEP 18: Implement HITL Resumption Endpoint**
- Action: Implement `src/ui/hitl_resumption.py::submit_decision()` and the graph-side resumption handler.
- Verification: All `tests/evals/test_hitl_resumption.py` scenarios from Section 9.3 pass.
- Dependencies: STEP 9 (checkpointing), STEP 17.
- Safe to run: Yes.

**STEP 19: Build the Streamlit Executive Decision Card**
- Action: Implement `src/ui/app.py` and `src/ui/generative_ui.py` per INTERFACE_OBSERVABILITY_SYSTEM.md Sections 2 and 4a.
- Verification: `streamlit run src/ui/app.py` loads locally in `mock` mode, renders the card and Audit Trail correctly against the Simple, Complex, and Edge Case mocks.
- Dependencies: STEP 17, STEP 18.
- Safe to run: Yes.

**STEP 20: Package AgentCore Deployment Manifests & Container Specification**
- Action: Scaffold production `agentcore.yaml`, `Dockerfile`, and `src/main.py` entrypoint targeting Amazon Bedrock AgentCore Runtime. Validate container build specifications and manifest schemas locally. Do NOT execute live cloud resource provisioning without authenticated billing credentials.
- Verification: `agentcore.yaml` passes schema linting; local Docker build completes successfully.
- Dependencies: STEP 15, STEP 16.
- Safe to run: Yes (local container & manifest validation only; zero cloud spend).

**STEP 21: Run Automated Evaluation Suites**
- Action: Execute the full `tests/` suite (unit, integration, LLM evals, HITL resumption) against `mock` mode first, then against the live `staging` mode (and `bedrock` mode if configured).
- Verification: All tests pass in both modes; all Section 9.6 Non-Negotiable Verification Requirements are met.
- Dependencies: ALL previous steps.
- Safe to run: Yes.

**STEP 22: End-to-End Verification & Deploy the Streamlit Frontend**
- Action: Set `IRONCLAD_RUNTIME_MODE=staging`, run a complete flow from a real ingress event through one full HITL approval cycle using the live `gemini-3.8-flash` staging engine; deploy `src/ui/app.py` to Streamlit Community Cloud with `GEMINI_API_KEY` configured in secrets.
- Verification: All Section 9.4 success criteria pass end-to-end; the deployed Streamlit URL is reachable publicly with 100% uptime, rendering a live decision card from real draw packets with live AI reasoning and zero AWS credential dependency.
- Dependencies: STEP 21 passed.
- Safe to run: Yes (final verification on zero-cost public hosting).

**STEP 23: Production Readiness Check**
- Action: Review every checklist in Section 9, run all Section 9.5 failure simulations against `bedrock` mode, confirm the production/local configuration distinctions from Section 2 are correctly split.
- Verification: All non-negotiable criteria met.
- Dependencies: STEP 22 passed.
- Safe to run: Yes.

---

## **EXECUTION PLAN INTEGRITY DECLARATION**

This master plan is AUTHORITATIVE and COMPLETE.

Downstream code generation systems must:
- Execute steps in exact order specified
- Verify each step before proceeding
- Never skip steps
- Never combine steps
- Never invent logic not specified
- Never modify specifications
- Never install an unverified or deprecated package version
- Follow the coding-assistant context file's rules and anti-patterns without exception
- Halt on verification failure

This plan eliminates all execution ambiguity.
Every dependency is explicit and version-verified.
Every verification is defined.
Every failure mode is anticipated.

Implementation is now deterministic and mechanical.

---
