import json
import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_project(tmp_path):
    for d in ["output", "metadata", ".tmp"]:
        (tmp_path / d).mkdir()
    return tmp_path


@pytest.fixture
def client(tmp_project, monkeypatch):
    monkeypatch.setenv("YT_PROJECT_ROOT", str(tmp_project))
    import importlib
    import backend.config
    importlib.reload(backend.config)
    import backend.routers.publish
    importlib.reload(backend.routers.publish)
    import backend.main
    importlib.reload(backend.main)
    from backend.main import app
    return TestClient(app)


def test_get_window_returns_shape(client):
    r = client.get("/api/v1/publish/window")
    assert r.status_code == 200
    data = r.json()
    assert "in_window" in data
    assert isinstance(data["in_window"], bool)
    assert "next_window" in data


def test_get_metadata_not_found_returns_404(client, tmp_project):
    assert client.get("/api/v1/publish/job-001/metadata").status_code == 404


def test_get_metadata_returns_data(client, tmp_project):
    meta_dir = tmp_project / "metadata" / "job-001"
    meta_dir.mkdir(parents=True)
    (meta_dir / "metadata.json").write_text(json.dumps({"title": "Test"}), encoding="utf-8")
    r = client.get("/api/v1/publish/job-001/metadata")
    assert r.json()["title"] == "Test"


def test_upload_missing_final_mp4_returns_400(client, tmp_project):
    r = client.post("/api/v1/publish/job-001/upload")
    assert r.status_code == 400
    assert "final.mp4" in r.json()["detail"]


def test_upload_writes_gate_to_state(client, tmp_project):
    job_id = "job-001"
    (tmp_project / "output" / job_id).mkdir(parents=True)
    (tmp_project / "output" / job_id / "final.mp4").touch()
    tmp_dir = tmp_project / ".tmp" / job_id
    tmp_dir.mkdir(parents=True)
    (tmp_dir / "state.json").write_text(
        json.dumps({"job_id": job_id, "completed_steps": []}), encoding="utf-8"
    )
    with patch("backend.routers.publish._launch_publish"):
        r = client.post(f"/api/v1/publish/{job_id}/upload")
    assert r.status_code == 200
    state = json.loads((tmp_dir / "state.json").read_text())
    assert "pre_upload_gate" in state["completed_steps"]
