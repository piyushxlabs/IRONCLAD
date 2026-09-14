---
trigger: always_on
---

Bare `try-except` blocks with `pass` are strictly forbidden.

All errors must be explicitly typed using the custom `IroncladError` hierarchy:
- `ToolExecutionError`
- `StateValidationError`
- `ApprovalTimeoutError`
- `ProhibitedActionError`
and logged to `error_logs` with full incident and node context.

Transient dependencies (OCR extraction MCP server, notification-dispatch MCP server) must implement exponential backoff:
- 1s -> 4s -> 16s
Maximum 3 retry attempts. Deterministic math and date tools have ZERO retries on validation failure (invalid data is an immediate permanent failure).

Strictly enforce the Silence-Over-Guessing Policy (Prohibition 3):
- If a required field (invoice amount, retainage percentage, notary date, statutory clause) is missing or illegible, NEVER fabricate, coerce, or assume default values (e.g., never assume 5% retainage if unreadable).
- Low-confidence or unreadable extractions must append a typed `Discrepancy` to `flagged_discrepancies` and leave the corresponding audit field unset, forcing `recommended_action` away from `APPROVE_RELEASE`.

Cognitive reasoning must use strictly typed structured outputs:
- `LineItemMappingAndDiscrepancy`
- `RiderClauseClassification`
- `DecisionCardPayload`
Configured with strict Pydantic models at `temperature=0.0`.