import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.core.store import ProjectStore, get_store
from backend.features.yt_shorts.routers.projects import router


@pytest.fixture
def client(tmp_path):
    app = FastAPI()
    app.include_router(router, prefix="/projects")

    def override_store():
        return ProjectStore(base_dir=str(tmp_path))

    app.dependency_overrides[get_store] = override_store
    return TestClient(app)


def test_create_project(client):
    response = client.post("/projects", json={"title": "My Video"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My Video"
    assert data["current_step"] == "topics"
    assert "id" in data
    assert "created_at" in data


def test_create_project_missing_title(client):
    response = client.post("/projects", json={})
    assert response.status_code == 422


def test_list_projects_empty(client):
    response = client.get("/projects")
    assert response.status_code == 200
    assert response.json() == []


def test_list_projects_returns_created(client):
    client.post("/projects", json={"title": "Video 1"})
    client.post("/projects", json={"title": "Video 2"})
    response = client.get("/projects")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_project(client):
    create_resp = client.post("/projects", json={"title": "My Video"})
    project_id = create_resp.json()["id"]
    response = client.get(f"/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["id"] == project_id


def test_get_missing_project(client):
    response = client.get("/projects/nonexistent-id")
    assert response.status_code == 404
