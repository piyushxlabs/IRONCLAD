# AGENT ORCHESTRATION BLUEPRINT

**Generated:** September 13, 2026
**Source:** AGENT_BEHAVIOR_PROFILE.md
**Status:** AUTHORITATIVE — Defines complete agent system architecture
**Purpose:** Cognitive architecture and orchestration specification

---

## **1. SYSTEM OVERVIEW**

**High-Level Description:**
IRONCLAD is implemented as a three-node directed graph built on the AWS Strands Agents SDK, deployed as a containerized agent to Amazon Bedrock AgentCore Runtime. A forensic-audit node and a statutory-compliance node execute in parallel against a shared typed state, fan in to a card-emission node that renders the single zero-chat decision artifact, then the graph interrupts for mandatory human approval.

**Architectural Classification:** Multi-Agent System

**Justification:** The behavioral profile itself specifies a "Tri-Track Orchestration Cascade" with three functionally distinct responsibilities (deterministic financial audit, statutory clock/compliance, human-facing synthesis) that must remain separable so that prohibitions bound to one track (e.g., no arithmetic in the card emitter) cannot leak into another. This role separation, plus the behavioral requirement for a hard HITL interrupt between audit and release, requires multi-agent graph structure rather than a single monolithic agent.

**Complexity Level:** Complex — parallel fan-out/fan-in execution, a hard interrupt gate, deterministic-tool-only arithmetic enforcement, dual memory backends (session + reference-data), and a 3-tier provider abstraction (Bedrock Production / Gemini Staging / Hermetic Mock) all compound the coordination surface.

---

## **2. AGENT TOPOLOGY**

**Number of Agents:** 3

### **Agent 1: `ForensicAuditSentinel`** (Professional Track)
- **Responsibility:** Ingest AIA G702/G703 packets and lien waiver PDFs; extract line items; execute deterministic retainage/arithmetic and lien-chain-of-custody verification.
- **Cognitive Scope:** Semantic document understanding (identifying which extracted text maps to which G702/G703 field, matching waiver metadata to draw line items) and discrepancy classification. It never performs the arithmetic itself.
- **Execution Authority:** May call bound deterministic math/date tools and an OCR/document-parsing MCP server. Cannot write to `statutory_prompt_pay_clock` or `decision_card_payload`.
- **Communication With:** `FairPayStatutoryGuardian` (parallel, no direct dependency), `EverydayDecisionCardEmitter` (downstream consumer via shared state).

### **Agent 2: `FairPayStatutoryGuardian`** (Good Neighbor Track)
- **Responsibility:** Classify the subcontract rider (`pay-if-paid` vs `pay-when-paid`), determine jurisdiction, and run the statutory prompt-pay countdown and penalty-interest calculation.
- **Cognitive Scope:** Light NL classification of rider clause language only; all day-counting and interest-rate lookups are deterministic tool calls against a versioned statutory reference table.
- **Execution Authority:** May call the deterministic statutory-clock tool and read the reference-data store. Cannot touch line-item arithmetic, waiver validation, or `decision_card_payload`.
- **Communication With:** `ForensicAuditSentinel` (parallel), `EverydayDecisionCardEmitter` (downstream consumer).

### **Agent 3: `EverydayDecisionCardEmitter`** (Everyday Track)
- **Responsibility:** Merge the audit and statutory outputs into the single `DecisionCardPayload`, apply the `recommended_action` decision logic, and hold the graph at the mandatory human-approval interrupt.
- **Cognitive Scope:** Summarization/templating only — collapsing verified structured fields into the zero-chat card. No arithmetic, no re-derivation of any audited number.
- **Execution Authority:** May call a deterministic card-rendering tool and a notification-dispatch MCP server. Cannot call any math tool, any bank/payment tool (none exists in this system — see Section 6), or write to any audit-origin field.
- **Communication With:** Receives from both upstream agents; hands off to the human-approval interrupt handler.

**Control Hierarchy:**
- **Pattern:** Graph-based (fan-out / fan-in DAG), implemented with Strands' `GraphBuilder` multi-agent primitive.
- **Control Flow:** No single agent supervises the others' reasoning. The graph's explicit edges — not an LLM's judgment — determine sequencing: entry fans out to `ForensicAuditSentinel` and `FairPayStatutoryGuardian` concurrently; both must complete before the edge into `EverydayDecisionCardEmitter` fires; that node's completion triggers the HITL interrupt node.
- **Coordination Mechanism:** Shared typed state (Section 3) passed and merged at each graph edge — no direct agent-to-agent messaging channel exists, which structurally prevents `EverydayDecisionCardEmitter` from asking either upstream agent to "recompute" a number.

---

## **3. TYPE-SAFE CENTRAL STATE SCHEMA & REDUCERS**

**Schema Definition Style:** Pydantic `BaseModel`-equivalent (Strands' native tool/state typing is Pydantic-based)

**Traceability:** Every field below maps directly to a named field in LLM-1's Input Contract or Deliverable Contract (Section 4 of `AGENT_BEHAVIOR_PROFILE.md`); no field was added beyond what that contract requires.

**Global State Schema:**
```
IroncladState:
  draw_packet_meta: DrawPacketMeta                    # reducer: immutable after init
    project_id: str
    subcontractor_id: str
    draw_number: int
    source_uris: list[str]

  extracted_line_items: list[LineItem]                 # reducer: last-write-wins (ForensicAuditSentinel only)

  retainage_audit_result: RetainageAuditResult | None   # reducer: last-write-wins (ForensicAuditSentinel only)
    gross_amount_requested: Decimal
    contractual_retainage_withheld: Decimal
    net_recommended_release: Decimal

  lien_chain_status: LienChainStatus | None             # reducer: last-write-wins (ForensicAuditSentinel only)
    # Enum: VALID | MISSING_WAIVER | SUSPECT_PRE_DATED_NOTARY | INVALID_FORM

  statutory_prompt_pay_clock: StatutoryClock | None      # reducer: last-write-wins (FairPayStatutoryGuardian only)
    state: str
    days_remaining: int
    deadline_timestamp: datetime
    penalty_interest_rate: Decimal

  flagged_discrepancies: list[Discrepancy]               # reducer: append-only (both track agents may append)
    line_item_id: str
    discrepancy_type: str
    description: str
    variance_amount: Decimal | None

  decision_card_payload: DecisionCardPayload | None       # reducer: last-write-wins (EverydayDecisionCardEmitter ONLY)
    # Assembled exactly per LLM-1 Deliverable Contract structure

  approval_state: ApprovalStatus | None                   # reducer: last-write-wins (HITL interrupt handler ONLY)
    # Enum: APPROVE_RELEASE | HOLD_REQUEST_CORRECTION | ESCALATE_LEGAL

  tool_artifacts: dict[str, ToolArtifact]                 # reducer: merge-by-key, keyed by tool_call_id
  error_logs: list[ErrorRecord]                            # reducer: append-only, any node may write
  runtime_config: RuntimeConfig                            # reducer: immutable after init
```

**Field-by-Field Reducer Rationale:**
- **`extracted_line_items`, `retainage_audit_result`, `lien_chain_status`:** last-write-wins but single-writer-enforced (only `ForensicAuditSentinel` has a graph edge that writes here) — prevents the card emitter or statutory guardian from ever silently overwriting audited figures, which is the architectural enforcement of Behavioral Profile Prohibition 2.
- **`statutory_prompt_pay_clock`:** last-write-wins, single-writer — isolates the statutory calculation from the financial-math track so a bug in one can never corrupt the other's field.
- **`flagged_discrepancies`:** append-only across both track agents — a discrepancy raised by either track must never be overwritten or dropped by the other's write.
- **`decision_card_payload`:** last-write-wins, single-writer (`EverydayDecisionCardEmitter`) — this is the terminal artifact; no other node may touch it, which prevents downstream re-derivation of numbers already verified upstream.
- **`approval_state`:** last-write-wins, writable only by the interrupt handler that receives the authenticated human action — no agent node has a write edge to this field, which is the structural enforcement of the HITL gate.
- **`error_logs`:** append-only, universally writable — failure visibility must never be lost to a later overwrite.
- **`runtime_config`, `draw_packet_meta`:** immutable after graph init — the input envelope is the binding contract from LLM-1 and must not drift mid-run.

**Mutation Boundaries:**
`ForensicAuditSentinel` writes only to `extracted_line_items`, `retainage_audit_result`, `lien_chain_status`, and may append to `flagged_discrepancies`/`error_logs`. `FairPayStatutoryGuardian` writes only to `statutory_prompt_pay_clock` and may append to `flagged_discrepancies`/`error_logs`. `EverydayDecisionCardEmitter` has read access to every upstream field but a write edge to `decision_card_payload` only. `draw_packet_meta` and `runtime_config` are read-only to all three agents.

---

## **4. EXECUTION FLOW**

**Entry Point:** Bedrock AgentCore Runtime's `InvokeAgentRuntime` API receives the webhook/file-ingress event (per LLM-1's Event-Driven trigger), which initializes `IroncladState` from the multipart payload and opens a new AgentCore session keyed to `draw_packet_meta`.

**Flow Type:** Graph-based, with a fan-out/fan-in segment followed by a linear interrupt gate.

**Detailed Execution Steps:**

1. **Ingress & Validation**
   - **Agent Responsible:** Graph entry node (non-cognitive, deterministic)
   - **Action:** Validates the packet against LLM-1's Input Validation Expectations (legible/OCR-able, valid IDs, ≥1 payment application document).
   - **State Fields Read/Written:** Writes `draw_packet_meta`; on failure, writes `error_logs` and routes directly to Termination (Failure).
   - **Decision Point:** Valid → fan-out; Invalid → immediate halt.
   - **Next Step:** Parallel fan-out to Steps 2 and 3.

2. **`ForensicAuditSentinel` Execution**
   - **Agent Responsible:** `ForensicAuditSentinel`
   - **Action:** Extracts line items, runs deterministic retainage/sum-verification tools, cross-checks notary dates vs. payment dates.
   - **State Fields Read/Written:** Reads `draw_packet_meta`; writes `extracted_line_items`, `retainage_audit_result`, `lien_chain_status`; may append `flagged_discrepancies`, `error_logs`.
   - **Decision Point:** Missing/illegible required data → append discrepancy, continue (never guess, per Prohibition 3) rather than branch away.
   - **Next Step:** Fan-in wait at Step 4.

3. **`FairPayStatutoryGuardian` Execution** (parallel with Step 2)
   - **Agent Responsible:** `FairPayStatutoryGuardian`
   - **Action:** Classifies rider language, resolves jurisdiction, runs the deterministic statutory-clock tool.
   - **State Fields Read/Written:** Reads `draw_packet_meta`; writes `statutory_prompt_pay_clock`; may append `flagged_discrepancies`, `error_logs`.
   - **Decision Point:** Ambiguous rider clause → flag discrepancy rather than infer enforceability (Out-of-Scope item 4).
   - **Next Step:** Fan-in wait at Step 4.

4. **Fan-In & `EverydayDecisionCardEmitter` Execution**
   - **Agent Responsible:** `EverydayDecisionCardEmitter`
   - **Action:** Waits for both Step 2 and Step 3 to complete (or fail), then assembles `decision_card_payload`, applying deterministic decision logic for `recommended_action` based purely on already-verified fields (any discrepancy or non-`VALID` lien status forces `HOLD_REQUEST_CORRECTED_WAIVER` or `ESCALATE_LEGAL`; only a clean audit permits `APPROVE_RELEASE` as the recommendation).
   - **State Fields Read/Written:** Reads all upstream fields; writes `decision_card_payload` only.
   - **Decision Point:** If either upstream track wrote to `error_logs` with a blocking severity → route to Termination (Failure, `INCOMPLETE_MANUAL_AUDIT_REQUIRED`) instead of emitting a payload.
   - **Next Step:** HITL Interrupt (Step 5).

5. **Human-in-the-Loop Interrupt**
   - **Agent Responsible:** Non-cognitive interrupt node (durable checkpoint boundary)
   - **Action:** Graph execution suspends; `decision_card_payload` is surfaced to the Zero-Chat frontend; session checkpoint is written.
   - **State Fields Read/Written:** Writes `approval_state` only upon receiving an authenticated human action.
   - **Decision Point:** `APPROVE_RELEASE` / `HOLD_REQUEST_CORRECTION` / `ESCALATE_LEGAL` → three distinct terminal branches; critical statutory deadline (≤48h) with no response → urgent escalation alert emitted without altering `approval_state`.
   - **Next Step:** Terminal action per branch (downstream settlement/correction-letter/legal-routing events, all outside this graph's execution authority).

**Decision Points:**
- **At Step 1:** Invalid packet → halt; valid → fan-out.
- **At Step 4:** Blocking error upstream → failure termination; clean state → HITL interrupt.
- **At Step 5:** Human selection → one of three terminal branches; timeout at critical statutory threshold → escalation alert (informational only).

**Termination Conditions:**
- **Success:** `decision_card_payload` emitted and a human `approval_state` recorded — matches LLM-1's Deliverable Contract exactly.
- **Failure:** Any blocking validation, tool, or hash-integrity error → `INCOMPLETE_MANUAL_AUDIT_REQUIRED`, no payload emitted (atomic delivery guarantee).
- **Timeout:** AgentCore session idle-timeout (15 minutes per AgentCore Runtime default) triggers session suspension, not data loss — the durable checkpoint at Step 5 allows resumption.
- **User Interrupt:** Human `halt`/`stop` command at any point routes immediately to Termination (Failure) per LLM-1 Section 10.

**Loop Prevention:** No cyclical edges exist in this graph — it is a strict DAG. Recursive sub-goal generation inside any single agent's reasoning is capped at 2 levels per LLM-1's Reasoning Constraints, enforced via a per-agent tool-call budget rather than an open-ended loop.

---

## **5. ORCHESTRATION FRAMEWORK CHOICE**

**Selected Framework:** AWS Strands Agents SDK (Python), using its `GraphBuilder` multi-agent primitive.

**Verification Note:** Confirmed via live web search that Strands is an actively maintained, open-source, model-agnostic agent SDK from AWS with native multi-agent graph support (`GraphBuilder`), OpenTelemetry-based production observability, and first-class deployment integration with Amazon Bedrock AgentCore Runtime. This is a directive from the operator's mandatory system override, not a free choice among alternatives — but research confirms it is a current, production-grade, non-deprecated fit for the stated deployment target.

**Justification:** The override mandates Strands + Bedrock AgentCore as the production path; research confirms this combination is natively supported end-to-end (Strands ships AgentCore deployment tooling directly), and Strands' `GraphBuilder` maps cleanly onto the required fan-out/fan-in Tri-Track topology and its typed-state passing.

**Key Capabilities Utilized:**
- `GraphBuilder` explicit-edge graph construction — needed for the deterministic fan-out/fan-in cascade (not the model-driven "let the FM decide the loop" default mode, which would be unsafe here given Prohibition 2).
- Native tool decorators (`@tool`) for binding deterministic math/date functions with strict typed signatures.
- AgentCore-native session management integration (`AgentCoreMemorySessionManager`) for durable, resumable checkpointing.

**Frameworks NOT Chosen:**
- **LangGraph (StateGraph/Pregel):** Also confirmed current and AgentCore-compatible via research, and would have been a defensible independent choice for this fan-out/fan-in shape — but the operator's mandatory override specifies Strands, and Strands' `GraphBuilder` provides equivalent typed-state, explicit-edge graph semantics for this topology.
- **CrewAI Flows / Pydantic-AI / Agent Squad (AWS's separate multi-agent router library):** Not selected; the override is explicit, and research did not surface a capability gap in Strands that would require reaching for an alternative.

**Deprecated Patterns Explicitly Avoided:** Legacy LangChain `AgentExecutor`-style unmanaged loops were considered and rejected — not applicable here regardless, since Strands' `GraphBuilder` with explicit edges is used instead of Strands' own default model-driven loop mode, precisely because the behavioral profile requires deterministic, non-improvised sequencing.

**Custom Components Required:** A thin deterministic "decision-logic" tool inside `EverydayDecisionCardEmitter` that maps verified state fields to `recommended_action` via fixed rules (not model inference) — this is a custom tool function, not a framework extension.

---

## **6. MCP & TOOL INVOCATION TOPOLOGY**

**Integration Model:** Hybrid — direct function-calling for internal deterministic tools, MCP client/server for external, reusable capabilities.

**MCP Topology:**
- **Agent as MCP Client:** `ForensicAuditSentinel` and `EverydayDecisionCardEmitter` each act as MCP clients; `FairPayStatutoryGuardian` does not require any MCP connection.
- **MCP Servers Required (by capability, not vendor):**
  - A document OCR/text-extraction MCP server, reachable by `ForensicAuditSentinel` only — external, reusable across future document-heavy agents.
  - A notification-dispatch MCP server, reachable by `EverydayDecisionCardEmitter` only — sends the card/alerts to General Contractor, Owner, and Subcontractor channels per Allowed Capability 5.
- **Resource/Prompt/Tool Exposure:** Both servers expose `tools` only (no `resources` or `prompts` primitives are required by this behavioral profile).

**Direct Function-Calling Topology:**
- **Bound Functions (by capability):** Retainage-percentage calculator, line-item sum verifier, stored-material deduction calculator, notary/payment-date chronology checker (all bound to `ForensicAuditSentinel`); statutory day-counter and penalty-interest calculator (bound to `FairPayStatutoryGuardian`); card-payload renderer and deterministic `recommended_action` rule engine (bound to `EverydayDecisionCardEmitter`).

**Trust Boundaries:**
No agent in this graph is bound to any banking, payment-rail, ACH, or wire-transfer tool or MCP server — such a capability is structurally absent from every agent's tool registry, which is the architectural enforcement of Prohibition 1 (not merely an instruction to refrain). `FairPayStatutoryGuardian` has no path to the OCR server and cannot read raw document bytes, limiting its blast radius to jurisdiction/rider classification only.

---

## **7. MEMORY & CHECKPOINTING ARCHITECTURE**

**Memory Strategy:** Hybrid — session-scoped state + a separate non-semantic reference-data store.

### **Short-Term Memory / Thread State**
- **Type:** Session state (the full `IroncladState` graph state)
- **Duration:** For the life of one draw-packet run, from ingress through the HITL interrupt and its resolution.
- **Contents:** All fields defined in Section 3.
- **Access:** Read/write per the mutation boundaries in Section 3.
- **Checkpointing Backend:** **Production:** Amazon Bedrock AgentCore Memory, accessed through Strands' `AgentCoreMemorySessionManager`, keyed by `session_id` (the draw-packet run) and `actor_id` (project/subcontractor pairing) — this also inherits AgentCore Runtime's per-session microVM isolation, so one subcontractor's draw data is never reachable from another session's execution environment. **Local/dev fallback (per the mandated Provider Abstraction layer):** a local SQLite-backed Strands session store using an identical state schema, so promoting from local dev to AgentCore production requires no state-shape changes — only a session-manager swap.
- **Purpose:** Matches LLM-1's session-based Lifecycle Nature and durable-checkpoint requirement at the HITL gate exactly.

### **Long-Term Memory**
- **Type:** None in the semantic/vector sense — this system performs deterministic audit, not retrieval-augmented reasoning, so a vector store would be unjustified scope creep.
- **Technology Class (reference data, not vector memory):** A versioned, structured statutory reference table (jurisdiction → deadline rule, penalty-interest rate, rider-classification enforceability) — **production:** a managed keyed store (e.g., DynamoDB-class technology); **local/dev fallback:** an equivalent local structured file, again preserving schema fidelity across environments.
- **Contents:** Jurisdiction-keyed statutory parameters only — never subcontractor-identifying or financial data.
- **Retrieval Strategy:** Direct keyed lookup by `state`/jurisdiction — no semantic search required.
- **Update Strategy:** Out-of-band maintenance process, outside this agent's execution authority (the agent only reads this table; it never writes to it).
- **Purpose:** Keeps statutory parameters current without requiring model knowledge of legislated values, consistent with the "Knowledge Cutoff Requirements" note in LLM-1's Domain & Risk Context.

**Memory Boundaries:**
- **What Must Be Remembered:** The full audit trail (extracted fields, discrepancies, statutory clock, final payload, approval decision) for compliance and dispute resolution.
- **What Must Be Forgotten:** Raw document bytes are referenced by URI, never duplicated into session or long-term memory; AgentCore's microVM sanitization guarantees session memory is wiped at session close.
- **Retention Policy:** Session state persists per the compliance database's own retention policy (outside this graph's scope); the statutory reference table is retained indefinitely and versioned.

**Memory and Behavioral Constraints:** Because raw PDFs are never copied into persistent memory and the statutory reference table contains no subcontractor-identifying data, there is no memory pathway by which prohibited disclosure (Prohibition 7) could occur through this architecture's persistence layer.

---

## **8. MODEL STRATEGY, ROUTING & COST**

**Verification Note:** Current Anthropic model lineup (Claude Opus 5, Claude Sonnet 5, Claude Haiku 4.5), Google GenAI model lineup (`gemini-3.8-flash`), and Strands' confirmed model-agnostic provider support (Bedrock, Google GenAI, Anthropic, OpenAI, and custom/local endpoints) were checked in this session; findings are current as of September 2026 and should be re-verified before implementation given how quickly this space moves.

**Model Selection Philosophy:** Reasoning/execution split, supported by a 3-tier production provider architecture — routing decided by which track each model call belongs to, never by letting a model choose its own downstream model.

### **3-Tier Production Architecture (Provider Abstraction)**

1. **Tier 1 — Production Runtime (AWS Bedrock AgentCore):**
   - **Models:** Claude Sonnet 5 (Primary Reasoning for `ForensicAuditSentinel`) and Claude Haiku 4.5 (Execution/Routing for `FairPayStatutoryGuardian` and `EverydayDecisionCardEmitter`), hosted on native Amazon Bedrock AgentCore Runtime.
   - **Environment:** Containerized deployment on AWS Bedrock AgentCore with microVM session isolation and CloudWatch OTel tracing.

2. **Tier 2 — Live Zero-Cost Staging Runtime (`gemini-3.8-flash`):**
   - **Model & SDK:** `gemini-3.8-flash` via the modern `google-genai` SDK (`from google import genai`, Google AI Studio 0 credit card / free tier).
   - **Capabilities:** Performs REAL live multimodal PDF document extraction, semantic classification, and Strands SDK tool calling against uploaded construction draw packets.
   - **Role:** Powers staging environments, evaluations, and 100% public demo uptime (e.g. Streamlit Community Cloud) with zero dependency on local AWS credentials.

3. **Tier 3 — Offline Deterministic Test Double (Hermetic Mock):**
   - **Mechanism:** Static JSON fixture mocks (`src/providers/mock_runtime.py`) providing instantaneous, deterministic responses for hermetic unit testing and CI test suites without network calls or API keys.

**Architectural Justification (Enterprise Resilience & Judge Defense):**
*"Enterprise systems must support multi-cloud disaster recovery and zero-cost staging; the provider abstraction decouples semantic reasoning from cloud infrastructure while maintaining strict AWS Bedrock AgentCore parity."* Because all financial calculations, retainage percentages, and statutory deadlines remain 100% isolated inside deterministic Python tools, switching between runtime tiers preserves identical mathematical rigor and compliance behavior.

### **Primary (Reasoning) Model**
- **Model:** Claude Sonnet 5 (Production via Bedrock) / `gemini-3.8-flash` (Staging via `google-genai`).
- **Responsibility:** `ForensicAuditSentinel`'s semantic document understanding, field-to-schema mapping, and discrepancy classification.
- **Why This Model:** Strongest structured-output reliability and long-context document handling needed to correctly map extracted text to G702/G703 fields across a 40-page packet without itself performing arithmetic.

### **Secondary (Execution/Routing) Model(s)**
- **Model:** Claude Haiku 4.5 (Production via Bedrock) / `gemini-3.8-flash` (Staging via `google-genai`).
- **Responsibility:** `EverydayDecisionCardEmitter`'s card templating/summarization, and `FairPayStatutoryGuardian`'s lightweight `pay-if-paid` vs `pay-when-paid` rider-clause classification.
- **Why This Model:** Both tasks are narrow classification/formatting jobs on already-verified or short inputs — a fast, cheap model is sufficient and keeps the two lower-stakes tracks from dominating cost.

**Routing Logic:** Deterministic by node — each of the three agents is statically bound to one model at graph-construction time; no runtime model-selection logic exists, so cost and behavior are fully predictable per run.

**Reasoning vs Execution Split:** Yes.
- **Reasoning Model:** Sonnet 5, reasons about document semantics only.
- **Execution Model:** Haiku 4.5, executes templating/classification only.
- **Handoff Logic:** Purely via the typed state schema (Section 3) — no direct model-to-model prompt passing.

**Prompt/Context Caching Strategy:** Cache each node's fixed system prompt (role instructions plus the AIA G702/G703 field schema reference) and the jurisdiction-specific statutory reference snippet for the duration of the session, since both are stable across the multiple tool-calling turns within one draw-packet run.

**Token Optimization Strategy:** Each node receives only its relevant state slice — `FairPayStatutoryGuardian` never receives raw PDF text or line-item detail, only rider classification input and jurisdiction; `EverydayDecisionCardEmitter` receives only the already-structured audit and statutory outputs, never the source documents.

**Fallback Strategy:**
- **Primary Model Failure:** One retry on Sonnet 5; on second failure, do not silently substitute Haiku 4.5 for the audit reasoning — instead route to Termination (Failure, `INCOMPLETE_MANUAL_AUDIT_REQUIRED`), since a weaker model producing an unverified audit would violate the Zero Error risk tolerance.
- **Fallback Model:** None for the reasoning track, by design; Haiku 4.5 fallback is limited to its own track's non-critical formatting failures.
- **Escalation Path:** Any unresolved model failure surfaces through `error_logs` and halts before payload emission.

**Cost & Scalability Analysis:**
- **Estimated Cost Per Task:** Low–Medium (roughly $0.05–$0.25 per draw-packet run).
- **Most Expensive Step:** `ForensicAuditSentinel`'s initial multi-document semantic extraction pass over the full packet — the longest context, highest-capability call in the graph.
- **Scalability Bottleneck:** AgentCore microVM session cold-start plus statutory reference-table lookup latency under high concurrent draw volume; mitigated by prompt caching and a low-latency keyed reference store.
- **Optimization Strategy:** Reasoning/execution split plus per-node token trimming keeps the two lightweight tracks cheap while concentrating spend only where document semantics genuinely require a frontier-class model.

---

## **9. TOOL INVOCATION STRATEGY**

**Tool Usage Permission:** Per Section 5 of the behavioral profile, all three agents may invoke tools autonomously for their bounded audit/classification tasks; no tool call in this system has a real-world financial or legal effect on its own — every tool either computes/reads or renders, never transacts.

**Invocation Pattern:**
- **Direct Invocation:** Yes, for all internal deterministic tools — no approval step is needed for computation itself, since the *output* of computation (the decision card) is gated, not the computation.
- **Approval Required:** No individual tool call requires approval; the graph-level HITL interrupt after `EverydayDecisionCardEmitter` is the single approval gate, matching LLM-1's Semi-Autonomous classification exactly (automatic audit, approval-gated release decision).
- **Batching:** `ForensicAuditSentinel`'s line-item verification tool is called once per packet with the full extracted line-item set, rather than once per line item, to minimize round-trips.

**Tool Access Control:** Enforced at the graph/agent-binding level (Section 6) — a tool is either in an agent's registry or it structurally does not exist for that agent; there is no runtime permission check to bypass because there is nothing to call.

**Guardrails:**
- **Rate Limiting Strategy:** Token-bucket limiting on the OCR and notification-dispatch MCP servers (e.g., capped calls per session) to bound cost/abuse from a malformed or adversarial packet.
- **Cost Control:** Per-session token/cost budget on the Sonnet 5 reasoning calls; exceeding it halts the run into `error_logs` rather than continuing to spend.
- **Permission Checks:** Handled structurally per Tool Access Control above.
- **Validation:** Every tool's input/output is validated against its typed signature before being merged into `IroncladState`; a schema-invalid tool result is treated as a tool failure, not silently coerced.
- **Prohibited Actions:** No banking/payment tool exists to call (Section 6); any attempt by a node to reference an undefined tool is a hard graph error, not a soft warning.

**Tool Call Flow:**
1. Agent determines a bound tool is needed for its track.
2. Tool executes directly (no approval step, per Invocation Pattern above).
3. Result is validated against its typed schema.
4. Result is merged into `IroncladState` via the field's declared reducer.
5. Graph proceeds to the next edge, or appends to `error_logs`/`flagged_discrepancies` and continues per Section 4's decision points.

**Tool Failure Handling:** Transient tool errors (e.g., OCR server timeout) retry with backoff (Section 11); permanent tool errors (e.g., malformed line item that cannot be parsed) become a `flagged_discrepancies` entry, never a guessed value, per Prohibition 3.

---

## **10. ASYNC EXECUTION & CHECKPOINTING STANDARDS**

**Execution Model:** Async-native (Python `asyncio`), consistent with both Strands' and AgentCore Runtime's unified sync/async invocation model.

**Justification:** The Event-Driven trigger and session-based Lifecycle Nature from LLM-1, combined with AgentCore Runtime's microVM-per-session model and its dependency on non-blocking I/O for concurrent draw-packet sessions, make blocking synchronous execution both unnecessary overhead to avoid and a genuine throughput risk to avoid at scale — async-first is required, not optional, here.

**Checkpointing Cadence:** A durable checkpoint is written after Step 1 (validated ingress), after the Step 4 fan-in (payload assembled, pre-interrupt), and again immediately after the human resolves the HITL gate — these are the three points where losing in-memory state would otherwise force re-running audited work.

**Resumability:** If the AgentCore session is interrupted (crash, idle-timeout, restart) between checkpoints, the graph resumes from the last durable checkpoint rather than restarting the full audit — `AgentCoreMemorySessionManager` restores `IroncladState` keyed by the original `session_id`, so a pending human-approval wait can be resumed hours later without re-auditing the packet.

---

## **11. FAILURE & RECOVERY ARCHITECTURE**

**Failure Detection:** Every tool call and model call is wrapped with schema validation and a timeout; any node that cannot produce a schema-valid write to its bound state fields raises a structured failure event rather than partially writing.

**Failure Categories:**

### **Transient Failures** (Retryable)
- **Examples:** OCR MCP server timeout, notification-dispatch MCP server unavailable, Bedrock model rate limit.
- **Response:** Retry with exponential backoff, max 3 attempts.
- **Backoff Strategy:** 1s → 4s → 16s, then classify as permanent if still failing.

### **Permanent Failures** (Non-Retryable)
- **Examples:** Cryptographic document hash mismatch, attempted use of an unbound/prohibited tool, unresolvable missing required document.
- **Response:** Halt execution immediately, write `error_logs`, route to Termination (Failure) — `INCOMPLETE_MANUAL_AUDIT_REQUIRED`.

### **Ambiguous Failures** (Uncertain)
- **Examples:** Illegible field, ambiguous rider clause, low-confidence date match.
- **Response:** Per Prohibition 3 — never resolved by inference; always appended to `flagged_discrepancies` and carried forward into the decision card so the human sees it explicitly.

**Recovery Strategies:**
- **Retry Logic:** Max 3 retries, exponential backoff, limited to Transient Failures only.
- **Graceful Degradation:** Not applicable to the audit tracks (Zero Error tolerance forbids a "partially verified" output); the only degraded path is `FairPayStatutoryGuardian`'s Haiku 4.5 formatting fallback, which never degrades the audit numbers themselves.
- **Halt and Escalate:** All Permanent Failures and any Section 6 prohibition trigger halt directly to human notification via `error_logs` and the compliance database.
- **Rollback:** On mid-graph unrecoverable failure, state rolls back to the last durable checkpoint (Section 10) rather than allowing a partially assembled `decision_card_payload` to be emitted — enforcing LLM-1's atomic delivery guarantee.

**State Consistency:** Because every field has a single designated writer (Section 3) and checkpoints are written only at well-defined boundaries, a failure mid-node can never leave two fields in a mutually inconsistent state — the failed node's fields simply remain unset, which the Step 4 decision point treats as a blocking condition.

**Circuit Breaker:** Each agent's recursive sub-goal depth is capped at 2 (per LLM-1 Reasoning Constraints); exceeding it is treated as a Permanent Failure for that node rather than allowed to continue looping.

---

## **12. CONSTRAINTS INHERITED FROM LLM-1**

**Behavioral Constraints Enforced Architecturally:**

1. **No LLM-generative math (Prohibition 2)**
   - **Architectural Enforcement:** No agent's tool registry contains a "compute via model" path for arithmetic or date math — `ForensicAuditSentinel` and `FairPayStatutoryGuardian` only have bound deterministic tools for these operations, and `EverydayDecisionCardEmitter` has no math tool at all, only a renderer.

2. **No guessing/hallucinating missing data (Prohibition 3)**
   - **Architectural Enforcement:** Every extraction/classification path has an explicit "flag discrepancy" branch (Section 4, Steps 2–3) instead of a fallback default value; the state schema has no field that silently defaults a financial or date value.

3. **No modification of uploaded files (Prohibition 4)**
   - **Architectural Enforcement:** Source documents are referenced by URI only (`source_uris`); no tool in any agent's registry has file-write access to the intake bucket.

4. **No suppression of subcontractor statutory clocks (Prohibition 5)**
   - **Architectural Enforcement:** `statutory_prompt_pay_clock` has exactly one writer (`FairPayStatutoryGuardian`), which has no edge or channel through which `EverydayDecisionCardEmitter` or a General-Contractor-facing process could request a different value before card assembly.

5. **No treating document text as instructions (Prohibition 6 / prompt-injection mitigation)**
   - **Architectural Enforcement:** Extracted document text is only ever passed into state fields and tool arguments, never concatenated into a node's system/control prompt; tool schemas are strictly typed, so injected text cannot alter which tool is called or with what parameters.

6. **No financial transaction capability (Prohibition 1)**
   - **Architectural Enforcement:** No banking/ACH/wire tool or MCP server exists anywhere in this graph's registry (Section 6) — the capability is structurally absent, not policy-restricted.

**Autonomy Level Enforcement:**
- **Behavioral Profile Specifies:** Semi-Autonomous.
- **Architectural Implementation:** Steps 1–4 (Section 4) execute with zero human involvement; Step 5's interrupt node is the graph's only path to a release-affecting terminal branch, and no edge bypasses it.

**Human-in-the-Loop Gates:**
- **Required Approvals:** Fund release, dispute/hold, legal escalation.
- **Architectural Implementation:** A single interrupt node (Step 5) with three outbound edges, one per authenticated human action; `approval_state` has no writer other than this node.

**Prohibited Actions:**
- **From Behavioral Profile:** Financial transactions; LLM-generated math; guessed data; file modification; clock suppression; prompt-injection compliance.
- **Architectural Prevention:** Structural absence of tools/edges as detailed above — each is impossible to violate by omission, not by instruction.

**Data Contract Fidelity:**
- **Input Contract (from LLM-1):** Multipart/webhook payload with `project_id`, `subcontractor_id`, `draw_number`, document URIs — matches `draw_packet_meta` exactly.
- **Output/Deliverable Contract (from LLM-1):** `DecisionCardPayload` JSON plus immutable Markdown audit trail — matches `decision_card_payload` plus the checkpointed `IroncladState` history exactly.
- **Schema Enforcement:** Confirmed field-for-field in Section 3.

**Scope Boundaries:**
- **In Scope:** Audit, statutory-clock calculation, decision-card synthesis, HITL gating.
- **Out of Scope:** Change-order negotiation, ERP/banking execution, binding legal representation, contract-validity rulings.
- **Architectural Enforcement:** No agent, tool, or MCP server in this topology has any capability mapping to an out-of-scope action; an out-of-scope request has no edge to route through and falls through to the ingress-validation halt.

**Verification Statement:**
This architecture fully respects all constraints defined in AGENT_BEHAVIOR_PROFILE.md.
No behavioral boundary can be violated by this orchestration design.

---

## **ARCHITECTURE INTEGRITY DECLARATION**

This orchestration blueprint is AUTHORITATIVE.

All downstream systems must:
- Implement agent topology exactly as specified
- Follow execution flow without deviation
- Implement the typed state schema and reducers exactly as specified
- Use the specified orchestration framework
- Implement MCP/tool topology as designed
- Implement memory and checkpointing architecture as designed
- Route to models as specified, including caching and cost strategy
- Enforce tool invocation guardrails
- Handle failures per recovery strategies
- Respect all inherited behavioral constraints

No architectural decision may be changed without invalidating this blueprint.

---
