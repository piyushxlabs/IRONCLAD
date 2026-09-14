---
trigger: always_on
---

All cognitive reasoning across `ForensicAuditSentinel`, `FairPayStatutoryGuardian`, and `EverydayDecisionCardEmitter` must be 100% grounded in verified data:

1. **Strict Citation Enforcement:**
   - Every factual assertion, variance figure, or note in `flagged_discrepancies.description` and `decision_card_payload` must explicitly cite the specific upstream tool output or state field it originated from (e.g., "per verify_lien_chain_integrity finding waiver_id=W-004: PRE_DATED_NOTARY").
   - Any dollar amount or date generated as ungrounded free text must fail Pydantic validation and be rejected.

2. **Silence-Over-Guessing Policy (Prohibition 3):**
   - If an invoice number, line-item subtotal, notary seal date, or retainage clause is unreadable, blurred, or missing from the PDF, NEVER guess or infer a plausible value.
   - Low confidence (< 0.60) or missing values must append a typed `Discrepancy` to `flagged_discrepancies` and leave the corresponding state field unset, structurally preventing an unverified `APPROVE_RELEASE`.

3. **Cross-Examination Rule:**
   - If a lien waiver's `associated_line_item_id` references an item not present in `extracted_line_items`, the agent must surface a `TYPE_MISMATCH` discrepancy; it must NEVER silently re-assign the waiver to the nearest plausible line item.

4. **Absolute Prohibitions:**
   Under no circumstances may any prompt, agent node, or tool:
   - Perform retainage arithmetic, line-item additions, or interest penalty calculations via natural language reasoning (Prohibition 2).
   - Initiate, execute, or simulate banking transactions, wire transfers, ACH payments, or ERP ledger postings (Prohibition 1).
   - Modify, rewrite, or overwrite uploaded source PDF files (Prohibition 4).
   - Suppress, recalculate, or extend statutory prompt-payment deadlines to favor a General Contractor (Prohibition 5).
   - Adjudicate change-order disputes, contract validity, or the legal enforceability of `pay-if-paid` clauses (Section 11 Out-of-Scope).