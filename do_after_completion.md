━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP COMPLETION CHECKLIST
# Dynamic Model Resolution via Environment Variable (Zero-UI-Touch)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Run live model invocation test to verify dynamic model resolution:
    ```
    uv run python -c "from dotenv import load_dotenv; load_dotenv(override=True); import asyncio; from src.models import get_model_invoker; inv = get_model_invoker('staging'); res = asyncio.run(inv.invoke_reasoning('State: TX. Clause: Pay when paid.', 'Classify')); print('ACTIVE MODEL RESPONSE:', res[:120])"
    ```
    Expected: Loud terminal banner `[LIVE GEMINI CALL] Model: gemini-3.5-flash-lite` followed by model response in ~2s.

[ ] Verify ModelCatalog unit test passes with default resolution and dynamic overrides:
    ```
    uv run pytest tests/unit/test_models.py
    ```
    Expected: 4 passed in ~0.2s.

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

[ ] Verify Next.js frontend build remains 100% untouched and functional:
    ```
    cd frontend && pnpm build
    ```
    Expected: Compiled successfully with Next.js 16.3.5 (Turbopack).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Start FastAPI Server and Next.js Frontend:
    1. Terminal 1:
       ```
       uv run uvicorn src.server:app --port 8000
       ```
    2. Terminal 2:
       ```
       cd frontend && pnpm dev
       ```
    3. Open `http://localhost:3000` in browser.
    4. Confirm frontend displays `[Gemini 3.8 Flash Staging]` badge (UI untouched).
    5. Run an audit and observe Terminal 1 output: It executes against `gemini-3.5-flash-lite` with loud logging, preserving free-tier request quota (500 RPD).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] Config: `src/models.py` — Decoupled staging model resolution with `ModelCatalog.get_model_id()` dynamically reading `GEMINI_STAGING_MODEL` (default: `"gemini-3.8-flash"`) and `GEMINI_EXECUTION_MODEL`
[ ] Provider: `src/providers/staging_runtime.py` — Target model defaults to `GEMINI_STAGING_MODEL` with automatic 429/503 failover resilience to `gemini-3.1-flash-lite`
[ ] Environment: `.env.example` — Added `GEMINI_STAGING_MODEL` and `GEMINI_EXECUTION_MODEL` configuration templates
[ ] Environment: `.env` — Configured `GEMINI_STAGING_MODEL=gemini-3.5-flash-lite` and `GEMINI_EXECUTION_MODEL=gemini-3.5-flash-lite`
[ ] Tests: `tests/unit/test_models.py` — Added monkeypatch assertions verifying default fallback to `gemini-3.8-flash` when unset and dynamic env resolution when set

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
powershell -Command "Test-Path src/models.py, src/providers/staging_runtime.py, tests/unit/test_models.py"
```
✅ Expected: True, True, True
❌ If missing: Check repository git status

Test 2 — Full Python Test Suite:
```
uv run pytest
```
✅ Expected: 162 passed in pytest
❌ If errors: Run `uv run pytest -v`

Test 3 — Live Dynamic Model Invocation:
```
uv run python -c "from dotenv import load_dotenv; load_dotenv(override=True); import asyncio; from src.models import get_model_invoker; inv = get_model_invoker('staging'); res = asyncio.run(inv.invoke_reasoning('State: TX. Clause: Pay when paid.', 'Classify')); print('ACTIVE MODEL RESPONSE:', res[:120])"
```
✅ Expected: Model `gemini-3.5-flash-lite` invoked and live response printed
❌ If errors: Verify `GEMINI_API_KEY` in `.env`

Test 4 — Static Linting Check:
```
uv run ruff check src tests run_dev.py
```
✅ Expected: All checks passed!
❌ If errors: Run `uv run ruff check --fix src tests run_dev.py`

Test 5 — Security Check:
[ ] Verify .env is in .gitignore:
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
git commit -m "Step: Dynamic Model Resolution via Environment Variable — decoupled model IDs in models.py and staging_runtime.py"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 23: Production Readiness Check until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
