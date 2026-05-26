import json
import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_project(tmp_path):
    (tmp_path / "compliance-logs").mkdir()
    return tmp_path


@pytest.fixture
def client(tmp_project, monkeypatch):
    monkeypatch.setenv("YT_PROJECT_ROOT", str(tmp_project))
    import importlib
    import backend.config
    importlib.reload(backend.config)
    import backend.routers.analytics
    importlib.reload(backend.routers.analytics)
    import backend.main
    importlib.reload(backend.main)
    from backend.main import app
    return TestClient(app)


def test_get_analytics_not_found_returns_404(client):
    assert client.get("/api/v1/analytics/job-001").status_code == 404


def test_get_analytics_returns_report(client, tmp_project):
    report_dir = tmp_project / "compliance-logs" / "job-001"
    report_dir.mkdir(parents=True)
    (report_dir / "audience-report.json").write_text(
        json.dumps({"us_share": 0.62, "flag": "GREEN"}), encoding="utf-8"
    )
    r = client.get("/api/v1/analytics/job-001")
    assert r.json()["flag"] == "GREEN"


def test_pull_triggers_background_task(client):
    with patch("backend.routers.analytics._launch_analytics") as mock:
        r = client.post("/api/v1/analytics/job-001/pull")
    assert r.status_code == 200
    assert mock.called
