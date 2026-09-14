━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTERFACE UPGRADE PHASE 2 COMPLETION CHECKLIST
# Next.js 15 Executive Decision Console Scaffolding
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Verify Next.js production build:
    ```
    cd frontend && pnpm build
    ```
    Expected: Compiled successfully with 0 errors (static pages generated)

[ ] Verify full Python backend test suite:
    ```
    uv run pytest
    ```
    Expected: 157 passed, 1 skipped in under 10.00s

[ ] Verify Python linting:
    ```
    uv run ruff check src tests
    ```
    Expected: All checks passed!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Optional: Launch development servers side-by-side to preview live dashboard:
    1. In Terminal 1 (FastAPI backend):
       ```
       uv run uvicorn src.server:app --port 8000
       ```
    2. In Terminal 2 (Next.js frontend):
       ```
       cd frontend && pnpm dev
       ```
    Expected: Console accessible at http://localhost:3000

[ ] Functional UI Inspection:
    - Open http://localhost:3000 in your browser
    - Click "Execute Audit" to trigger real-time SSE streaming from FastAPI
    - Observe 3 financial KPI tiles, lien status badge, and prompt-pay countdown
    - Verify 3-button HITL Action Center and expandable Forensic Audit Trail

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `frontend/src/app/page.tsx` — Single-page Zero-Chat Executive Decision Console
[ ] File: `frontend/src/components/Header.tsx` — Project metadata, scenario picker, and runtime badge
[ ] File: `frontend/src/components/StatusBanner.tsx` — Real-time animated SSE stage tracker
[ ] File: `frontend/src/components/FinancialSummary.tsx` — 3 dominant financial KPI tiles (Gross, Retainage, Net)
[ ] File: `frontend/src/components/ComplianceRow.tsx` — Lien chain status & Prompt-Pay statutory countdown
[ ] File: `frontend/src/components/DiscrepancyTable.tsx` — Interactive audit findings and severity badges
[ ] File: `frontend/src/components/ActionCenter.tsx` — 3-button authenticated HITL action center
[ ] File: `frontend/src/components/AuditTrailDrawer.tsx` — Collapsible execution timeline and audit JSON export
[ ] File: `frontend/src/lib/api.ts` — SSE client for streaming and HITL decision submission
[ ] File: `frontend/src/types/index.ts` — TypeScript models mirroring backend Pydantic schemas
[ ] Config: `frontend/tailwind.config.ts` — Institutional dark theme (`#0B0F19`, `#111827`, `#1F2937`)
[ ] Package: `next@15.1.7`, `react@19.3.0`, `tailwindcss@3.4.19`, `lucide-react@0.475.0`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
powershell -Command "Test-Path frontend/src/app/page.tsx, frontend/src/lib/api.ts, frontend/src/components/Header.tsx"
```
✅ Expected: True True True
❌ If missing: Check `frontend/src/` structure

Test 2 — Environment / Dependencies:
```
node -v; pnpm -v
```
✅ Expected: Node v24+, pnpm v11+
❌ If errors: Ensure Node.js and pnpm are installed and on PATH

Test 3 — Next.js Build Check:
```
powershell -Command "cd frontend; pnpm build"
```
✅ Expected: Compiled successfully with 0 errors
❌ If errors: Check TypeScript types and imports in `frontend/src/`

Test 4 — Python Backend Regression Check:
```
uv run pytest
```
✅ Expected: 157 passed, 1 skipped
❌ If errors: Ensure Python backend remains untouched

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
git commit -m "Interface Upgrade Phase 2: Next.js 15 App Router Executive Decision Console Scaffolding"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Phase 3 (Integration & Verification Scripts) until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
