---
trigger: always_on
---

Before executing any graph node or tool call, enforce strict pre-condition invariants in Python code:

1. **State Immutability:**
   - `draw_packet_meta` and `runtime_config` are strictly immutable after initialization (`immutable-after-init`) — any overwrite attempt must raise `StateValidationError`.

2. **`extract_draw_packet_metadata` Preconditions:**
   - Must only execute if `draw_packet_meta.source_uris` is non-empty and passed ingress bucket allowlist checks.
   - URI must match allowed schemes (e.g., `s3://` in production or local fixture paths in staging/mock).

3. **`audit_retainage_math` Preconditions:**
   - Parameters (`contract_retainage_pct`, `current_billed`, `stored_materials`, `prior_payments`) must be non-negative Decimals/floats and non-null.
   - Must only be invoked after `LineItemMappingAndDiscrepancy` normalizes the extracted data. Never call with placeholder or guessed values.

4. **`verify_lien_chain_integrity` Preconditions:**
   - Requires `waivers` list to contain at least 1 record (an empty list must fail immediately with a `MISSING_WAIVER` discrepancy before calling the tool).
   - `check_date` must parse as a valid ISO 8601 date and not be future-dated.

5. **`statutory_prompt_pay_clock` Preconditions:**
   - Requires `state_jurisdiction` to resolve to an active key in the statutory reference table (`src/statutory_reference/lookup.py`).
   - `contract_clause` must be strictly validated as `"pay-if-paid"` or `"pay-when-paid"` from `RiderClauseClassification` — never invoke with null or ambiguous classifications.

6. **`dispatch_decision_notification` Preconditions:**
   - Standard path: Must only execute AFTER `decision_card_payload` is written to state in the same turn.
   - Escalation path: Only executes if `statutory_prompt_pay_clock.days_remaining <= 2` AND `approval_state` is currently `None`.
   - `recipients` must be a subset of `["GENERAL_CONTRACTOR", "OWNER", "SUBCONTRACTOR"]`.

7. **Single-Writer Reducer Checks:**
   - State updates must verify caller identity before modifying fields in `src/state/reducers.py`:
     - Only `ForensicAuditSentinel` may write `extracted_line_items`, `retainage_audit_result`, `lien_chain_status`.
     - Only `FairPayStatutoryGuardian` may write `statutory_prompt_pay_clock`.
     - Only `EverydayDecisionCardEmitter` may write `decision_card_payload`.
     - Only the HITL resumption handler may write `approval_state`.