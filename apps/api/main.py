from fastapi import FastAPI, HTTPException, status

from apps.api.store import InMemoryJobStore
from packages.common.config import get_settings
from packages.common.jobs import create_job
from packages.common.models import (
    HealthResponse,
    JobCreateRequest,
    JobRecord,
    ReadinessResponse,
)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    job_store = InMemoryJobStore()

    @app.get("/healthz", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            service="api",
            status="ok",
            environment=settings.environment,
        )

    @app.get("/readyz", response_model=ReadinessResponse)
    def readiness() -> ReadinessResponse:
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
    def submit_job(request: JobCreateRequest) -> JobRecord:
        return job_store.add(create_job(request))

    @app.get("/jobs", response_model=list[JobRecord])
    def list_jobs() -> list[JobRecord]:
        return job_store.list()

    @app.get("/jobs/{job_id}", response_model=JobRecord)
    def get_job(job_id: str) -> JobRecord:
        job = job_store.get(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found",
            )
        return job

    return app


app = create_app()
