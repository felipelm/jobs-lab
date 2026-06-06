from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status

from apps.api.dependencies import get_job_queue, get_job_repository
from apps.api.telemetry import configure_tracing, get_tracer
from packages.common.config import get_settings
from packages.common.database import check_database_readiness
from packages.common.models import (
    HealthResponse,
    JobCreateRequest,
    JobRecord,
    ReadinessResponse,
)
from packages.common.queue import JobQueue
from packages.common.repository import JobRepository
from packages.common.trace_context import capture_current_trace_context


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    configure_tracing(
        app,
        enabled=settings.otel_enabled,
        otlp_endpoint=settings.otel_exporter_otlp_endpoint,
    )
    tracer = get_tracer()

    @app.get("/healthz", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            service="api",
            status="ok",
            environment=settings.environment,
        )

    @app.get("/readyz", response_model=ReadinessResponse)
    async def readiness(
        ready: Annotated[bool, Depends(check_database_readiness)],
    ) -> ReadinessResponse:
        if not ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not ready",
            )

        return ReadinessResponse(
            service="api",
            status="ready",
            ready=True,
        )

    @app.post(
        "/jobs",
        response_model=JobRecord,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def submit_job(
        request: JobCreateRequest,
        repository: Annotated[JobRepository, Depends(get_job_repository)],
        queue: Annotated[JobQueue, Depends(get_job_queue)],
    ) -> JobRecord:
        with tracer.start_as_current_span("create_job") as span:
            try:
                trace_context = capture_current_trace_context()
                job = await repository.create(request, trace_context=trace_context)
            except Exception as exc:
                span.record_exception(exc)
                raise

            span.set_attribute("job.id", job.id)
            span.set_attribute("job.type", job.type)

        with tracer.start_as_current_span("enqueue_job") as span:
            span.set_attribute("job.id", job.id)
            span.set_attribute("job.type", job.type)
            try:
                await queue.enqueue_job_id(job.id)
            except Exception as exc:
                span.record_exception(exc)
                raise

        return job

    @app.get("/jobs", response_model=list[JobRecord])
    async def list_jobs(
        repository: Annotated[JobRepository, Depends(get_job_repository)],
    ) -> list[JobRecord]:
        return await repository.list()

    @app.get("/jobs/{job_id}", response_model=JobRecord)
    async def get_job(
        job_id: str,
        repository: Annotated[JobRepository, Depends(get_job_repository)],
    ) -> JobRecord:
        job = await repository.get(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found",
            )
        return job

    return app


app = create_app()
