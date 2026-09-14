━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP COMPLETION CHECKLIST
# Live Gemini 3.8 Flash Invocation & Loud Telemetry Verification
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Run live Google GenAI model invocation test to verify genuine Gemini 3.8 Flash inference:
    ```
    uv run python -c "import asyncio, os; from dotenv import load_dotenv; load_dotenv(override=True); from src.models import get_model_invoker; invoker = get_model_invoker('staging'); res = asyncio.run(invoker.invoke_reasoning('State: TX. Subcontract clause: Payment is conditioned upon Owner payment.', 'Classify this clause.', 'gemini-3.8-flash')); print('LIVE RESPONSE:', res[:120])"
    ```
    Expected: Output shows loud terminal banner `[LIVE GEMINI CALL]` with model `gemini-3.8-flash` followed by live legal analysis text.

[ ] Verify FastAPI server health endpoint reports staging mode:
    ```
    uv run python -c "from fastapi.testclient import TestClient; from src.server import app; client = TestClient(app); print(client.get('/api/health').json())"
    ```
    Expected: `{'status': 'Healthy', ..., 'runtime_mode': 'staging', ...}`

[ ] Run full regression test suite (162 tests):
    ```
    uv run pytest
    ```
    Expected: 162 passed in pytest with zero failures.

[ ] Run linter:
    ```
    uv run ruff check src tests run_dev.py
    ```
    Expected: `All checks passed!`

[ ] Verify Next.js Turbopack production build:
    ```
    cd frontend && pnpm build
    ```
    Expected: Compiled successfully with Next.js 16.3.5 (Turbopack) in ~1s.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Start FastAPI Server and observe loud console logging during live audit:
    1. In Terminal 1 (FastAPI backend):
       ```
       uv run uvicorn src.server:app --port 8000
       ```
    2. In Terminal 2 (Next.js frontend):
       ```
       cd frontend && pnpm dev
       ```
    3. Open `http://localhost:3000` in browser.
    4. Click "Run Compliance Audit" on the Simple Clean or Complex Defect scenario.
    5. Observe the Terminal 1 console: It will print high-visibility banners:
       `============================================================`
       `[LIVE GEMINI CALL] Sending request to Google GenAI...`
       `Model: gemini-3.8-flash`
       `Prompt Preview: ...`
       `Duration: ...s`
       `Response Content: ...`
       `============================================================`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `src/server.py` — Instantiated `invoker = get_model_invoker(active_mode)` and passed it into `graph.execute(...)` for all live SSE audit runs
[ ] File: `src/providers/staging_runtime.py` — Loud terminal banners for model ID, latency, prompt and response previews; Windows cp1252 `_safe_log` encoding protections; automatic `gemini-3.6-flash` failover resilience on transient 503/429 errors
[ ] File: `src/agents/fair_pay_statutory_guardian.py` — Loud console indicators before LLM rider classification and inside fallback blocks
[ ] Feature: Live LLM Verification — Verified end-to-end multi-agent DAG inference running against Google Gemini 3.8 Flash with 100% test suite pass rate

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
powershell -Command "Test-Path src/server.py, src/providers/staging_runtime.py, src/agents/fair_pay_statutory_guardian.py"
```
✅ Expected: True, True, True
❌ If missing: Check repository git status

Test 2 — Full Python Test Suite:
```
uv run pytest
```
✅ Expected: 162 passed in pytest
❌ If errors: Run `uv run pytest -v` to inspect failing assertion

Test 3 — Live Gemini 3.8 Flash Standalone Invocation:
```
uv run python -c "import asyncio; from src.models import get_model_invoker; inv = get_model_invoker('staging'); print(asyncio.run(inv.invoke_reasoning('TX pay-if-paid check', 'Classify', 'gemini-3.8-flash'))[:80])"
```
✅ Expected: Live model text returned with loud terminal banners
❌ If errors: Verify `GEMINI_API_KEY` is set in `.env`

Test 4 — Static Linting Check:
```
uv run ruff check src tests run_dev.py
```
✅ Expected: All checks passed!
❌ If errors: Run `uv run ruff check --fix src tests run_dev.py`

Test 5 — Security Check:
[ ] Verify .env is in .gitignore
    ```
    powershell -Command "Select-String -Path .gitignore -Pattern '.env'"
    ```
    ✅ Expected: `.env` appears in the output
    ❌ If missing: Add `.env` to `.gitignore` immediately

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 GIT COMMIT
(Run this ONLY after all above checks pass)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
git add .
git commit -m "Step: Live Gemini 3.8 Flash Invocation & Loud Telemetry Verification — wired active invoker and safe terminal logging"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 23: Production Readiness Check until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
