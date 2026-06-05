from fastapi.testclient import TestClient

from apps.api.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "api",
        "status": "ok",
        "environment": "local",
    }


def test_submit_job() -> None:
    client = TestClient(app)

    response = client.post(
        "/jobs",
        json={"kind": "email", "payload": {"to": "learner@example.com"}},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["kind"] == "email"
    assert body["payload"] == {"to": "learner@example.com"}
    assert body["status"] == "queued"
    assert body["id"]
    assert body["created_at"]

