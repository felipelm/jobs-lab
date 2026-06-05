from fastapi.testclient import TestClient

from apps.api.database import check_database_readiness
from apps.api.dependencies import get_job_repository
from apps.api.main import create_app
from packages.common.jobs import create_job
from packages.common.models import JobCreateRequest, JobRecord


class FakeJobRepository:
    def __init__(self) -> None:
        self.jobs: dict[str, JobRecord] = {}

    async def create(self, request: JobCreateRequest) -> JobRecord:
        job = create_job(request)
        self.jobs[job.id] = job
        return job

    async def list(self) -> list[JobRecord]:
        return list(self.jobs.values())

    async def get(self, job_id: str) -> JobRecord | None:
        return self.jobs.get(job_id)


def create_test_client(
    ready: bool = True,
) -> TestClient:
    app = create_app()
    repository = FakeJobRepository()

    app.dependency_overrides[get_job_repository] = lambda: repository
    app.dependency_overrides[check_database_readiness] = lambda: ready

    return TestClient(app)


def test_health_endpoint() -> None:
    client = create_test_client()

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "service": "api",
        "status": "ok",
        "environment": "local",
    }


def test_readiness_endpoint() -> None:
    client = create_test_client()

    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {
        "service": "api",
        "status": "ready",
        "ready": True,
    }


def test_readiness_endpoint_returns_503_when_database_is_unavailable() -> None:
    client = create_test_client(ready=False)

    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database not ready"}


def test_submit_job() -> None:
    client = create_test_client()

    response = client.post(
        "/jobs",
        json={"type": "email", "payload": {"to": "learner@example.com"}},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["type"] == "email"
    assert body["payload"] == {"to": "learner@example.com"}
    assert body["status"] == "queued"
    assert body["id"]
    assert body["created_at"]
    assert body["updated_at"]


def test_list_jobs_returns_created_jobs() -> None:
    client = create_test_client()

    first = client.post(
        "/jobs",
        json={"type": "email", "payload": {"to": "first@example.com"}},
    ).json()
    second = client.post(
        "/jobs",
        json={"type": "report", "payload": {"name": "daily"}},
    ).json()

    response = client.get("/jobs")

    assert response.status_code == 200
    assert [job["id"] for job in response.json()] == [first["id"], second["id"]]


def test_get_job_returns_created_job() -> None:
    client = create_test_client()
    created = client.post(
        "/jobs",
        json={"type": "email", "payload": {"to": "learner@example.com"}},
    ).json()

    response = client.get(f"/jobs/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_job_returns_404_for_unknown_job() -> None:
    client = create_test_client()

    response = client.get("/jobs/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
