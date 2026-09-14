# INTERFACE & OBSERVABILITY SYSTEM

**Generated:** September 13, 2026
**Source:** AGENT_LOGIC_SPEC.md
**Status:** AUTHORITATIVE — Defines complete human-agent interaction and telemetry layer
**Purpose:** Interface design, streaming protocol, and observability specification

> **Adaptation note (read once):** The Step-4 override strictly prohibits chat bubbles and mandates a single Executive Decision Card as the primary surface. The base template below assumes a chat-streaming interaction model; every section has been adapted to the zero-chat reality while preserving the same underlying typed-event and trace-fidelity guarantees. Where a section heading below says "Message," read it as "Card Section" — no conversational input/output exists anywhere in this system.

---

## **1. INTERACTION PHILOSOPHY**

**Overall Interaction Model:** Task-First — strictly, zero-chat Task-First. One task = one draw-packet audit run, surfaced as exactly one Executive Decision Card per session. There is no conversational input surface anywhere in this interface.

**Description:** A human never types to this agent. A draw packet arrives, the Strands graph runs unattended through `ForensicAuditSentinel` and `FairPayStatutoryGuardian` in parallel, and the interface's only job is to render the resulting card the instant `EverydayDecisionCardEmitter` completes and let the human resolve it with exactly one tap.

**Human vs Agent Initiative:**
- **User-Driven:** Never in this system — no user-initiated tool call or free-form request exists (per AGENT_LOGIC_SPEC.md Section 11, there is no chat input to drive anything).
- **Agent-Driven:** Steps 1–4 of the execution flow (ingestion through card assembly) run entirely agent-driven, with zero human involvement, per the Semi-Autonomous autonomy level.
- **Collaborative:** The single HITL checkpoint (Section 5 below) is the one moment of human initiative — and it is the only moment.

**This Agent's Initiative Model:** Fully agent-driven until the card exists, then fully human-driven for exactly one decision, then agent-driven again for notification dispatch. There is no back-and-forth.

**Transparency vs Simplicity Balance:**

**Transparency Priority:** Every number on the card must be traceable to a specific tool output (per AGENT_LOGIC_SPEC.md Section 8's Citation Enforcement); every discrepancy must be visible before a decision is made; the statutory clock must never be softened.

**Simplicity Priority:** The three-node graph trace, tool-call detail, and native model reasoning are never on the primary card — they exist in a single collapsed "Show Audit Trail" panel the reviewer opts into.

**Balance Strategy:** The Decision Card is the fast path (one glance, one tap); the Audit Trail panel is the slow path (full forensic detail) — both render from the exact same typed state, so "simple" never means "different data," only "less of it visible at once."

**Interaction Principles:**
1. The card never hides a discrepancy or a non-`VALID` lien status to look cleaner — `recommended_action` is a fixed rule, not a UI judgment (AGENT_LOGIC_SPEC.md Section 1, `EverydayDecisionCardEmitter`'s constraints).
2. The human's three buttons are the only write path back into the graph — there is no other control surface.
3. A missing or unreadable field is shown as missing, never silently omitted from the card.

---

## **2. PRIMARY USER INTERFACE**

**Core Interaction Surface:** A single-page Executive Decision Card — not a chat window, not a dashboard with multiple panels of equal weight. One card is the entire primary surface per session.

**Layout Structure:** A slim header (project/subcontractor/draw number), the Executive Decision Card as the dominant central element, a collapsed "Show Audit Trail" expander directly beneath the card, and the three action buttons docked at the card's bottom edge, disabled until the card is populated.

**Card Sections (replacing "Message Types" — see Adaptation Note):**

### **Audit Status Badge**
- **Format:** A single colored badge, driven directly by `lien_chain_status` — green "PASSED" for `VALID`; amber "FLAGGED — Missing Waiver" for `MISSING_WAIVER`; red "FLAGGED — Pre-Dated Notary" for `SUSPECT_PRE_DATED_NOTARY`; red "FLAGGED — Invalid Form" for `INVALID_FORM`.
- **Display:** Top-left of the card, largest visual element after the dollar figures.

### **Financial Summary (Gross vs. Net)**
- **Format:** Three side-by-side metric tiles: Gross Amount Requested, Contractual Retainage Withheld, Net Recommended Release — copied verbatim from `decision_card_payload`, never recomputed client-side.
- **Display:** Center of the card, directly under the badge.

### **Flagged Discrepancy Breakdown Table**
- **Format:** A table with columns Line Item, Discrepancy Type, Description, Variance Amount, sourced verbatim from `decision_card_payload.flagged_discrepancies`.
- **Display:** Below the financial summary; hidden entirely (collapsed to "No discrepancies flagged") only when the list is empty — never fabricated as absent when it isn't.

### **Statutory Prompt-Pay Countdown Timer**
- **Format:** A live countdown reading days/hours remaining until `deadline_timestamp`, with the `penalty_interest_rate` shown beneath it; turns red and adds a "Critical" tag once `days_remaining` ≤ 2 (48 hours), matching AGENT_BEHAVIOR_PROFILE.md Section 8's critical threshold.
- **Display:** Right side of the card, always visible, never collapsible — this is a statutory obligation, not decoration.

### **System/Status Banner**
- **Purpose:** The only non-card text on the page — a single-line status string ("Auditing packet…", "Audit complete — awaiting your decision", "On hold — correction requested", "Escalated to legal") reflecting the current graph state.
- **Display:** Directly above the card, styled distinctly (gray/neutral) from the badge so it's never mistaken for an audit finding.

### **Audit Trail Panel (Tool/Graph Output)**
- **Purpose:** Full forensic detail — every tool call, every node's reasoning summary — for the reviewer who wants to verify before clicking.
- **Display:** A single collapsed expander beneath the card; expanding it reveals one sub-expander per graph node (Section 4a defines the per-tool rendering inside it).
- **Interactivity:** Expandable per node; a "Download full audit trail (JSON)" link at the bottom, sourced from the checkpointed `IroncladState`.

**Technical Implementation Specs:**

**Frontend Tech Recommendation:** **Streamlit**, chosen and verified in Phase 1.5 specifically because it deploys with zero extra configuration to **Streamlit Community Cloud** — the exact free-hosting target for the public Devpost Live Demo Link. When deployed to Streamlit Community Cloud, the app defaults to the **Live Zero-Cost Staging Runtime** (`IRONCLAD_RUNTIME_MODE=staging`, powered by `GEMINI_API_KEY` and the official `google-genai` SDK), ensuring 100% public demo uptime with real AI multimodal document extraction and zero dependency on local AWS credentials. The production `bedrock` mode remains toggleable via environment variables (`IRONCLAD_RUNTIME_MODE=bedrock`) for AWS AgentCore runtime environments. Streamlit's `st.status` and `st.session_state` primitives map directly onto this system's "one card, one decision" interaction model.

**Component Library:** Streamlit's built-in widget set (`st.metric`, `st.dataframe`, `st.status`, `st.button`, `st.expander`) — no additional component library is needed for a single-card layout, keeping the zero-cost/zero-dependency footprint the hackathon constraint requires.

**Reason:** A generic chat-streaming frontend SDK (Vercel AI SDK, Assistant-UI, CopilotKit) is the wrong tool here — this system has no chat surface to drive, and none of those libraries improve a single structured-card render.

**Connection Protocol — Verified, Two-Hop Reality & Multi-Runtime Architecture:**
- **Production Mode (`IRONCLAD_RUNTIME_MODE=bedrock`):**
  - **Hop 1 (AgentCore Runtime → Streamlit server process):** Real Server-Sent Events over HTTP. Amazon Bedrock AgentCore Runtime's `InvokeAgentRuntime` API returns a streaming HTTP response; the Strands agent process running in the AgentCore container streams its own tool-call/state events back through this channel. The Streamlit server-side Python process consumes this stream directly via the AWS SDK's streaming response iterator.
  - **Hop 2 (Streamlit server → browser):** Streamlit's own internal WebSocket-based protocol — server-side code re-renders Streamlit widgets each time it consumes a new event from Hop 1, and Streamlit pushes the resulting DOM diff to the browser.
- **Staging Mode (`IRONCLAD_RUNTIME_MODE=staging` — Public Demo Default):**
  - Streamlit server directly invokes the in-process `staging_runtime.py` engine running `gemini-3.8-flash` via `google-genai`, streaming step-by-step Strands graph events directly to `st.session_state` with 100% public uptime and zero AWS IAM credential requirements.
- **Mock Mode (`IRONCLAD_RUNTIME_MODE=mock` — Hermetic Testing):**
  - Local in-process streaming from deterministic JSON fixtures for testing.
- **Verification Note:** Confirmed current via live search that (a) Strands + AgentCore Runtime supports streaming agent responses, and (b) Streamlit provides no native SSE endpoint of its own — `st.write_stream` consumes a Python generator server-side, it does not expose browser-facing SSE. This multi-runtime architecture maintains identical UI/card presentation across all three tiers.
- **Alternative (if true browser-native SSE is later required):** **FastHTML**, built on Starlette + htmx, was verified in this session to support genuine server-push SSE via the `hx-ext="sse"` / `sse-connect` / `sse-swap` htmx extension — a direct single-hop match for Section 2a's event vocabulary. It would deploy to HuggingFace Spaces via the Docker SDK rather than the Streamlit-Community-Cloud path this specification defaults to.

**Accessibility (A11y) Standards:**
- **Live Regions:** Streamlit's `st.status` container has its own built-in ARIA live-region behavior for "running/complete/error" states; the countdown timer's text is re-announced only on state change (PASSED → FLAGGED, or entering Critical), not on every second's tick, to avoid screen-reader spam.
- **Keyboard Nav:** The three action buttons are native Streamlit `st.button` elements — natively focusable/tab-navigable; no custom keyboard handling is introduced.
- **Screen Readers:** The status banner (not the badge) is the element wired to announce "Audit complete" once, rather than the badge re-announcing on every rerun.

**Responsive Strategy:**
- **Mobile View:** The three financial metric tiles stack vertically; the Flagged Discrepancy table becomes a scrollable accordion (one row expands to show its full description) rather than a wide table, using Streamlit's column-collapse behavior at narrow viewports.
- **Desktop View:** Metric tiles and countdown timer sit side-by-side in a wide column layout; the Audit Trail expander sits below at full width.

**Streaming Behavior:**

**Streaming Granularity:** Step-by-step / action-by-action — this system has no free-text generation to stream token-by-token (per AGENT_LOGIC_SPEC.md, every agent output is either a tool call or a structured-output write, never prose).

**Streaming Strategy:**
- **Status Banner Text:** Updates in discrete steps (not token deltas) as each graph node completes — "Auditing packet…" → "Verifying lien chain…" → "Calculating statutory clock…" → "Audit complete."
- **Native Thinking / Graph Trace:** Streams live into the Audit Trail panel's per-node sub-expanders (Section 3), but only if the reviewer has already expanded the panel — collapsed panels buffer and render on expansion rather than streaming into a hidden component.
- **Tool Execution:** Each tool call updates its own `st.status` line inside the relevant node's sub-expander in real time as Hop 1 events arrive.

**Real-Time Updates:**
- **Status Indicators:** A single spinner tied to the status banner while any node is still running; disappears the instant `decision_card_payload` is written.
- **Progress Bars:** Not used — the graph has only 3 nodes and typically completes in seconds to low tens of seconds (per AGENT_ORCHESTRATION_BLUEPRINT.md Section 8's cost/latency analysis); a spinner plus status text is sufficient and avoids implying false precision.
- **Cancellation:** The reviewer may close the browser tab at any time without corrupting state — the AgentCore session checkpoint (AGENT_ORCHESTRATION_BLUEPRINT.md Section 10) survives independently of the Streamlit connection; reopening the same session URL resumes showing the correct state.

**Message Threading:** Not applicable — there is exactly one card per session, never a thread of multiple exchanges.

---

## **2a. TYPED STREAMING EVENT DATA CONTRACT**

**Protocol Verification Note:** The event *vocabulary* below matches the same nine event types verified as current practice for agent UIs (mirroring Vercel AI SDK's part-type taxonomy at a conceptual level); the *transport* is the two-hop Streamlit reality described in Section 2, not raw browser SSE — see that section's Verification Note before assuming this JSON is literally what the browser receives. This is Hop 1's wire format (AgentCore Runtime → Streamlit server).

**Transport:** SSE-over-HTTP (Hop 1 only, per Section 2); no equivalent typed contract is exposed to the browser (Hop 2 is Streamlit's opaque internal protocol).

**Event Type Vocabulary:**

```
data: {"type": "text-delta", "content": "..."}
data: {"type": "reasoning-delta", "content": "...", "source": "native-thinking | graph-trace", "node": "ForensicAuditSentinel | FairPayStatutoryGuardian | EverydayDecisionCardEmitter"}
data: {"type": "tool-call-start", "tool_call_id": "...", "tool_name": "...", "node": "...", "input_preview": {...}}
data: {"type": "tool-call-delta", "tool_call_id": "...", "partial_output": {...}}
data: {"type": "tool-call-result", "tool_call_id": "...", "success": true, "result": {...}}
data: {"type": "state-update", "field": "...", "reducer": "append-only | merge-by-key | last-write-wins", "value": {...}}
data: {"type": "approval-required", "checkpoint_id": "...", "action_preview": {...}, "graph_node": "EverydayDecisionCardEmitter"}
data: {"type": "error", "code": "...", "message": "...", "recoverable": true}
data: {"type": "stream-end", "reason": "success | interrupted | error"}
```

**Per-Event Field Definitions:**

### **text-delta**
- **When Emitted:** Only for the status-banner string updates (Section 2) — this system has no chat text stream; treat any `text-delta` as a banner-string replacement, not an append.
- **Fields:** `content` — the full new banner string (not a token fragment, despite the shared vocabulary name).
- **UI Handling:** Streamlit replaces the status banner's text in place.

### **reasoning-delta**
- **When Emitted:** `source: "native-thinking"` — whenever `ForensicAuditSentinel`'s Sonnet 5 call streams extended-thinking content (Section 3a). `source: "graph-trace"` — whenever any node completes an internal reasoning cycle step from AGENT_LOGIC_SPEC.md Section 2.
- **Fields:** `content` (text chunk), `source`, `node` (which of the three agents emitted it).
- **UI Handling:** Appended into that node's sub-expander in the Audit Trail panel only; never surfaced on the primary card.

### **tool-call-start**
- **When Emitted:** The instant any of the six tools in AGENT_LOGIC_SPEC.md Section 3 is invoked.
- **Fields:** `tool_call_id`, `tool_name`, `node`, `input_preview` (sanitized — never raw PDF bytes, per AGENT_LOGIC_SPEC.md Section 8).
- **UI Handling:** Adds a new "running" `st.status` line under the emitting node's sub-expander.

### **tool-call-delta**
- **When Emitted:** Only by `extract_draw_packet_metadata` if the OCR MCP server streams partial field extraction; the four purely internal deterministic tools complete atomically and never emit this event.
- **Fields:** `tool_call_id`, `partial_output`.
- **UI Handling:** Updates the same status line's detail text without closing it.

### **tool-call-result**
- **When Emitted:** On completion of any tool call, success or failure.
- **Fields:** `tool_call_id`, `success`, `result` (matches the tool's Pydantic Output model from AGENT_LOGIC_SPEC.md Section 4).
- **UI Handling:** Closes the status line as complete (✓) or failed (✗) and renders the tool's generative-UI mapping (Section 4a) inside that node's sub-expander.

### **state-update**
- **When Emitted:** Every time a tool/structured-output write is merged into `IroncladState`, per AGENT_ORCHESTRATION_BLUEPRINT.md Section 3's reducers.
- **Fields:** `field`, `reducer` (restated verbatim from LLM-2's schema — never invented here), `value`.
- **UI Handling:** Drives the Financial Summary tiles, Audit Status Badge, and countdown timer to update the instant their backing field is written — these are the only `state-update` events that touch the primary card; all others only update the Audit Trail panel.

### **approval-required**
- **When Emitted:** Exactly once per run, the instant `decision_card_payload` is written and the graph reaches the Section 5 checkpoint.
- **Fields:** `checkpoint_id`, `action_preview` (the full `DecisionCardPayload`), `graph_node: "EverydayDecisionCardEmitter"`.
- **UI Handling:** Enables the three action buttons and freezes the status banner to "Audit complete — awaiting your decision."

### **error**
- **When Emitted:** Any Permanent Failure per AGENT_LOGIC_SPEC.md Section 9.
- **Fields:** `code`, `message`, `recoverable`.
- **UI Handling:** Status banner switches to an error state (Section 9 below); if `recoverable` is false, the three buttons remain disabled and a "Manual Audit Required" notice replaces the card.

### **stream-end**
- **When Emitted:** Either after `approval-required` fires (a normal pause, not a true end) or after a Permanent Failure halts the run.
- **Fields:** `reason`.
- **UI Handling:** Stops the spinner; for `reason: "interrupted"` (the normal HITL pause), the card remains fully interactive — this is not a dead-end state.

**Ordering & Backpressure Guarantees:** Events for a given `tool_call_id` always arrive in `tool-call-start` → (optional `tool-call-delta`)* → `tool-call-result` order; `state-update` events for a field always arrive after the tool/structured-output call that produced them. If the Streamlit browser tab disconnects mid-stream (Hop 2 drops), Hop 1's AgentCore session checkpoint is unaffected — reloading the page re-fetches the current `IroncladState` snapshot directly rather than replaying the event stream, so no event is "missed" in a way that corrupts the displayed card.

---

## **3. REASONING VISIBILITY MODEL**

**Visibility Philosophy:** Full forensic transparency is available, but nothing about reasoning ever competes with the Decision Card for the reviewer's attention — it all lives one click away in the Audit Trail panel.

### **3a. Native Model Thinking Tokens**

**Applicability:** Yes for `ForensicAuditSentinel` (Claude Sonnet 5, the document-semantics reasoning track per AGENT_ORCHESTRATION_BLUEPRINT.md Section 8) — extended thinking may be enabled for this node's document-mapping calls. Not applicable to `FairPayStatutoryGuardian` or `EverydayDecisionCardEmitter` (Claude Haiku 4.5, narrow classification/templating tasks where extended thinking adds latency without proportionate value).

**UI Treatment:**
- **Component:** A collapsible "Model reasoning" sub-section inside `ForensicAuditSentinel`'s Audit Trail sub-expander — visually distinct (italic, muted color) from tool-call status lines.
- **Default State:** Collapsed — even within an already-expanded Audit Trail panel, native thinking requires a second, explicit expand.
- **Streaming Behavior:** `reasoning-delta` events with `source: "native-thinking"` append live into this sub-section only while it is expanded; otherwise buffered silently.
- **Safety Note:** Per Section 3c, any thinking content that would reveal extracted-document text verbatim (rather than the agent's classification reasoning about it) is filtered before display.

### **3b. Graph Node / Multi-Step Agent Traces**

**Applicability:** Yes — the three-node fan-out/fan-in graph (AGENT_ORCHESTRATION_BLUEPRINT.md Section 2) is exactly the kind of multi-step transition worth surfacing for a reviewer who wants to verify the audit before approving release.

**UI Treatment:**
- **Component:** Three ordered sub-expanders inside the Audit Trail panel — `ForensicAuditSentinel`, `FairPayStatutoryGuardian` (rendered side-by-side or stacked to reflect their parallel execution), then `EverydayDecisionCardEmitter` beneath both once they complete.
- **What's Shown Per Step:** Node name, each tool call it made (Section 4), and which `IroncladState` fields it wrote.
- **Streaming Behavior:** Populated live by `reasoning-delta` (`source: "graph-trace"`), `tool-call-*`, and `state-update` events scoped to that node.
- **Clutter Prevention:** The entire Audit Trail panel is one single collapsed expander by default at the page level — none of this appears until the reviewer opts in, keeping the primary card the only thing visible on load.

**Visible Reasoning Components:**

### **Node Internal Thought (from AGENT_LOGIC_SPEC.md Section 2's bounded ReAct cycle)**
- **What's Shown:** One-line summary of what the node decided to do next (e.g., "Extracted 4 line items, mapping to typed records").
- **When Shown:** Inline within that node's sub-expander, in the order the actions occurred.
- **Format:** Plain text, timestamped.
- **User Control:** Always visible once the parent node sub-expander is opened — no further nesting needed for this level.

### **Tool/Structured-Output Selection**
- **What's Shown:** Which tool or structured output was invoked and why (drawn from the node's `<primary_objective>` reasoning, e.g., "All four numeric fields present — calling audit_retainage_math").
- **When Shown:** Immediately preceding that tool's status line.
- **Format:** Small caption text above the status line.
- **User Control:** Not separately hideable — it's part of the same status-line unit.

**Summarization Strategy:**

**When to Summarize:** Always, on the primary card — the card never shows anything but the final `DecisionCardPayload` fields.

**How to Summarize:** The card shows the conclusion (badge, figures, discrepancies, countdown); the Audit Trail shows every step that produced it.

**When to Show Full Detail:** Only inside the opted-in Audit Trail panel, and only for `ForensicAuditSentinel`'s native thinking after a second, separate expand (Section 3a).

**Progressive Disclosure:**

**Default View:** The card alone — status banner, badge, figures, discrepancy table, countdown, three buttons.

**Expandable View:** Audit Trail panel (graph traces, tool calls, structured-output judgments) → further expandable native-thinking sub-section.

**Hidden Entirely:** Raw extracted PDF text is never rendered anywhere in the UI, even in debug/expanded views — only the typed, normalized field values are shown, consistent with the source documents remaining read-only references (AGENT_LOGIC_SPEC.md Section 1).

### **3c. Safety Filters for Sensitive Reasoning**

**Content That Must Be Filtered:**
- Any native-thinking content that quotes extracted document text verbatim at length, rather than reasoning about its classification — this reduces the risk of a prompt-injection payload embedded in a PDF being faithfully reproduced and re-rendered to the reviewer as if it were agent commentary.
- Any internal tool-call retry/backoff detail beyond the final success/failure state — operationally irrelevant to the reviewer and clutters the trail.

**Filtering Strategy:** Verbatim document-text spans longer than a short excerpt are replaced with `[document text — see field value above]`, pointing back to the already-normalized, safely-rendered typed field instead.

**Transparency About Filtering:** The Audit Trail panel's footer always states "Some raw extracted text is summarized here; see the structured fields above for exact values" — the reviewer is told filtering happened, never left to assume they're seeing everything.

---

## **4. TOOL & ACTION OBSERVABILITY**

### **Document Extraction (`extract_draw_packet_metadata`)**

**Before Execution:**
- **Announcement:** Status line "Reading draw packet document…" under `ForensicAuditSentinel`'s sub-expander.
- **Streaming Event:** `tool-call-start`.
- **Parameters Shown:** The source filename only (not the full URI, to avoid exposing internal bucket paths).
- **User Approval:** None required — automatic, per Semi-Autonomous autonomy.

**During Execution:**
- **Status Indicator:** `st.status` spinner with label "Extracting fields…".
- **Streaming Event:** `tool-call-delta`, if the OCR service streams partial fields.
- **Estimated Duration:** Not shown numerically — OCR duration varies too much by document quality to promise a number.
- **Cancellation:** Not offered mid-tool-call (Section 2's tab-close/reload behavior is the only "cancel" available, and it doesn't abort the backend run).

**After Execution:**
- **Streaming Event:** `tool-call-result`.
- **Success Display:** Collapses to a single "✓ Extracted N line items, M waivers" line; full field list available via Section 4a's generative UI mapping.
- **Failure Display:** "✗ Could not read this document" with the specific low-confidence/unreadable fields listed, tied directly to the resulting `flagged_discrepancies` entries.
- **Retry Option:** Automatic (Transient) per AGENT_LOGIC_SPEC.md Section 9 — no user action; a Permanent extraction failure instead routes the whole run to `INCOMPLETE_MANUAL_AUDIT_REQUIRED` and the card never renders.

### **Retainage Math, Lien Chain, Statutory Clock (the three deterministic tools)**

**Before/During Execution:** These complete in well under a second (pure computation); no separate "in progress" state is shown — they appear directly as completed status lines with their result already attached, to avoid manufacturing a false sense of a multi-second calculation.

**After Execution:**
- **Success Display:** Each renders its generative-UI mapping (Section 4a) directly — the numbers, the waiver findings table, or the countdown — inline in its node's sub-expander, matching exactly what also appears (summarized) on the primary card.
- **Failure Display:** A red "✗ [Tool name] could not complete" line with the specific validation error, never a guessed substitute value.

### **Notification Dispatch (`dispatch_decision_notification`)**

**Before Execution:** Silent — this fires automatically right after `decision_card_payload` is written; no separate announcement clutters the moment the card becomes actionable.

**After Execution:**
- **Success Display:** A small, low-emphasis toast: "Notified General Contractor, Owner, and Subcontractor."
- **Failure Display:** A low-emphasis warning toast: "Notification could not be sent — the decision card itself is still accurate and awaiting your action" (per AGENT_LOGIC_SPEC.md Tool Inventory, dispatch failure never blocks the HITL gate).

**Input/Output Visibility Rules:**

**Always Show:** Final figures, discrepancies, lien status, statutory clock — everything that ends up in `decision_card_payload`.

**Show on Request:** Raw tool-call inputs/outputs, native thinking, per-waiver findings detail — inside the Audit Trail.

**Never Show:** Full source-document URIs, any internal `tool_call_id`/session/trace identifiers, raw extracted PDF text spans (Section 3c).

**Success vs Failure Representation:**

**Success Indicators:** Green checkmark, "✓" prefix, green-tinted status line.

**Failure Indicators:** Red "✗" prefix, red-tinted status line, paired with the exact `flagged_discrepancies`/`error_logs` text.

**Partial Success:** "Extracted 3 of 4 line items; 1 field flagged as unreadable" — never rounded up to "success."

**Latency & Waiting States:**

**Short Operations (<2s):** The four deterministic tools — no spinner, appear already-complete.

**Medium Operations (2–10s):** OCR extraction, statutory table lookup under load — `st.status` spinner with tool name.

**Long Operations (>10s):** Not expected in this system's normal path (AGENT_ORCHESTRATION_BLUEPRINT.md Section 8 estimates seconds-to-low-tens-of-seconds); if exceeded, the status banner adds "(taking longer than usual)" without a numeric ETA, since none is verifiable.

**Stuck/Timeout:** If the graph exceeds its per-node tool-call budget (AGENT_LOGIC_SPEC.md Section 2) without completing, the status banner switches to "Audit could not complete automatically — flagged for manual review," matching the Permanent Failure path.

**Heartbeat/Liveness Indicators:**
- **Mechanism:** The status banner's spinner itself is the heartbeat — Streamlit's `st.status(state="running")` animates continuously while Hop 1 is still open.
- **Purpose:** Reassures the reviewer the run hasn't silently died during OCR/extraction, the one step with genuinely variable latency.

---

## **4a. GENERATIVE UI & RICH TOOL OUTPUT RENDERING**

### **`extract_draw_packet_metadata` Output**

**Output Shape:** `line_items: list[LineItem]`, `waiver_records: list[LienWaiverRecord]`, `low_confidence_fields: list[str]`.

**Rendering Component:** JSON tree / expandable field list, inside the Audit Trail only.

**Why This Component:** Raw OCR output is inherently a nested, variable-shape record set — a table would force artificial uniformity; a collapsible tree preserves the actual document structure for a reviewer who wants to sanity-check the source read.

**Interactivity:** Each `low_confidence_fields` entry is highlighted in amber and links to its corresponding `flagged_discrepancies` row.

**Streaming Behavior:** Renders once, on `tool-call-result` — this tool does not stream partial structure in a way worth rendering incrementally.

**Fallback:** If the returned shape fails Pydantic validation (AGENT_LOGIC_SPEC.md Section 9), render "Extraction returned an unreadable structure — flagged for manual review" instead of a blank or broken tree.

---

### **`audit_retainage_math` Output**

**Output Shape:** `gross_amount_requested`, `contractual_retainage_withheld`, `net_recommended_release`, `calculation_trace: list[str]`.

**Rendering Component:** The three primary-card metric tiles (Section 2) directly, plus a plain ordered list of `calculation_trace` steps inside the Audit Trail for the reviewer who wants to see the arithmetic itself.

**Why This Component:** These three numbers are the single most decision-critical output in the entire system — they get the card's highest-prominence treatment, not a generic JSON dump.

**Interactivity:** None needed on the card (read-only figures); the `calculation_trace` list in the Audit Trail is plain, copyable text.

**Streaming Behavior:** Populates the card tiles the instant the `state-update` event for `retainage_audit_result` arrives — before the other track or the final card assembly completes, so the reviewer sees numbers appear progressively rather than all at once at the very end.

**Fallback:** If the internal consistency check (AGENT_LOGIC_SPEC.md Section 9) rejects the output, the tiles show "—" with a tooltip "Audit could not verify this figure" rather than a stale or zeroed value.

---

### **`verify_lien_chain_integrity` Output**

**Output Shape:** `lien_chain_status`, `findings: list[WaiverFinding]`.

**Rendering Component:** The Audit Status Badge (Section 2) directly from `lien_chain_status`, plus a small table of `findings` (waiver ID → OK/PRE_DATED_NOTARY/MISSING_NOTARY_DATE/TYPE_MISMATCH) inside the Audit Trail.

**Why This Component:** A single overall status deserves a single glanceable badge; the per-waiver findings are naturally tabular (fixed columns, variable rows) and benefit from a real table rather than prose.

**Interactivity:** Table rows are sortable by finding type so a reviewer auditing many waivers can group problems together.

**Streaming Behavior:** Badge updates the instant `lien_chain_status`'s `state-update` arrives; the findings table populates alongside it.

**Fallback:** If `lien_chain_status` is unexpectedly null (should be unreachable per AGENT_LOGIC_SPEC.md's tool contract), the badge renders a neutral gray "Status unavailable — manual review required" rather than defaulting to green.

---

### **`statutory_prompt_pay_clock` Output**

**Output Shape:** `days_remaining`, `deadline_timestamp`, `penalty_interest_rate`, `statute_reference`.

**Rendering Component:** The Countdown Timer component (Section 2), with `statute_reference` shown as small print beneath it.

**Why This Component:** A deadline is fundamentally a live-updating countdown, not a static number — a chart or table would understate its urgency.

**Interactivity:** Hovering/tapping the timer reveals the exact `deadline_timestamp` and `statute_reference` citation.

**Streaming Behavior:** Renders once from `tool-call-result` and then ticks down client-side between reruns using the fixed `deadline_timestamp` — it does not re-query the backend every second.

**Fallback:** If the jurisdiction lookup failed (Permanent Failure per AGENT_LOGIC_SPEC.md Section 3), the timer position shows "Statutory clock unavailable — jurisdiction not resolved" in red, which itself forces `recommended_action` away from `APPROVE_RELEASE`.

---

### **`DecisionCardPayload` (Structured Output — the terminal artifact)**

**Output Shape:** The full payload per AGENT_LOGIC_SPEC.md Section 5 — this is not one tool's output but the assembled whole.

**Rendering Component:** This structured output *is* the Executive Decision Card itself — every other component above is a piece of it.

**Why This Component:** No further transformation is applied; showing anything other than these exact fields would violate the "card must reflect verified state verbatim" constraint (AGENT_LOGIC_SPEC.md Section 1, `EverydayDecisionCardEmitter`'s prohibitions).

**Interactivity:** The three action buttons (Section 5).

**Streaming Behavior:** The card's individual tiles/badge/table/timer populate progressively as their underlying `state-update` events arrive (see each tool's entry above); the buttons themselves only activate on the `approval-required` event once the full payload is confirmed complete.

**Fallback:** If `approval-required` never fires because a blocking error halted the run first, no card renders at all — the status banner's error state (Section 9) replaces it entirely, never a partially-filled card.

---

### **`dispatch_decision_notification` Output**

**Output Shape:** `success`, `dispatched_to: list[str]`.

**Rendering Component:** A single-line toast (Section 4), not a card or table.

**Why This Component:** This is a confirmation, not a decision input — it doesn't warrant competing visually with the card.

**Interactivity:** None.

**Streaming Behavior:** Appears on `tool-call-result` for this tool, after the card is already live.

**Fallback:** Silent degradation to the warning toast described in Section 4 — never blocks or hides the card.

---

## **5. HUMAN-IN-THE-LOOP INTERACTIVE GRAPH RESUMPTION**

**Approval Gates:** Exactly one — the checkpoint immediately after `EverydayDecisionCardEmitter` writes `decision_card_payload` (AGENT_ORCHESTRATION_BLUEPRINT.md Section 4, Step 5; AGENT_LOGIC_SPEC.md Section 10).

### **Checkpoint: Decision Card Release Gate**

**Trigger:** `approval_state` is still null and `decision_card_payload` is non-null — the graph is durably paused at this exact node, per AGENT_ORCHESTRATION_BLUEPRINT.md Section 10's checkpointing cadence.

**Paused-State Rendering:**
- **Streaming Event:** `approval-required`.
- **UI Presentation:** The Executive Decision Card itself, now with its three buttons enabled — this is deliberately not a separate modal or popup, since the card *is* the approval surface per the Step-4 mandate's zero-chat design.
- **Information Shown:** The complete `DecisionCardPayload` — badge, figures, discrepancy table, countdown — is the entirety of "why approval is required" information; nothing is withheld pending the decision.
- **Editable Fields:** None. Per AGENT_LOGIC_SPEC.md Section 1, `EverydayDecisionCardEmitter` has no write access to audit-origin fields, and this UI layer does not invent an edit capability the cognitive layer doesn't support — the reviewer decides among the three fixed actions; they do not alter the audited numbers.

**Resumption Payload Contract:**

**On "Approve Release":**
```json
{
  "action": "APPROVE_RELEASE",
  "checkpoint_id": "...",
  "modified_inputs": null
}
```

**On "Hold — Request Correction":**
```json
{
  "action": "HOLD_REQUEST_CORRECTION",
  "checkpoint_id": "...",
  "modified_inputs": null,
  "reason": "optional user-supplied text explaining the hold"
}
```

**On "Escalate Legal":**
```json
{
  "action": "ESCALATE_LEGAL",
  "checkpoint_id": "...",
  "modified_inputs": null,
  "reason": "optional user-supplied text explaining the escalation"
}
```

**Note on deviation from the base template:** The generic Approve/Deny/Edit contract is replaced with these exact three actions because that is what AGENT_BEHAVIOR_PROFILE.md Section 8 and AGENT_LOGIC_SPEC.md Section 1 actually define — inventing a generic "deny" or an "edit inputs" capability here would be a control this UI layer is prohibited from adding (base template Rule: "Never invent new controls or capabilities not backed by agent logic"). `modified_inputs` remains in the contract shape only to preserve schema symmetry with the base template; it is always `null` in this system and MUST be rejected by the backend if a client ever sends a non-null value, since no field in `decision_card_payload` is user-editable.

**Backend Resumption Behavior:**
- **On Approve Release:** The AgentCore session resumes from the Step-5 checkpoint, writes `approval_state = APPROVE_RELEASE`, and the graph transitions to its terminal success state — this authorization artifact then leaves this system's execution authority (AGENT_BEHAVIOR_PROFILE.md Goal Boundaries).
- **On Hold — Request Correction:** Resumes, writes `approval_state = HOLD_REQUEST_CORRECTION`, and the correction-letter dispatch fires per AGENT_BEHAVIOR_PROFILE.md Section 8.
- **On Escalate Legal:** Resumes, writes `approval_state = ESCALATE_LEGAL`, and the packet routes to legal counsel per the same section.
- **Validation:** The backend rejects any resumption payload where `action` is not exactly one of the three literal values, or where `modified_inputs` is non-null, before writing to `approval_state` — this mirrors AGENT_LOGIC_SPEC.md Section 4's strict enum validation on the underlying tool schemas.

**Timeout Behavior:** Per AGENT_BEHAVIOR_PROFILE.md Section 8 — if no human response arrives and `statutory_prompt_pay_clock.days_remaining` reaches the critical threshold (≤ 2 days), `dispatch_decision_notification` fires the `URGENT_STATUTORY_ESCALATION` notification automatically; the card itself keeps waiting indefinitely (no auto-timeout ever silently selects an action on the human's behalf) and the countdown timer visually communicates the growing urgency in the meantime.

---

## **6. ACTIVITY, AUDIT LOGS & TELEMETRY/TRACING**

**Telemetry Standard Verification Note:** Live-verified in this session: OpenTelemetry GenAI Semantic Conventions remain in **Development** status as of this session (moved to the dedicated `open-telemetry/semantic-conventions-genai` repository; no tagged release; attribute names like `gen_ai.provider.name`, `gen_ai.operation.name` are stable in practice but not formally Stable in OTel's own maturity ladder). This instability is a real, current finding, not an unverifiable gap — it is factored into the choice below rather than hidden.

**Chosen Tracing Backend:** A verified hybrid, and one that requires essentially no extra instrumentation work given the architecture already locked in Step 2: **Amazon Bedrock AgentCore Runtime auto-instruments the Strands agent via AWS Distro for OpenTelemetry (ADOT) and emits OTel-compatible spans to the `bedrock-agentcore` CloudWatch namespace by default** (verified current — this satisfies the mandate's CloudWatch requirement natively, with zero additional code). The same OTLP-formatted spans are additionally dual-exported to **Langfuse's native OTel ingestion endpoint** (verified current — Langfuse accepts OTLP/HTTP traces directly) so that scoring, annotation, and evaluation-dataset workflows (Section 7a) have a purpose-built LLM-observability UI alongside CloudWatch's infrastructure-level dashboards.

**Trace/Span Model:**
- **Trace:** One trace = one draw-packet run, keyed by the same `session_id` used for AgentCore Memory checkpointing (AGENT_ORCHESTRATION_BLUEPRINT.md Section 7) — trace and session identity are the same identifier by design, so a reviewer can go from "this card" to "this trace" with no separate lookup.
- **Span Hierarchy:** trace → per-node `invoke_agent` span (one each for `ForensicAuditSentinel`, `FairPayStatutoryGuardian`, `EverydayDecisionCardEmitter`, per the GenAI `invoke_agent` operation convention) → `execute_tool` child spans for each of the six tools → an `inference` child span for each underlying Sonnet 5 / Haiku 4.5 model call.
- **Span Attributes Captured:** `gen_ai.provider.name` (`aws.bedrock`), `gen_ai.operation.name` (`invoke_agent` / `execute_tool` / `inference`), `gen_ai.request.model` / response model, input/output token counts, latency (span duration), and — per the verified GenAI convention's privacy guidance — no full prompt/document text in span *attributes*; extracted-document content, if captured at all for debugging, goes in span *events* only, which can be filtered/dropped at the collector level without touching agent code.

**Event Types Logged:**

**User Actions:**
- The single decision (`APPROVE_RELEASE` / `HOLD_REQUEST_CORRECTION` / `ESCALATE_LEGAL`) and its optional `reason` text.
- Any tab reload while awaiting decision (session-resumption event, not a new action).

**Agent Reasoning:**
- `ForensicAuditSentinel`'s native-thinking spans (Section 3a), when enabled.
- Graph-trace spans for all three nodes.

**Agent Actions:**
- All six tool calls, each with input/output digests, latency, and success/failure, per the `execute_tool` span convention.
- Every `IroncladState` write, tagged with its field name and reducer.

**System Events:**
- Errors and Permanent/Transient/Ambiguous failure classifications (AGENT_LOGIC_SPEC.md Section 9).
- The HITL `approval-required` trigger and the resumption payload that resolved it.
- Any safety-guardrail-triggered rejection (AGENT_LOGIC_SPEC.md Section 10).

**User-Visible vs Internal Logs:**

**User-Visible Activity Log:** The Audit Trail panel itself (Section 3b) — high-level, per-node, per-tool events with plain-language labels; this IS the user-visible log in this system, not a separate page.

**Internal Debug/Trace Logs:**
- **Purpose:** Technical debugging, compliance audit, and evaluation-dataset construction.
- **Contents:** Full span tree per the model above — raw tool inputs/outputs (as span events), token/cost/latency breakdowns.
- **Format:** OTel spans, viewable in either the CloudWatch GenAI Observability console (Trace View, filterable by `session.id`) or the Langfuse UI.
- **Access:** CloudWatch console access (AWS IAM-gated) or Langfuse project access — never exposed inside the Streamlit reviewer UI itself, keeping the reviewer's surface to the card + Audit Trail only.

**Timestamping & Trace Structure:**

**Timestamp Format:** Absolute time with a relative annotation in the Audit Trail ("2:31 PM · 4 minutes ago"); spans in CloudWatch/Langfuse use standard OTel nanosecond timestamps.

**Trace Linking:** `execute_tool` and `inference` spans are children of their node's `invoke_agent` span, which is a child of the run's root trace — a direct three-level hierarchy, matching the graph's actual shape (no deeper nesting exists to represent).

**Session Boundaries:** One trace per draw-packet run; multiple draws for the same subcontractor are separate traces linked only by shared `project_id`/`subcontractor_id` resource attributes, not merged into one trace.

**Debug vs Normal User Modes:**

**Normal User Mode (the reviewer's only mode in this system):** Shows the card plus the opt-in Audit Trail panel; hides raw prompts, token counts, and cost figures entirely — these have no bearing on a payment-release decision.

**Debug Mode:** Does not exist inside the Streamlit reviewer UI — full observability lives in CloudWatch/Langfuse, accessed by engineers/auditors through those tools' own interfaces, not a hidden toggle inside the decision-card app. This keeps the zero-chat, single-purpose UI honest about its scope rather than smuggling a second, more complex UI into the same app.

**Log/Trace Retention & Export:**

**Retention:** Per the compliance database's own retention policy (outside this specification, per AGENT_ORCHESTRATION_BLUEPRINT.md Section 7); CloudWatch Logs/traces follow the account's configured retention, Langfuse follows its own project retention settings.

**Export:** The Audit Trail panel's "Download full audit trail (JSON)" link (Section 2) gives the reviewer a self-service export of that one run's checkpointed state; full trace export for engineering/compliance use goes through CloudWatch's CLI/SDK or Langfuse's API, not through the reviewer-facing app.

---

## **7. USER FEEDBACK & CONTROL LOOP**

**Interrupt Mechanisms:**

**How User Interrupts Agent:** There is no interrupt control in the normal sense — the graph runs unattended through the audit phase and pauses on its own at the one checkpoint (Section 5). The only human-initiated stop is closing the browser tab, which does not actually halt the backend run (Section 2).

**What Happens on (Tab) Interrupt:**
1. The AgentCore session checkpoint continues independently — Hop 1 is server-to-server and doesn't depend on a browser being open.
2. Reopening the session URL re-renders the current state, whatever phase it's in.
3. No "stopped" message is shown, since nothing was actually stopped.

**Correction Mechanisms:**

**How User Corrects Agent:** Only through the "Hold — Request Correction" action itself (Section 5) — there is no direct-correction chat, no undo/redo of the audit, since the audit is a deterministic, already-verified computation, not a draft the human edits.

**Agent Response to Correction:** On `HOLD_REQUEST_CORRECTION`, the correction-letter dispatch to the subcontractor is the agent's entire "response" — there is no re-audit loop inside this run; a corrected packet arrives as a new draw-packet event and a new session.

**Approval / Rejection Mechanisms:** Fully covered by Section 5's three-action contract; there is no separate "Deny" or "Ask for more info" option, since those aren't real actions this cognitive system supports.

**Regeneration vs Continuation:**

**Regeneration:** Not applicable — there is nothing to regenerate; the audit is deterministic, not a draft response a user might want "reworded."

**Continuation:** The only continuation is graph resumption after the HITL decision (Section 5) — covered there, not a separate mechanism.

**Confidence Signals Shown to User:**

**Agent Confidence Indicators:** Per-field, not per-response — the `low_confidence_fields` list from `extract_draw_packet_metadata` (Section 4a) is the only confidence signal in this system, and it always resolves into either a clean field or a `flagged_discrepancies` entry (AGENT_LOGIC_SPEC.md Section 8's confidence thresholds) rather than a floating "45% confident" label anywhere on the card — the card itself is binary: a field is either verified or it's a discrepancy.

**User Trust Signals & Feedback Capture:** No generic thumbs-up/down chat feedback exists in this system (there is no conversational response to rate). The feedback signal that does exist is the decision itself plus its optional `reason` text — captured in Section 7a below as the system's actual feedback mechanism, rather than inventing an unrelated satisfaction-rating widget this cognitive layer has no use for.

---

## **7a. FEEDBACK-TO-TELEMETRY ANNOTATION PIPELINE**

**Purpose:** Every human decision at the HITL gate becomes a structured, queryable Langfuse score on that run's trace, so audit-quality trends (e.g., how often clean audits get held anyway, or how often `ESCALATE_LEGAL` correlates with a specific discrepancy type) are analyzable over time.

**Feedback Signal → Annotation Mapping:**

| User Feedback Action | Captured At (Trace/Span) | Annotation Written | Backend Field (per verified schema) |
|---|---|---|---|
| `APPROVE_RELEASE` selected | Root trace (the run's `session_id`) | Categorical score, value = `"approve_release"` | Langfuse `score` object, `name: "reviewer_decision"`, `value: "approve_release"` |
| `HOLD_REQUEST_CORRECTION` selected | Root trace | Categorical score + attached `reason` text | Langfuse `score.value: "hold_request_correction"`, plus a linked comment on the trace with the `reason` text |
| `ESCALATE_LEGAL` selected | Root trace | Categorical score + attached `reason` text | Langfuse `score.value: "escalate_legal"`, plus a linked comment |
| A `HOLD`/`ESCALATE` where the audit itself was `PASSED`/clean (i.e., human overrode a clean recommendation) | Root trace | Boolean score `human_override_of_clean_audit: true` | Langfuse `score` object, `name: "human_override_of_clean_audit"`, `value: true` |

**Write Timing:** Immediately on resumption-payload receipt, before the graph resumes execution — the annotation write and the state-write to `approval_state` happen in the same backend transaction so a decision can never be recorded in one system and not the other.

**Dataset Use:** These trace-level scores let a compliance or product team later pull "all runs where the audit passed clean but a human still held or escalated" as an evaluation set — surfacing cases where the deterministic audit and human judgment diverge, which is exactly the kind of signal this Zero-Error-tolerance system should be watching, restated here at the specification level only.

---

## **8. AUTONOMY & SAFETY CONTROLS**

**Autonomy Level Indicators:**

**Current Autonomy Display:**
- **Location:** The status banner text itself doubles as the autonomy indicator — "Auditing packet…" implies automatic operation; "Audit complete — awaiting your decision" implies the human-gated state. No separate badge is added, since inventing a persistent "Semi-Autonomous" chip would add UI surface with no corresponding control (this system has exactly one fixed autonomy level; there's nothing for a user to toggle).
- **Format:** Plain text within the existing banner.
- **Clarity:** The banner text is written in plain language rather than the internal term "Semi-Autonomous," since the reviewer needs to know what's happening, not the architectural classification.

**Autonomy Level Settings:**

**Semi-Autonomous (fixed, non-configurable):**
- **Default State:** The only state — AGENT_BEHAVIOR_PROFILE.md Section 7 locks this as Semi-Autonomous with no user-facing toggle, and this UI layer does not invent one, per the base template's prohibition on adding controls the cognitive layer doesn't support.
- **User Control:** None — the reviewer cannot switch this system to Manual (approve every tool call) or Fully Autonomous (skip the release gate); both would violate AGENT_BEHAVIOR_PROFILE.md's locked autonomy level.
- **Change Mechanism:** None exists.

**Mode Switching:** Not applicable — there is only one mode.

**Manual Override Mechanisms:**

**Override Controls:**
- **Stop:** Not offered as a distinct control beyond tab-close (Section 7) — since the audit phase has no side effects to halt (it only reads documents and computes), there is nothing meaningful to "stop" before the HITL gate; after the gate, the reviewer's three buttons already are the full set of available actions.
- **Pause:** Not applicable — the graph already pauses on its own at the one checkpoint that matters.
- **Takeover:** Not applicable — there is no in-progress action a human could take over from the agent; the agent's only actions are read/compute (automatic) or notify (post-decision).

**Override Availability:** N/A, per above — this system's HITL gate already IS the override point; adding further override controls would be inventing capability the cognitive layer doesn't have.

**Human-in-the-Loop Trigger Visualization:** Covered fully in Section 5 — the card's own three-button state change from "disabled" to "enabled" is the trigger visualization; no separate modal or flashing badge is layered on top, per the zero-chat mandate keeping the card itself as the single approval surface.

**Visual Indicators:**
- **Pending Approval:** The three buttons render in an active, colored state (green/amber/red matching their semantics) the instant `approval-required` fires; before that, they render grayed-out and disabled.
- **Timeout Warning:** The countdown timer turning red and adding the "Critical" tag (Section 2) IS the timeout warning — there is no separate approval-timeout countdown, since AGENT_BEHAVIOR_PROFILE.md Section 8 defines only one deadline that matters (the statutory clock), not an arbitrary "please respond soon" UI-invented timer.

**Escalation States:**

**When Agent Escalates to Human:** Only automatically, via the `URGENT_STATUTORY_ESCALATION` notification when `days_remaining` ≤ 2 and no decision has been made (Section 5's Timeout Behavior) — this is a notification escalation, not a UI state change on the card itself, since the card was already fully actionable from the moment it appeared.

**Escalation UI:**
- **Indicator:** The countdown timer's red "Critical" state (already covered above) is the only escalation indicator on the card; the actual notification goes out through `dispatch_decision_notification`, external to this UI.
- **Explanation:** Not needed as separate UI text — the countdown timer's own numbers are the explanation.
- **User Options:** Unchanged — the same three buttons remain the reviewer's only options, now under visible time pressure.

**Failure or Escalation States:**

**Agent Failure Display:** Covered fully in Section 9.

**Safety Guardrail Activations:**

**When Guardrail Triggers:** Any of AGENT_LOGIC_SPEC.md Section 10's structural prohibitions being approached (e.g., a tool attempting to write outside its declared state field) is, by construction, impossible to reach at runtime — there is no code path for it to fire, so there is no corresponding UI state to design. The guardrails that DO have a visible effect are the ones tied to real failure paths (missing data, unresolvable jurisdiction, hash mismatch), which are the Permanent Failures already covered in Section 9.

**User Communication:**
- **Visible:** Yes, whenever a guardrail-adjacent failure halts the run (e.g., "Cannot proceed — required lien waiver data is missing" rather than a raw internal prohibition name).
- **Message:** Plain-language restatement of the specific `flagged_discrepancies`/`error_logs` entry, never the internal prohibition ID.
- **Transparency:** The Audit Trail panel, if expanded, shows the exact discrepancy type for a technically-minded reviewer; the status banner shows the plain-language version for everyone else.

---

## **9. ERROR & UNCERTAINTY UX**

**Uncertainty Communication Patterns:**

**Low Confidence:** A field that fell below AGENT_LOGIC_SPEC.md Section 8's confidence threshold is never shown as a number with a caveat — it is shown as a `flagged_discrepancies` row instead, per the Silence-Over-Guessing policy. There is no "45% confident, proceed with caution" state anywhere in this system, because the cognitive layer itself never produces one — a value is either verified or it's a discrepancy.

**Medium Confidence:** The one place a true medium-confidence signal survives to the UI is `low_confidence_fields` from `extract_draw_packet_metadata` (Section 4a) — shown as an amber highlight in the Audit Trail's field tree, not on the primary card, since the card's numbers have already passed the downstream audit tools regardless.

**High Confidence:** The default, unmarked state of every figure on the card.

**Ambiguity:**
- **When Request is Ambiguous:** Not applicable — there is no free-form request for a human to make ambiguous; the only human input is one of three fixed buttons.
- **When Tool Output is Ambiguous:** Per AGENT_LOGIC_SPEC.md Section 8's Cross-Examination rule — a `TYPE_MISMATCH` finding (e.g., a waiver referencing a nonexistent line item) is surfaced as its own discrepancy row, never silently resolved to the "nearest plausible" match.

**Failure Explanation Approach:**

**What Agent Admits:** Every Permanent Failure, every missing field, every unresolved jurisdiction — nothing is smoothed over, per AGENT_LOGIC_SPEC.md Section 9's Invalid Output Detection and this system's Zero-Error risk tolerance (AGENT_BEHAVIOR_PROFILE.md Section 1).

**What Agent Explains:**
- **Why failure occurred:** The specific `error_logs`/`flagged_discrepancies` description, restated in plain language.
- **What was attempted:** For a Transient failure, "retried 3 times" is shown; for a Permanent failure, "no retry — [specific reason retry wouldn't help]."
- **What user can do:** For most failures, nothing inside this UI — a failed audit routes to `INCOMPLETE_MANUAL_AUDIT_REQUIRED` and the reviewer's next step is outside this system (manual review), which the status banner says plainly rather than offering a fake "Retry" button that re-runs a computation that will fail identically.

### **Tool-Specific Failure Mapping Table:**

| Critical Tool | Failure Scenario | User Error Message | Recovery Action (UI) |
|---|---|---|---|
| `extract_draw_packet_metadata` | OCR timeout (Transient) | "Reading the document is taking longer than expected — retrying automatically." | None needed — auto-retry; no button shown |
| `extract_draw_packet_metadata` | Illegible/corrupt PDF (Permanent) | "This document could not be read and has been flagged for manual audit." | "Card will not appear — see Audit Trail for details" (no retry button, since retrying an illegible file won't help) |
| `audit_retainage_math` | Invalid/negative input (Permanent) | "A billing figure in this line item could not be verified." | No retry button — flows to the discrepancy table instead |
| `verify_lien_chain_integrity` | Empty waiver list (Permanent) | "No lien waivers were found for this draw." | Badge shows "FLAGGED — Missing Waiver"; no retry button |
| `statutory_prompt_pay_clock` | Unresolvable jurisdiction (Permanent) | "The statutory deadline could not be calculated for this project's jurisdiction." | Countdown area shows the red unavailable state (Section 4a); no retry button |
| `dispatch_decision_notification` | Delivery failure (Transient/Permanent) | "Notification could not be sent, but your decision was recorded successfully." | None — this failure never blocks or requires action, per Section 4 |

**Failure Types:**

### **Tool Failure**
- **Message:** As tabulated above, always tool-specific and plain-language.
- **User Options:** Almost always none, by design — this is a deterministic audit system, not an interactive assistant the reviewer troubleshoots; a failed audit is a manual-review referral, not a retry loop for the reviewer to manage.

### **Reasoning Failure**
- **Message:** "This packet could not be fully audited automatically and has been flagged for manual review." (maps to the per-node tool-call-budget exhaustion / stall detection in AGENT_LOGIC_SPEC.md Section 2).
- **User Options:** None inside this UI — routes to manual review, same as a Permanent tool failure.

### **Safety Violation Attempt**
- **Message:** Not user-visible in practice, since (per Section 8 above) every structural guardrail in this system is architecturally unreachable rather than something that "attempts and gets blocked" at runtime — there is no live scenario where this message would fire.

**Transparency vs Reassurance Balance:**

**Full Transparency When:** Any failure occurs, any discrepancy is flagged, any deadline turns critical — always, without exception, per the system's Zero-Error risk tolerance.

**Reassurance When:** A Transient failure is mid-retry (the banner says "retrying automatically" rather than alarming the reviewer over something the system will likely resolve on its own); a notification-dispatch failure (explicitly reassures that the decision itself was still recorded, Section 4).

**Balance Strategy:** Because this is a financial compliance system rather than a conversational assistant, transparency wins essentially every tie — the one place reassurance is warranted is distinguishing "this will self-resolve" (retry) from "this needs your attention" (everything else), and the UI keeps that distinction sharp rather than smoothing all failures into one generic error look.

**Trust Preservation Rules:**

**Never:** Show a card with a clean badge while a discrepancy exists; show a retry button for a failure retrying won't fix; soften a statutory deadline; invent a confidence percentage the cognitive layer didn't produce.

**Always:** Show the exact discrepancy text; show the exact countdown; let the reviewer's three buttons be the only route to a release decision.

**Trust-Building Patterns:**
1. The badge, figures, and discrepancy table are always internally consistent with each other because they're all copied verbatim from the same `decision_card_payload` — never independently derived by the UI layer.
2. The Audit Trail panel exists specifically so a skeptical reviewer can verify the card against the underlying tool calls themselves, rather than being asked to simply trust a summary.
3. Failures never disappear silently — a failed run either shows its failure state or doesn't render a card at all; it never renders a card with fabricated or defaulted values.

---

## **10. EXPLICIT UI NON-GOALS**

**What the Interface Will NOT Show:**

1. **A chat input box or conversational history of any kind**
   - **Reason:** Explicitly prohibited by the Step-4 mandate, and unsupported by the cognitive layer — no agent in AGENT_LOGIC_SPEC.md accepts free-form user text.

2. **Raw source PDF content, anywhere, in any view**
   - **Reason:** Source documents are read-only references (AGENT_LOGIC_SPEC.md Section 1); rendering their raw content risks displaying an injection payload verbatim and adds no verification value beyond the already-normalized typed fields.

3. **A generic "confidence score" or percentage on the primary card**
   - **Reason:** The cognitive layer's actual output is binary per field (verified or flagged) — inventing a blended percentage would misrepresent how the audit actually works.

4. **A configurable autonomy-level toggle**
   - **Reason:** AGENT_BEHAVIOR_PROFILE.md locks Semi-Autonomous with no user-facing switch; adding one would be a control not backed by the cognitive layer.

**What Will NOT Be Exposed to Users:**

**Internal System Details:**
- The AWS Strands `GraphBuilder` topology, model routing logic, and prompt-caching strategy (AGENT_ORCHESTRATION_BLUEPRINT.md Sections 5/8) — irrelevant to a payment-release decision.
- Exact token counts and per-call cost figures — available only in CloudWatch/Langfuse (Section 6), not the reviewer UI.

**Sensitive System Information:**
- Internal `tool_call_id`/`checkpoint_id`/`session_id` values beyond what's needed to key the resumption payload — shown to the backend, not surfaced as reviewer-facing text.
- The exact prompt-injection-detection mechanics referenced in AGENT_LOGIC_SPEC.md Section 8 — naming the detection method would teach circumvention, consistent with treating that as internal defense-in-depth rather than a documented feature.

**What Is Intentionally Abstracted:**

**Technical Implementation:** The two-hop streaming architecture (Section 2) is invisible to the reviewer — they simply see a card populate; whether that came from AgentCore's SSE stream or a Streamlit rerun is implementation detail with zero decision-relevance.

**System Complexity:** The three-node parallel graph is shown as three clearly-labeled sub-expanders (Section 3b), not hidden — but it is never presented on the primary card, where "the audit" reads as one coherent process rather than three separately-running agents, since that distinction doesn't change what the reviewer needs to decide.

**Abstraction Strategy:** Abstract *how* the answer was produced (framework, model routing, transport) freely; never abstract *what* the answer says (any figure, status, or deadline) — the first category is implementation, the second is the actual compliance-relevant content this system exists to surface accurately.

---

## **INTERFACE SYSTEM INTEGRITY DECLARATION**

This interface specification is AUTHORITATIVE.

All downstream systems must:
- Implement interaction model exactly as specified
- Stream responses per the defined typed event data contract
- Show reasoning visibility per specified rules, distinguishing native thinking tokens from graph traces
- Display tool actions and structured outputs with the defined observability and generative UI components
- Implement the exact HITL graph-resumption payload contract for every approval gate
- Capture telemetry per the verified tracing standard chosen in Section 6
- Wire user feedback into the telemetry annotation pipeline exactly as specified
- Provide activity logs as specified
- Enable user feedback and control mechanisms
- Surface autonomy and safety controls
- Communicate errors and uncertainty honestly
- Respect all explicit non-goals

The interface must faithfully reflect agent cognitive reality.
No simplification may hide what agent actually does.
No embellishment may fake capabilities agent doesn't have.
No streaming event or trace may be invented that doesn't correspond to a real step in LLM-3's cognitive design.

Trust is built through transparency, honesty, and control.

---
