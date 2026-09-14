---
trigger: always_on
---

When implementing `strands-agents`, `bedrock-agentcore`, and model providers, you must NEVER assume package submodules, function decorators, or class names from memory:

1. **Introspect Before Import:**
   - Immediately after running `uv sync` in Step 2, verify installed packages via terminal checks:
     `python -c "import strands; print(dir(strands))"`
     `python -c "import google.genai; print(dir(google.genai))"`
   - Never write speculative import paths like `from strands.multiagent import ...` or `from bedrock_agentcore.runtime import ...` without confirming their existence in the installed package first.

2. **Multi-Agent Topology Implementation:**
   - If the installed `strands-agents` package exposes a native graph/DAG builder, inspect its exact signature before using it.
   - If multi-agent coordination in the installed Strands version is agent-based or pipeline-based, build a clean, typed async orchestrator in `src/agents/graph.py` that executes the Tri-Track DAG flow (`ForensicAuditSentinel` || `FairPayStatutoryGuardian` -> `EverydayDecisionCardEmitter`).

3. **Google GenAI Staging Runtime:**
   - Use strictly the modern official `google-genai` SDK (`from google import genai` and `from google.genai import types`).
   - Model identifier: `gemini-3.8-flash`.
   - Always read `GEMINI_API_KEY` from environment variables.

4. **Lazy Boto3 Loading in `bedrock_runtime.py`:**
   - All AWS SDK (`boto3`, Bedrock client) calls must be initialized lazily inside class methods, never at module root.
   - Importing `src.providers.bedrock_runtime` in environments without AWS credentials must never raise an `ImportError` or fail at startup.