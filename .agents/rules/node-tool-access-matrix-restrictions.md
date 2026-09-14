---
trigger: always_on
---

The nodes in `src/agents/` must strictly enforce the Node-Tool Access Matrix defined in `AGENT_LOGIC_SPEC.md` Section 6:

* **Ingress Node (Deterministic, Non-LLM):** Ingests webhook/multipart payload, verifies document hashes, validates envelope IDs. NO external tool calls.
* **`ForensicAuditSentinel` (Professional Track Node):** Bound ONLY to:
  - `extract_draw_packet_metadata` (OCR/extraction MCP)
  - `LineItemMappingAndDiscrepancy` (Structured Output)
  - `audit_retainage_math` (Deterministic math tool)
  - `verify_lien_chain_integrity` (Deterministic date validation tool)
  STRICTLY FORBIDDEN from writing to `statutory_prompt_pay_clock` or `decision_card_payload`.
* **`FairPayStatutoryGuardian` (Good Neighbor Track Node):** Bound ONLY to:
  - `RiderClauseClassification` (Structured Output)
  - `statutory_prompt_pay_clock` (Deterministic statutory engine reading internal reference data)
  STRICTLY FORBIDDEN from calling OCR extraction, retainage math tools, or lien chain tools.
* **`EverydayDecisionCardEmitter` (Everyday Track Node):** Bound ONLY to:
  - `DecisionCardPayload` (Structured Output synthesis)
  - `dispatch_decision_notification` (Notification MCP)
  STRICTLY FORBIDDEN from calling any arithmetic, OCR, or date-math tools. Receives upstream state as READ-ONLY inputs.
* **HITL Interrupt Gate (Deterministic Checkpoint):** Bound ONLY to the authenticated human action (`APPROVE_RELEASE`, `HOLD_REQUEST_CORRECTION`, `ESCALATE_LEGAL`). NO model calls.

Prohibition 1 Hard Boundary:
No node in this system may ever hold, import, or bind tools for bank transfers, ACH, credit cards, or ERP ledgers.