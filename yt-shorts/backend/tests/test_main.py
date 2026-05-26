from fastapi.testclient import TestClient


def test_health_returns_ok():
    from backend.main import app
    client = TestClient(app)
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_cors_header_present():
    from backend.main import app
    client = TestClient(app)
    r = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
