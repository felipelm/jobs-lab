from opentelemetry import trace
from opentelemetry.context import attach, detach
from opentelemetry.trace import (
    NonRecordingSpan,
    SpanContext,
    TraceFlags,
    set_span_in_context,
)

from packages.common.trace_context import (
    capture_current_trace_context,
    deserialize_trace_context,
    extract_context,
    serialize_trace_context,
)


def test_serialize_trace_context_keeps_only_w3c_headers() -> None:
    serialized = serialize_trace_context(
        {
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
            "tracestate": "vendor=value",
            "ignored": "value",
        }
    )

    assert serialized == {
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "tracestate": "vendor=value",
    }


def test_deserialize_trace_context_normalizes_header_names() -> None:
    deserialized = deserialize_trace_context(
        {
            "TraceParent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        }
    )

    assert deserialized == {
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
    }


def test_extract_context_restores_w3c_span_context() -> None:
    context = extract_context(
        {
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        }
    )

    span_context = trace.get_current_span(context).get_span_context()

    assert span_context.trace_id == int("4bf92f3577b34da6a3ce929d0e0e4736", 16)
    assert span_context.span_id == int("00f067aa0ba902b7", 16)
    assert span_context.trace_flags == TraceFlags(TraceFlags.SAMPLED)


def test_capture_current_trace_context_serializes_current_span() -> None:
    span_context = SpanContext(
        trace_id=int("4bf92f3577b34da6a3ce929d0e0e4736", 16),
        span_id=int("00f067aa0ba902b7", 16),
        is_remote=False,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
        trace_state=[],
    )
    token = attach(set_span_in_context(NonRecordingSpan(span_context)))

    try:
        serialized = capture_current_trace_context()
    finally:
        detach(token)

    assert serialized == {
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
    }
