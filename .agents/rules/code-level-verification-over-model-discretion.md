---
trigger: always_on
---

Human-in-the-Loop (HITL) gates, release recommendations, and state mutation boundaries must be independently enforced in deterministic Python code, NEVER left to model discretion:

1. Fixed Decision Logic for Fund Release:
   - `EverydayDecisionCardEmitter` MUST enforce `recommended_action` via deterministic Python code:
     `if len(state.flagged_discrepancies) == 0 and state.lien_chain_status == LienChainStatus.VALID: recommended_action = "APPROVE_RELEASE"`
     `else: recommended_action = "HOLD_REQUEST_CORRECTED_WAIVER" (or "ESCALATE_LEGAL" per discrepancy severity)`
   - Never permit the model to recommend release if an open discrepancy exists or if lien status is not `VALID`.

2. Citation Grounding & Zero LLM Math:
   - Code must verify that every single dollar figure in `decision_card_payload` (`gross_amount_requested`, `contractual_retainage_withheld`, `net_recommended_release`) matches byte-for-byte a verified calculation output from `audit_retainage_math` in `state.retainage_audit_result`.
   - If any number originates from free-text model generation, reject the state write immediately.

3. Single-Writer State Reducer Enforcement:
   - Enforce writer boundaries programmatically in `src/state/reducers.py`:
     - `extracted_line_items`, `retainage_audit_result`, `lien_chain_status` -> writable ONLY by `ForensicAuditSentinel`.
     - `statutory_prompt_pay_clock` -> writable ONLY by `FairPayStatutoryGuardian`.
     - `decision_card_payload` -> writable ONLY by `EverydayDecisionCardEmitter`.
     - `approval_state` -> writable ONLY by the HITL resumption handler.
     - `flagged_discrepancies` and `error_logs` -> append-only reducers.

4. Immutability of Financial Inputs:
   - Original document references (`draw_packet_meta.source_uris`) and runtime configurations are immutable after initialization. Code must prevent any node from modifying source documents.