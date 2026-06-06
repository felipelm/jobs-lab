from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

SERVICE_NAME_VALUE = "jobs-api"

_configured = False


def configure_tracing(
    app: FastAPI,
    enabled: bool,
    otlp_endpoint: str | None,
) -> None:
    if not enabled:
        return

    tracer_provider = _get_or_create_tracer_provider(otlp_endpoint)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)


def get_tracer() -> trace.Tracer:
    return trace.get_tracer("apps.api")


def _get_or_create_tracer_provider(otlp_endpoint: str | None) -> TracerProvider:
    global _configured

    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        return provider

    tracer_provider = TracerProvider(
        resource=Resource.create({SERVICE_NAME: SERVICE_NAME_VALUE})
    )

    if not _configured:
        if otlp_endpoint:
            tracer_provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
                )
            )
        else:
            tracer_provider.add_span_processor(
                SimpleSpanProcessor(ConsoleSpanExporter())
            )
        trace.set_tracer_provider(tracer_provider)
        _configured = True

    return tracer_provider
