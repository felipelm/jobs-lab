from fastapi.testclient import TestClient

from apps.api.main import create_app


def test_health_endpoint() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "service": "api",
        "status": "ok",
        "environment": "local",
    }


def test_readiness_endpoint() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {
        "service": "api",
        "status": "ready",
        "ready": True,
    }


def test_submit_job() -> None:
    app = create_app()
    client = TestClient(app)

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
    app = create_app()
    client = TestClient(app)

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
    app = create_app()
    client = TestClient(app)
    created = client.post(
        "/jobs",
        json={"type": "email", "payload": {"to": "learner@example.com"}},
    ).json()

    response = client.get(f"/jobs/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_job_returns_404_for_unknown_job() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/jobs/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
