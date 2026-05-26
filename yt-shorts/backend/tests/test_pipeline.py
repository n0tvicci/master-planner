import json
import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_project(tmp_path):
    (tmp_path / ".tmp").mkdir()
    (tmp_path / "topics").mkdir()
    return tmp_path


@pytest.fixture
def client(tmp_project, monkeypatch):
    monkeypatch.setenv("YT_PROJECT_ROOT", str(tmp_project))
    import importlib
    import backend.config
    importlib.reload(backend.config)
    import backend.routers.pipeline
    importlib.reload(backend.routers.pipeline)
    import backend.main
    importlib.reload(backend.main)
    from backend.main import app
    return TestClient(app)


def _write_state(root: Path, job_id: str, state: dict):
    job_dir = root / ".tmp" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")


def test_get_jobs_empty(client, tmp_project):
    assert client.get("/api/v1/pipeline/jobs").json() == []


def test_get_jobs_lists_existing_jobs(client, tmp_project):
    _write_state(tmp_project, "job-001", {"job_id": "job-001", "completed_steps": []})
    jobs = client.get("/api/v1/pipeline/jobs").json()
    assert any(j["job_id"] == "job-001" for j in jobs)


def test_get_state_returns_state(client, tmp_project):
    _write_state(tmp_project, "job-001", {"job_id": "job-001", "completed_steps": ["generate_script"]})
    r = client.get("/api/v1/pipeline/job-001/state")
    assert r.status_code == 200
    assert r.json()["completed_steps"] == ["generate_script"]


def test_get_state_missing_returns_404(client, tmp_project):
    assert client.get("/api/v1/pipeline/missing/state").status_code == 404


def test_run_returns_job_id(client, tmp_project):
    queue = [{"id": "t1", "title": "Test Topic", "score": 9}]
    (tmp_project / "topics" / "queue.json").write_text(json.dumps(queue), encoding="utf-8")
    with patch("backend.routers.pipeline._launch_pipeline"):
        r = client.post("/api/v1/pipeline/run")
    assert r.status_code == 200
    assert "job_id" in r.json()


def test_run_empty_queue_returns_400(client, tmp_project):
    (tmp_project / "topics" / "queue.json").write_text("[]", encoding="utf-8")
    r = client.post("/api/v1/pipeline/run")
    assert r.status_code == 400
    assert "empty" in r.json()["detail"].lower()
