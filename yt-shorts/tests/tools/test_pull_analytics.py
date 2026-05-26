import json
import pytest
from unittest.mock import MagicMock, patch
import tools.pull_analytics as pull_analytics


def _mock_analytics_response(rows):
    mock_resp = {"rows": rows, "columnHeaders": [{"name": "country"}, {"name": "views"}]}
    mock_client = MagicMock()
    mock_client.reports.return_value.query.return_value.execute.return_value = mock_resp
    return mock_client


def test_run_writes_green_report(project_root):
    rows = [["US", 600], ["CA", 200], ["GB", 200]]
    mock_client = _mock_analytics_response(rows)
    with patch("tools.pull_analytics.get_analytics_client", return_value=mock_client):
        report = pull_analytics.run("test-job", "vid123", project_root)
    assert report["flag"] == "GREEN"
    assert report["us_share"] == pytest.approx(0.6)
    assert (project_root / "compliance-logs" / "test-job" / "audience-report.json").exists()


def test_run_writes_yellow_report(project_root):
    rows = [["US", 450], ["IN", 300], ["CA", 250]]
    mock_client = _mock_analytics_response(rows)
    with patch("tools.pull_analytics.get_analytics_client", return_value=mock_client):
        report = pull_analytics.run("test-job", "vid123", project_root)
    assert report["flag"] == "YELLOW"
    assert 0.4 <= report["us_share"] <= 0.5


def test_run_writes_red_report(project_root):
    rows = [["IN", 700], ["US", 150], ["PH", 150]]
    mock_client = _mock_analytics_response(rows)
    with patch("tools.pull_analytics.get_analytics_client", return_value=mock_client):
        report = pull_analytics.run("test-job", "vid123", project_root)
    assert report["flag"] == "RED"
    assert report["us_share"] < 0.4


def test_run_handles_no_views_returns_red(project_root):
    mock_client = _mock_analytics_response([])
    with patch("tools.pull_analytics.get_analytics_client", return_value=mock_client):
        report = pull_analytics.run("test-job", "vid123", project_root)
    assert report["flag"] == "RED"
    assert report["us_share"] == 0.0


def test_run_report_json_saved_correctly(project_root):
    rows = [["US", 800], ["CA", 200]]
    mock_client = _mock_analytics_response(rows)
    with patch("tools.pull_analytics.get_analytics_client", return_value=mock_client):
        pull_analytics.run("test-job", "vid123", project_root)
    saved = json.loads(
        (project_root / "compliance-logs" / "test-job" / "audience-report.json").read_text()
    )
    assert saved["video_id"] == "vid123"
    assert saved["job_id"] == "test-job"
    assert "pulled_at" in saved
    assert saved["country_breakdown"]["US"] == 800
