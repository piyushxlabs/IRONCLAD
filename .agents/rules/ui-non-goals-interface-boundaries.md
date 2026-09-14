---
trigger: always_on
---

Per `INTERFACE_OBSERVABILITY_SYSTEM.md` Section 10, the Streamlit review interface must NOT include:

1. A conversational chat box, prompt text area, or multi-turn conversational message interface (the interface is strictly a single-page Executive Decision Card, not a chatbot).

2. Inlined raw PDF document text or scanned image blobs (source documents remain read-only references; displaying raw unstructured text creates prompt injection display risks and clutters the card).

3. A generic blended "confidence score" percentage on the card (audit verification is deterministic and binary per field: verified or discrepancy).

4. A configurable autonomy-level toggle (Manual vs. Fully Autonomous) — the system is permanently locked to Semi-Autonomous per `AGENT_BEHAVIOR_PROFILE.md`.

5. Editable financial input fields on the card during the HITL gate (all figures are read-only reflections of audited state; the reviewer chooses between `APPROVE_RELEASE`, `HOLD_REQUEST_CORRECTION`, and `ESCALATE_LEGAL`, but cannot manually alter the verified math).

6. Arbitrary "please respond soon" countdown timers — the only countdown allowed is the legally mandated State Prompt-Payment statutory countdown.

7. Emergency stop or pause buttons (the audit phase has no real-world transacting side effects before the HITL gate; the three action buttons already represent the full decision set).

If any instruction implies adding these components, flag it as an interface specification violation before building.