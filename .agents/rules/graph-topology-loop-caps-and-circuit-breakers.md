---
trigger: always_on
---

The agent workflow must strictly implement the fan-out/fan-in directed acyclic graph (DAG) topology using the AWS Strands Agents SDK `GraphBuilder` defined in `AGENT_ORCHESTRATION_BLUEPRINT.md` Section 4:

`ingress (deterministic validation) -> [ForensicAuditSentinel || FairPayStatutoryGuardian] -> EverydayDecisionCardEmitter -> hitl_interrupt -> terminal`

Do NOT create open-ended ReAct agent loops, autonomous multi-turn chat cycles, or unmanaged recursive loops.

Execution boundaries and cycle caps are strictly enforced:

1. Acyclic Graph Flow:
   - Ingress fans out to `ForensicAuditSentinel` (Pro track) and `FairPayStatutoryGuardian` (Good Neighbor track) concurrently.
   - Both nodes must complete before fan-in edge triggers `EverydayDecisionCardEmitter` (Everyday track).
   - `EverydayDecisionCardEmitter` writes `decision_card_payload` and triggers the single, mandatory `hitl_interrupt`.

2. Per-Node Micro-Loop Cap:
   - Tool and structured-output calls inside any single node are hard-capped at `MAX_NODE_CALLS = 4` (enforcing the 2-level recursive sub-goal limit from `AGENT_BEHAVIOR_PROFILE.md` Section 9).
   - A node calling the same tool twice with byte-identical arguments is treated as a stall and converts to a `Discrepancy`/`ErrorRecord` immediately.

3. Circuit Breaker:
   - If progress halts (no new state field written and no discrepancy logged during a cycle), the circuit breaker trips, sets the audit to `INCOMPLETE_MANUAL_AUDIT_REQUIRED`, and terminates the run cleanly without emitting partial release figures.