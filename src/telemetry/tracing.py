"""OpenTelemetry dual-exporter instrumentation and GenAI semantic tracing."""

from __future__ import annotations

import os
import time
from collections.abc import AsyncIterator, Iterator, Sequence
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.trace import Span, Status, StatusCode

# OpenTelemetry GenAI Semantic Convention attribute keys (Development Specification)
GEN_AI_PROVIDER_NAME = "gen_ai.provider.name"
GEN_AI_OPERATION_NAME = "gen_ai.operation.name"
GEN_AI_REQUEST_MODEL = "gen_ai.request.model"
GEN_AI_RESPONSE_MODEL = "gen_ai.response.model"
GEN_AI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GEN_AI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
SESSION_ID_ATTR = "session.id"
PROJECT_ID_ATTR = "ironclad.project_id"
SUBCONTRACTOR_ID_ATTR = "ironclad.subcontractor_id"
DRAW_NUMBER_ATTR = "ironclad.draw_number"
NODE_NAME_ATTR = "ironclad.node_name"
TOOL_NAME_ATTR = "ironclad.tool_name"


class InMemorySpanExporter(SpanExporter):
    """In-memory OpenTelemetry span exporter for hermetic testing and audit inspection."""

    def __init__(self) -> None:
        self.spans: list[ReadableSpan] = []

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        self.spans.clear()

    def clear(self) -> None:
        self.spans.clear()


class TelemetryManager:
    """Manages OpenTelemetry tracing, dual-export pipelines, and in-memory trace capture."""

    _instance: TelemetryManager | None = None

    def __init__(self) -> None:
        self.in_memory_exporter = InMemorySpanExporter()
        self.provider = TracerProvider()
        self.provider.add_span_processor(SimpleSpanProcessor(self.in_memory_exporter))
        self.tracer = self.provider.get_tracer("ironclad.sentinel", "1.0.0")

    @classmethod
    def get_instance(cls) -> TelemetryManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def get_tracer(self, name: str = "ironclad.sentinel") -> trace.Tracer:
        return self.provider.get_tracer(name, "1.0.0")

    def get_exported_spans(self) -> list[ReadableSpan]:
        return list(self.in_memory_exporter.spans)

    def clear_exported_spans(self) -> None:
        self.in_memory_exporter.clear()

    def get_span_hierarchy(self) -> list[dict[str, Any]]:
        """Returns recorded spans formatted as structured dictionary records."""
        records: list[dict[str, Any]] = []
        for span in self.in_memory_exporter.spans:
            parent_id = None
            if span.parent and span.parent.span_id:
                parent_id = f"{span.parent.span_id:016x}"

            span_id = f"{span.context.span_id:016x}"
            trace_id = f"{span.context.trace_id:032x}"

            records.append(
                {
                    "name": span.name,
                    "span_id": span_id,
                    "parent_id": parent_id,
                    "trace_id": trace_id,
                    "attributes": dict(span.attributes or {}),
                    "status": span.status.status_code.name if span.status else "UNSET",
                    "duration_ns": (span.end_time or 0) - (span.start_time or 0),
                }
            )
        return records


def get_telemetry_manager() -> TelemetryManager:
    return TelemetryManager.get_instance()


def get_tracer(name: str = "ironclad.sentinel") -> trace.Tracer:
    return get_telemetry_manager().get_tracer(name)


@contextmanager
def trace_audit_run(
    session_id: str,
    project_id: str = "",
    subcontractor_id: str = "",
    draw_number: int = 1,
) -> Iterator[Span]:
    """Root trace span for an autonomous draw-packet audit run."""
    tracer = get_tracer()
    with tracer.start_as_current_span(
        f"audit_run:{session_id}",
        attributes={
            GEN_AI_OPERATION_NAME: "audit_run",
            SESSION_ID_ATTR: session_id,
            PROJECT_ID_ATTR: project_id,
            SUBCONTRACTOR_ID_ATTR: subcontractor_id,
            DRAW_NUMBER_ATTR: draw_number,
        },
    ) as span:
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise


@asynccontextmanager
async def trace_agent_invocation(
    agent_name: str,
    session_id: str = "",
) -> AsyncIterator[Span]:
    """Per-node invoke_agent span conforming to GenAI Semantic Conventions."""
    tracer = get_tracer()
    runtime_mode = os.getenv("IRONCLAD_RUNTIME_MODE", "mock").lower()
    provider_name = "aws.bedrock" if runtime_mode == "bedrock" else ("google.genai" if runtime_mode == "staging" else "mock")

    with tracer.start_as_current_span(
        f"invoke_agent:{agent_name}",
        attributes={
            GEN_AI_OPERATION_NAME: "invoke_agent",
            GEN_AI_PROVIDER_NAME: provider_name,
            NODE_NAME_ATTR: agent_name,
            SESSION_ID_ATTR: session_id,
        },
    ) as span:
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise


@contextmanager
def trace_tool_execution(
    tool_name: str,
    input_digest: dict[str, Any] | None = None,
) -> Iterator[Span]:
    """Tool execution span under a node span conforming to GenAI Semantic Conventions."""
    tracer = get_tracer()
    attrs: dict[str, Any] = {
        GEN_AI_OPERATION_NAME: "execute_tool",
        TOOL_NAME_ATTR: tool_name,
    }
    with tracer.start_as_current_span(f"execute_tool:{tool_name}", attributes=attrs) as span:
        start_t = time.perf_counter()
        try:
            if input_digest:
                # Privacy rule: Add summary keys to events rather than full prompt attributes
                span.add_event(
                    "tool_input_digest",
                    attributes={f"input.{k}": str(v)[:100] for k, v in input_digest.items()},
                )
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise
        finally:
            duration_ms = (time.perf_counter() - start_t) * 1000.0
            span.set_attribute("tool.duration_ms", duration_ms)


@contextmanager
def trace_model_inference(
    model_id: str,
    provider_name: str = "mock",
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> Iterator[Span]:
    """Model inference child span capturing token usage and latency."""
    tracer = get_tracer()
    with tracer.start_as_current_span(
        f"inference:{model_id}",
        attributes={
            GEN_AI_OPERATION_NAME: "inference",
            GEN_AI_PROVIDER_NAME: provider_name,
            GEN_AI_REQUEST_MODEL: model_id,
            GEN_AI_USAGE_INPUT_TOKENS: input_tokens,
            GEN_AI_USAGE_OUTPUT_TOKENS: output_tokens,
        },
    ) as span:
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise
