━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP COMPLETION CHECKLIST
# Fix Streamlit Cloud Deployment & Align UI with Next.js Console
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Verify Streamlit headless startup with sys.path root resolution:
    ```
    uv run python -c "import sys; from pathlib import Path; root = Path('.').resolve(); sys.path.insert(0, str(root)); from src.agents.graph import build_ironclad_graph; g = build_ironclad_graph(); print('GRAPH BUILT SUCCESSFULLY:', g is not None)"
    ```
    Expected: `GRAPH BUILT SUCCESSFULLY: True`

[ ] Verify Streamlit UI unit and integration tests:
    ```
    uv run pytest tests/unit/test_ui_components.py tests/integration/test_streamlit_app_flow.py
    ```
    Expected: 11 passed in pytest.

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

[ ] Verify root requirements.txt contains essential runtime dependencies:
    ```
    powershell -Command "Select-String -Path requirements.txt -Pattern 'strands-agents', 'google-genai', 'pydantic'"
    ```
    Expected: All three packages matched in requirements.txt.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Push commit to GitHub to trigger automatic Streamlit Cloud rebuild:
    ```
    git add .
    git commit -m "Fix: Streamlit Cloud deployment sys.path resolution, root requirements.txt, and UI parity"
    git push origin main
    ```
    Expected: Streamlit Community Cloud detects git push and rebuilds container successfully.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `src/ui/app.py` — Dynamic `REPO_ROOT` insertion into `sys.path` and automatic `st.secrets` mapping to `os.environ`
[ ] File: `requirements.txt` — Root production dependency manifest for Streamlit Cloud build workers
[ ] Config: `.streamlit/config.toml` — Aligned theme palette (`#0B0F19`, `#111827`, `#3B82F6`, `#F9FAFB`) and headless server configuration
[ ] Feature: Streamlit Cloud Compatibility — Seamless cloud deployment on Streamlit Community Cloud with zero AWS credential dependencies

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
powershell -Command "Test-Path src/ui/app.py, requirements.txt, .streamlit/config.toml"
```
✅ Expected: True, True, True
❌ If missing: Check repository git status

Test 2 — Full Python Test Suite:
```
uv run pytest
```
✅ Expected: 162 passed in pytest
❌ If errors: Run `uv run pytest -v`

Test 3 — UI Flow Tests:
```
uv run pytest tests/unit/test_ui_components.py tests/integration/test_streamlit_app_flow.py
```
✅ Expected: 11 passed
❌ If errors: Inspect failing test assertion

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
📦 GIT COMMIT & PUSH
(Run this ONLY after all above checks pass)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
git add .
git commit -m "Fix: Streamlit Cloud deployment sys.path resolution, root requirements.txt, and UI parity"
git push origin main
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 23: Production Readiness Check until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
