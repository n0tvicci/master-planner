from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_projects_route_exists():
    response = client.get("/api/yt-shorts/projects")
    assert response.status_code == 200


def test_core_jobs_route_exists():
    response = client.get("/api/core/jobs")
    assert response.status_code == 200


def test_cors_headers():
    response = client.options(
        "/api/yt-shorts/projects",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code in (200, 204)
