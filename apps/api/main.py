from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status

from apps.api.dependencies import get_job_queue, get_job_repository
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


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

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
        job = await repository.create(request)
        await queue.enqueue_job_id(job.id)
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
