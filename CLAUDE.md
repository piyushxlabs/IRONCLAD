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
