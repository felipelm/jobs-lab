from collections.abc import Mapping
from typing import Any

from opentelemetry import propagate
from opentelemetry.context import Context

TRACE_CONTEXT_KEYS = {"traceparent", "tracestate"}


def capture_current_trace_context() -> dict[str, str]:
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    return serialize_trace_context(carrier)


def serialize_trace_context(carrier: Mapping[str, Any] | None) -> dict[str, str]:
    if carrier is None:
        return {}

    return {
        key.lower(): str(value)
        for key, value in carrier.items()
        if key.lower() in TRACE_CONTEXT_KEYS and value is not None
    }


def deserialize_trace_context(
    trace_context: Mapping[str, Any] | None,
) -> dict[str, str]:
    return serialize_trace_context(trace_context)


def extract_context(trace_context: Mapping[str, Any] | None) -> Context:
    return propagate.extract(deserialize_trace_context(trace_context))
