---
trigger: always_on
---

All backend Python code must be 100% type-hinted with Pydantic V2 models and use non-blocking `async`/`await` for all I/O operations (Strands graph node transitions, Bedrock AgentCore session checkpointing / SQLite access, MCP tool calls, and LLM invocations).

Synchronous blocking I/O (`requests`, synchronous `boto3` calls, `time.sleep`) is strictly prohibited in agent nodes and tools.

Provider Call Mandates:
- Staging model calls to Google GenAI MUST use the modern official `google-genai` SDK with non-blocking async execution:
  `await client.aio.models.generate_content(...)`
- Production `bedrock_runtime.py` must implement lazy initialization of `boto3` clients inside methods so that module loading never fails when AWS credentials are absent in local or staging environments.

Pydantic V2 Strict Validation:
- All state models (`IroncladState`, `DrawPacketMeta`, `LineItem`, `LienWaiverRecord`, `RetainageAuditResult`, `StatutoryClock`, `Discrepancy`, `DecisionCardPayload`) must use strict Pydantic V2 definitions with field descriptions.
- Use explicit validation before and after tool calls:
  `model_config = ConfigDict(extra="forbid")` (or `extra="ignore"` where forward compatibility is required).

Never parse invoice sums, retainage percentages, notary dates, or statutory countdowns using manual string slicing or brittle regex.