import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_project(tmp_path):
    (tmp_path / "topics").mkdir()
    return tmp_path


@pytest.fixture
def client(tmp_project, monkeypatch):
    monkeypatch.setenv("YT_PROJECT_ROOT", str(tmp_project))
    import importlib
    import backend.config
    importlib.reload(backend.config)
    import backend.routers.topics
    importlib.reload(backend.routers.topics)
    import backend.main
    importlib.reload(backend.main)
    return TestClient(backend.main.app)


def _write(path: Path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def test_get_pending_empty(client, tmp_project):
    r = client.get("/api/v1/topics/pending")
    assert r.status_code == 200
    assert r.json() == []


def test_get_pending_returns_data(client, tmp_project):
    _write(tmp_project / "topics" / "pending.json", [{"id": "abc", "title": "Test"}])
    r = client.get("/api/v1/topics/pending")
    assert r.json()[0]["title"] == "Test"


def test_get_queue_empty(client, tmp_project):
    r = client.get("/api/v1/topics/queue")
    assert r.json() == []


def test_get_published_empty(client, tmp_project):
    r = client.get("/api/v1/topics/published")
    assert r.json() == []


def test_approve_moves_topic_to_queue(client, tmp_project):
    _write(tmp_project / "topics" / "pending.json",
           [{"id": "abc123", "title": "Test Topic", "score": 9}])
    r = client.post("/api/v1/topics/abc123/approve")
    assert r.status_code == 200
    remaining = json.loads((tmp_project / "topics" / "pending.json").read_text())
    assert remaining == []
    queue = json.loads((tmp_project / "topics" / "queue.json").read_text())
    assert queue[0]["title"] == "Test Topic"


def test_approve_unknown_id_returns_404(client, tmp_project):
    _write(tmp_project / "topics" / "pending.json", [])
    assert client.post("/api/v1/topics/notexist/approve").status_code == 404


def test_reject_removes_topic(client, tmp_project):
    _write(tmp_project / "topics" / "pending.json",
           [{"id": "abc123", "title": "Test Topic"}])
    r = client.post("/api/v1/topics/abc123/reject")
    assert r.status_code == 200
    remaining = json.loads((tmp_project / "topics" / "pending.json").read_text())
    assert remaining == []


def test_reject_unknown_id_returns_404(client, tmp_project):
    _write(tmp_project / "topics" / "pending.json", [])
    assert client.post("/api/v1/topics/notexist/reject").status_code == 404
