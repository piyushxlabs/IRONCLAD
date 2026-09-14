━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTERFACE UPGRADE PHASE 3 COMPLETION CHECKLIST
# Integration, Modernization to Next.js 16 & Unified CLI Runners
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Run the unified status diagnostic check:
    ```
    uv run python run_dev.py status
    ```
    Expected: All 4 subsystems report [OK] (FastAPI, DAG, Streamlit, Next.js 16)

[ ] Verify Next.js 16 Turbopack production build:
    ```
    cd frontend && pnpm build
    ```
    Expected: Compiled successfully with Next.js 16.3.5 (Turbopack) in under 5s

[ ] Run the full Python regression test suite across all 22 test files:
    ```
    uv run pytest
    ```
    Expected: 161 passed, 1 skipped in under 15.00s

[ ] Run code quality linter:
    ```
    uv run ruff check src tests run_dev.py
    ```
    Expected: All checks passed!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Optional: Launch development environment with unified commands:
    1. Terminal 1 — Launch FastAPI backend:
       ```
       uv run python run_dev.py server
       ```
       Expected: FastAPI serving on http://0.0.0.0:8000
    2. Terminal 2 — Launch Next.js 16 Executive Console:
       ```
       cd frontend && pnpm dev
       ```
       Expected: Dashboard active on http://localhost:3000
    3. Terminal 3 (Optional fallback) — Launch Streamlit Console:
       ```
       uv run python run_dev.py streamlit
       ```
       Expected: Streamlit active on http://localhost:8501

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `run_dev.py` — Unified CLI development runner (server, streamlit, agentcore, status)
[ ] File: `tests/integration/test_unified_runners.py` — Integration test suite for runners and manifests
[ ] File: `frontend/package.json` — Modernized to `next@^16.3.5` with React 19 and Turbopack
[ ] Config: `pyproject.toml` — `[project.scripts]` CLI bindings and `[tool.ruff]` lint configuration
[ ] Package: `next@16.3.5` — Upgraded Next.js framework with native Turbopack compilation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
powershell -Command "Test-Path run_dev.py, tests/integration/test_unified_runners.py, frontend/package.json"
```
✅ Expected: True True True
❌ If missing: Check repository root

Test 2 — Environment / Dependencies:
```
powershell -Command "cd frontend; pnpm list next"
```
✅ Expected: next 16.3.5
❌ If errors: Run `cd frontend; pnpm install --ignore-scripts`

Test 3 — Next.js 16 Turbopack Build Check:
```
powershell -Command "cd frontend; pnpm build"
```
✅ Expected: Compiled successfully with Next.js 16.3.5 (Turbopack)
❌ If errors: Check Next.js build logs in `frontend/.next`

Test 4 — Python Full Test Suite:
```
uv run pytest
```
✅ Expected: 161 passed, 1 skipped
❌ If errors: Run `uv run pytest -v` to locate failing module

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
git commit -m "Interface Upgrade Phase 3: Integration, Next.js 16 Turbopack upgrade & unified CLI runner"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 23 (Production Readiness Check & Final Submission Polish) until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
