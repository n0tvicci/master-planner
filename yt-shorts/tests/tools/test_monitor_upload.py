import json
import pytest
from tools.utils.state import load_state
import tools.monitor_upload as monitor_upload


def test_run_prints_video_url(project_root, capsys):
    monitor_upload.run("test-job", "vid123", "Why Snipers Avoid Lasers", project_root)
    out = capsys.readouterr().out
    assert "vid123" in out
    assert "youtube.com/shorts/vid123" in out


def test_run_prints_24h_48h_72h_checkpoints(project_root, capsys):
    monitor_upload.run("test-job", "vid123", "Test Title", project_root)
    out = capsys.readouterr().out
    assert "24h" in out
    assert "48h" in out
    assert "72h" in out


def test_run_writes_uploaded_at_to_state(project_root):
    monitor_upload.run("test-job", "vid123", "Test Title", project_root)
    state = load_state("test-job", project_root)
    assert "uploaded_at" in state
    assert state["uploaded_at"]  # non-empty string


def test_run_prints_analytics_command(project_root, capsys):
    monitor_upload.run("test-job", "vid123", "Test Title", project_root)
    out = capsys.readouterr().out
    assert "--analytics" in out
    assert "test-job" in out
