from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.routers.core import router
from backend.core.jobs import job_manager


def test_list_jobs_empty():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    response = client.get("/core/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_jobs_returns_created():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    job_manager.create("yt_shorts", "proj-1", "topics")
    response = client.get("/core/jobs")
    assert response.status_code == 200
    jobs = response.json()
    assert any(j["feature"] == "yt_shorts" for j in jobs)
