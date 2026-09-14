---
trigger: always_on
---

You must strictly follow "SECTION 10: STEP-BY-STEP EXECUTION SEQUENCE" from `AGENT_MASTER_PLAN.md` (Steps 1 to 23).

Execution Rules:

1. Never work on more than ONE step at a time (e.g., complete Step 7: Configure Models and verify it before starting Step 8: Typed State Schema & Reducers).

2. Never begin the next step until the user explicitly reviews the current step's code and types "Proceed" or "Yes".

3. After completing a step, output a concise verification checklist demonstrating that all unit tests, schemas, and invariants required by Section 9.2/9.6 have passed, and WAIT for confirmation before proceeding.