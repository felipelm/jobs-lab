from dataclasses import dataclass
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.metrics import Counter, Histogram
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

SERVICE_NAME_VALUE = "jobs-worker"

_meter_configured = False
_metrics: "WorkerMetrics | None" = None
_tracer_configured = False


@dataclass(frozen=True)
class WorkerMetrics:
    jobs_succeeded_total: Counter
    jobs_failed_total: Counter
    jobs_retried_total: Counter
    job_processing_duration_seconds: Histogram
    queue_depth: Any


def configure_tracing(enabled: bool, otlp_endpoint: str | None) -> None:
    if not enabled:
        return

    _get_or_create_tracer_provider(otlp_endpoint)
    _get_or_create_meter_provider(otlp_endpoint)


def get_tracer() -> trace.Tracer:
    return trace.get_tracer("apps.worker")


def get_metrics() -> WorkerMetrics:
    global _metrics

    if _metrics is None:
        meter = metrics.get_meter("apps.worker")
        _metrics = WorkerMetrics(
            jobs_succeeded_total=meter.create_counter(
                "jobs_succeeded_total",
                description="Total jobs successfully processed by workers",
            ),
            jobs_failed_total=meter.create_counter(
                "jobs_failed_total",
                description="Total jobs permanently failed by workers",
            ),
            jobs_retried_total=meter.create_counter(
                "jobs_retried_total",
                description="Total jobs retried by workers",
            ),
            job_processing_duration_seconds=meter.create_histogram(
                "job_processing_duration_seconds",
                unit="s",
                description="Duration of worker job processing",
            ),
            queue_depth=meter.create_gauge(
                "queue_depth",
                description="Observed Redis job queue depth",
            ),
        )

    return _metrics


def _get_or_create_tracer_provider(otlp_endpoint: str | None) -> TracerProvider:
    global _tracer_configured

    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        return provider

    tracer_provider = TracerProvider(
        resource=Resource.create({SERVICE_NAME: SERVICE_NAME_VALUE})
    )

    if not _tracer_configured and otlp_endpoint:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True))
        )
        trace.set_tracer_provider(tracer_provider)
        _tracer_configured = True

    return tracer_provider


def _get_or_create_meter_provider(otlp_endpoint: str | None) -> MeterProvider | None:
    global _meter_configured

    provider = metrics.get_meter_provider()
    if isinstance(provider, MeterProvider):
        return provider

    if not otlp_endpoint:
        return None

    meter_provider = MeterProvider(
        resource=Resource.create({SERVICE_NAME: SERVICE_NAME_VALUE}),
        metric_readers=[
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True),
                export_interval_millis=5000,
            )
        ],
    )

    if not _meter_configured:
        metrics.set_meter_provider(meter_provider)
        _meter_configured = True

    return meter_provider
