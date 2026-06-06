from fastapi.testclient import TestClient

from apps.api.dependencies import get_job_queue, get_job_repository
from apps.api.main import create_app
from packages.common.database import check_database_readiness
from packages.common.jobs import create_job
from packages.common.models import JobCreateRequest, JobRecord


class FakeJobRepository:
    def __init__(self) -> None:
        self.jobs: dict[str, JobRecord] = {}

    async def create(
        self,
        request: JobCreateRequest,
        trace_context: dict[str, str] | None = None,
    ) -> JobRecord:
        job = create_job(request, trace_context=trace_context)
        self.jobs[job.id] = job
        return job

    async def list(self) -> list[JobRecord]:
        return list(self.jobs.values())

    async def get(self, job_id: str) -> JobRecord | None:
        return self.jobs.get(job_id)


class FakeJobQueue:
    def __init__(self) -> None:
        self.enqueued_job_ids: list[str] = []

    async def enqueue_job_id(self, job_id: str) -> None:
        self.enqueued_job_ids.append(job_id)

    async def dequeue_job_id(self, timeout_seconds: float) -> str | None:
        if not self.enqueued_job_ids:
            return None
        return self.enqueued_job_ids.pop(0)

    async def depth(self) -> int:
        return len(self.enqueued_job_ids)


class ApiTestContext:
    def __init__(self, client: TestClient, queue: FakeJobQueue) -> None:
        self.client = client
        self.queue = queue


def create_test_client(
    ready: bool = True,
) -> ApiTestContext:
    app = create_app()
    repository = FakeJobRepository()
    queue = FakeJobQueue()

    app.dependency_overrides[get_job_repository] = lambda: repository
    app.dependency_overrides[get_job_queue] = lambda: queue
    app.dependency_overrides[check_database_readiness] = lambda: ready

    return ApiTestContext(client=TestClient(app), queue=queue)


def test_health_endpoint() -> None:
    client = create_test_client().client

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "service": "api",
        "status": "ok",
        "environment": "local",
    }


def test_readiness_endpoint() -> None:
    client = create_test_client().client

    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {
        "service": "api",
        "status": "ready",
        "ready": True,
    }


def test_readiness_endpoint_returns_503_when_database_is_unavailable() -> None:
    client = create_test_client(ready=False).client

    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database not ready"}


def test_submit_job() -> None:
    context = create_test_client()
    client = context.client

    response = client.post(
        "/jobs",
        json={
            "type": "email",
            "payload": {"to": "learner@example.com"},
            "max_attempts": 5,
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["type"] == "email"
    assert body["payload"] == {"to": "learner@example.com"}
    assert body["status"] == "queued"
    assert body["attempts"] == 0
    assert body["max_attempts"] == 5
    assert body["error"] is None
    assert "trace_context" not in body
    assert body["id"]
    assert body["created_at"]
    assert body["updated_at"]
    assert context.queue.enqueued_job_ids == [body["id"]]


def test_list_jobs_returns_created_jobs() -> None:
    client = create_test_client().client

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
    client = create_test_client().client
    created = client.post(
        "/jobs",
        json={"type": "email", "payload": {"to": "learner@example.com"}},
    ).json()

    response = client.get(f"/jobs/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_job_returns_404_for_unknown_job() -> None:
    client = create_test_client().client

    response = client.get("/jobs/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
