---
trigger: always_on
---

You MUST strictly adhere to the authorized IRONCLAD technology stack:

* **Orchestration Framework:** AWS Strands Agents SDK (`strands-agents==1.42.0`) using multi-agent `GraphBuilder` DAG with typed state transitions.

* **Production Target Runtime:** Amazon Bedrock AgentCore Runtime (`bedrock-agentcore`, `@app.entrypoint`, `agentcore.yaml`).
  - Production models: Claude Sonnet 5 (Reasoning) & Claude Haiku 4.5 (Execution) via Bedrock model access.
  - `src/providers/bedrock_runtime.py` MUST use lazy `boto3` client initialization inside methods, never at module root.

* **Live Staging & Demo Runtime:** Google Gemini 3.8 Flash (`gemini-3.8-flash`) via the modern official `google-genai` SDK (`from google import genai`), reading `GEMINI_API_KEY` from environment. Used for 100% free-tier public demo uptime on Streamlit Community Cloud without requiring AWS IAM credentials.

* **Local Test Double:** Hermetic offline JSON fixture mock (`src/providers/mock_runtime.py`) consuming `tests/mocks/` for instantaneous unit tests without network calls.

* **Backend & State Schemas:** Python 3.11+, Pydantic V2 (`pydantic>=2.9,<2.12`), async-first (`asyncio`).

* **Frontend Interface:** Streamlit (`streamlit`), implementing a Zero-Chat 1-Click Executive Decision Card (`src/ui/app.py`) with expandable audit trail.

* **Telemetry & Tracing:** OpenTelemetry API/SDK (`strands-agents[otel]`) dual-exported to AWS CloudWatch (`bedrock-agentcore` namespace) and Langfuse (`langfuse==4.15.2`).

* **Package & Dependency Management:** `uv` managing `pyproject.toml`.

UNDER NO CIRCUMSTANCES should you write code importing unauthorized or conflicting libraries (e.g., LangGraph, CrewAI, AutoGen, legacy LangChain `AgentExecutor`, legacy `google-generativeai`, synchronous `requests`, or raw `while True` uncheckpointed loops).