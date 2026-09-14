---
trigger: always_on
---

Never refactor, rename, restructure, or modify working code, schemas, or directory layouts without explicit user permission.

If you believe an architectural adjustment is needed, state:

* What you want to change (specific `IroncladState` fields, reducers, Strands `GraphBuilder` nodes, tool signatures, or provider interfaces).

* Why it is needed (referencing the 5 locked specification documents: `AGENT_BEHAVIOR_PROFILE.md`, `AGENT_ORCHESTRATION_BLUEPRINT.md`, `AGENT_LOGIC_SPEC.md`, `INTERFACE_OBSERVABILITY_SYSTEM.md`, or `AGENT_MASTER_PLAN.md`).

* What could break (e.g., single-writer state guarantees, Bedrock AgentCore deployment compatibility, Streamlit zero-chat card rendering, or lazy `boto3` initialization).

Then wait for explicit user approval.

Unauthorized refactoring of the `IroncladState` schema, declared reducers, or the Tri-Track multi-agent topology is an architectural violation.