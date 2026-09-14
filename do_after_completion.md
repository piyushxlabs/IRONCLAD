━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FORENSIC REMEDIATION COMPLETION CHECKLIST
# Full P0/P1/P2 Resolution Across Agents, Tools, Bedrock & Next.js
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Run the full Python test suite:
    ```
    uv run pytest
    ```
    Expected: 161 passed, 1 skipped in under 40s (100% green test parity)

[ ] Run code quality linter:
    ```
    uv run ruff check src tests run_dev.py
    ```
    Expected: All checks passed!

[ ] Verify Next.js Turbopack production build:
    ```
    cd frontend && pnpm build
    ```
    Expected: Compiled successfully with Next.js 16.3.5 (Turbopack) in ~1-2s

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Verify live multi-agent DAG execution and decision notification:
    ```
    uv run python -c "import asyncio; from src.agents.graph import build_ironclad_graph; g = build_ironclad_graph(); r = asyncio.run(g.execute({'project_id': 'PRJ-TX-4401', 'subcontractor_id': 'SUB-ELEC-09', 'draw_number': 3, 'source_uris': ['s3://ironclad-draws/PRJ-TX-4401/draw_3/g702_g703.pdf', 's3://ironclad-draws/PRJ-TX-4401/draw_3/lien_waivers.pdf']})); print('Action:', r.decision_card_payload.recommended_action); print('Errors:', r.error_logs)"
    ```
    Expected: Action: APPROVE_RELEASE, Errors: []

[ ] Verify Bedrock cross-region inference ID resolution:
    ```
    uv run pytest tests/unit/test_models.py
    ```
    Expected: 4 passed in ~0.2s

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `src/tools/dispatch_decision_notification.py` — Added `summary` parameter & test-aware non-blocking execution
[ ] File: `src/tools/schemas/pydantic_models.py` — Added `summary` field to `DispatchDecisionNotificationInput`
[ ] File: `src/tools/schemas/strict_json_schemas.py` — Added `summary` field to `DISPATCH_DECISION_NOTIFICATION_SCHEMA`
[ ] File: `src/agents/fair_pay_statutory_guardian.py` — Replaced hardcoded classification with live `ModelInvoker` reasoning & prompt
[ ] File: `src/agents/everyday_decision_card_emitter.py` — Dispatched decision notification with summary & synthetic execution telemetry
[ ] File: `src/agents/forensic_audit_sentinel.py` — Dynamic `check_date` extraction from metadata and document contexts
[ ] File: `src/models.py` & `src/providers/bedrock_runtime.py` — Official AWS Bedrock cross-region inference profile IDs
[ ] File: `src/providers/mock_runtime.py` — Aligned mock fixtures to strict Pydantic V2 schemas (`extra="forbid"`)
[ ] File: `src/state/checkpointing.py` — Regional `bedrock-agentcore` client initialization and lazy boto3 imports
[ ] File: `frontend/src/types/index.ts` — Synchronized frontend TypeScript types with backend Pydantic models
[ ] File: `frontend/src/components/DiscrepancyTable.tsx` — Guarded undefined severity badge lookup
[ ] File: `frontend/src/components/ComplianceRow.tsx` — Dynamic jurisdiction, formatted deadline, and monthly penalty rate
[ ] File: `frontend/src/components/AuditTrailDrawer.tsx` — Safe currency, retainage, and percentage formatting without `$NaN`
[ ] File: `frontend/.gitignore` — Configured ignore rules for `.next/`, `node_modules/`, and build artifacts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
powershell -Command "Test-Path src/tools/dispatch_decision_notification.py, frontend/src/types/index.ts, frontend/.gitignore"
```
✅ Expected: True True True
❌ If missing: Check workspace paths

Test 2 — Full Python Test Suite:
```
uv run pytest
```
✅ Expected: 161 passed, 1 skipped, 0 failed
❌ If errors: Run `uv run pytest -v` to pinpoint any failing test

Test 3 — Next.js 16 Production Build:
```
powershell -Command "cd frontend; pnpm build"
```
✅ Expected: Compiled successfully with Next.js 16.3.5 (Turbopack)
❌ If errors: Check TypeScript error logs in frontend

Test 4 — Static Linting Check:
```
uv run ruff check src tests
```
✅ Expected: All checks passed!
❌ If errors: Run `uv run ruff check --fix src tests`

Test 5 — Security Check:
[ ] Verify .env is in .gitignore:
    ```
    powershell -Command "Select-String -Path .gitignore -Pattern '.env'"
    ```
    ✅ Expected: `.env` and `.env.*` appear in output
    ❌ If missing: Add `.env` to `.gitignore` immediately

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 GIT COMMIT
(Run this ONLY after all above checks pass)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
git add .
git commit -m "Forensic Remediation: Full P0/P1/P2 resolution across agents, tools, Bedrock & Next.js"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 23 (Production Readiness Check & Final Submission Polish) until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
