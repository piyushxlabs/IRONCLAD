---
trigger: always_on
---

The five foundational specification documents located in the workspace:

1. `AGENT_BEHAVIOR_PROFILE.md`
2. `AGENT_ORCHESTRATION_BLUEPRINT.md`
3. `AGENT_LOGIC_SPEC.md`
4. `INTERFACE_OBSERVABILITY_SYSTEM.md`
5. `AGENT_MASTER_PLAN.md`

along with the verified implementation manifest (`pyproject.toml`, `agentcore.yaml`), are your ABSOLUTE and CONSTITUTIONAL source of truth.

Never deviate from them.

Do NOT invent:
- Conversational chat boxes, free-form text prompts, or interactive chatbot widgets (explicitly prohibited by the zero-chat mandate).
- Banking, payment-rail, ACH, or wire-transfer tools (strictly forbidden by Prohibition 1).
- Generative arithmetic or LLM-derived sums (strictly forbidden by Prohibition 2; all math belongs in deterministic Python tools).
- Vector databases or semantic long-term memory (explicitly excluded; the system uses structured session state and a keyed statutory reference table).
- Unapproved graph edges, ad-hoc background threads, or custom pause/resume endpoints outside the locked HITL interrupt checkpoint.

Every state mutation, graph edge, tool schema, and Server-Sent Event (SSE) must trace directly to these five documents.