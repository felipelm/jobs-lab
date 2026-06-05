from fastapi import FastAPI, status

from packages.common.config import get_settings
from packages.common.jobs import create_job
from packages.common.models import HealthResponse, JobCreateRequest, JobRecord


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            service="api",
            status="ok",
            environment=settings.environment,
        )

    @app.post(
        "/jobs",
        response_model=JobRecord,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def submit_job(request: JobCreateRequest) -> JobRecord:
        return create_job(request)

    return app


app = create_app()

