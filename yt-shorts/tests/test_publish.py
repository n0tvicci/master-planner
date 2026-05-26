import importlib
import json
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _reload_publish(project_root):
    if "publish" in sys.modules:
        del sys.modules["publish"]
    import os
    os.environ["PUBLISH_PROJECT_ROOT"] = str(project_root)
    import publish
    importlib.reload(publish)
    return publish


def _write_final_video(project_root, job_id):
    out_dir = project_root / "output" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "final.mp4").write_bytes(b"fake video")


def _write_metadata(project_root, job_id, meta):
    md_dir = project_root / "metadata" / job_id
    md_dir.mkdir(parents=True, exist_ok=True)
    (md_dir / "metadata.json").write_text(json.dumps(meta))


def _write_state(project_root, job_id, state_data):
    tmp_dir = project_root / ".tmp" / job_id
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / "state.json").write_text(json.dumps(state_data))


# ── Prerequisite guard ────────────────────────────────────────────────────────

def test_missing_final_video_exits_with_error(project_root, monkeypatch):
    publish = _reload_publish(project_root)
    monkeypatch.setattr(sys, "argv", ["publish.py", "--job", "test-job"])
    with pytest.raises(SystemExit) as exc_info:
        publish.main(project_root)
    assert exc_info.value.code == 1


# ── Gate failure ──────────────────────────────────────────────────────────────

def test_gate_failure_exits_nonzero(project_root, monkeypatch, sample_metadata):
    _write_final_video(project_root, "test-job")
    publish = _reload_publish(project_root)
    monkeypatch.setattr(sys, "argv", ["publish.py", "--job", "test-job"])

    with patch("tools.pre_upload_gate.run",
               return_value={"status": "FAIL", "failed_checks": ["Clip count is 22-25?"]}), \
         pytest.raises(SystemExit) as exc_info:
        publish.main(project_root)

    assert exc_info.value.code == 1


# ── Dry run ───────────────────────────────────────────────────────────────────

def test_dry_run_generates_metadata_and_skips_upload(
    project_root, monkeypatch, config, sample_script, sample_metadata, capsys
):
    _write_final_video(project_root, "20260524-test-job")
    publish = _reload_publish(project_root)
    monkeypatch.setattr(sys, "argv", ["publish.py", "--job", "20260524-test-job", "--dry-run"])

    mock_upload = MagicMock()

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.generate_metadata.run", return_value=sample_metadata) as mock_meta, \
         patch("tools.pre_upload_gate.run", return_value={"status": "PASS"}), \
         patch("tools.upload_youtube.run", mock_upload):
        _write_metadata(project_root, "20260524-test-job", sample_metadata)
        publish.main(project_root)

    mock_upload.assert_not_called()
    out = capsys.readouterr().out
    assert "DRY RUN" in out


# ── Upload window ─────────────────────────────────────────────────────────────

def test_outside_upload_window_exits_zero(
    project_root, monkeypatch, config, sample_script, sample_metadata
):
    _write_final_video(project_root, "20260524-test-job")
    _write_metadata(project_root, "20260524-test-job", sample_metadata)
    _write_state(project_root, "20260524-test-job", {
        "job_id": "20260524-test-job",
        "completed_steps": ["pre_upload_gate", "generate_metadata"],
    })
    publish = _reload_publish(project_root)
    monkeypatch.setattr(sys, "argv", ["publish.py", "--job", "20260524-test-job"])

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.upload_youtube.is_in_upload_window", return_value=False), \
         patch("tools.upload_youtube.next_upload_window") as mock_nw, \
         pytest.raises(SystemExit) as exc_info:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        mock_nw.return_value = datetime(2026, 5, 26, 7, 0, tzinfo=ZoneInfo("America/New_York"))
        publish.main(project_root)

    assert exc_info.value.code == 0


def test_immediate_flag_skips_window_check(
    project_root, monkeypatch, config, sample_script, sample_metadata
):
    _write_final_video(project_root, "20260524-test-job")
    _write_metadata(project_root, "20260524-test-job", sample_metadata)
    _write_state(project_root, "20260524-test-job", {
        "job_id": "20260524-test-job",
        "completed_steps": ["pre_upload_gate", "generate_metadata"],
    })
    publish = _reload_publish(project_root)
    monkeypatch.setattr(
        sys, "argv", ["publish.py", "--job", "20260524-test-job", "--immediate"]
    )

    mock_window_check = MagicMock(return_value=False)

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.upload_youtube.is_in_upload_window", mock_window_check), \
         patch("tools.upload_youtube.run",
               return_value={"video_id": "vid123", "url": "https://youtube.com/shorts/vid123"}), \
         patch("tools.monitor_upload.run"):
        publish.main(project_root)

    mock_window_check.assert_not_called()


# ── Happy path ────────────────────────────────────────────────────────────────

def test_happy_path_calls_all_steps_in_order(
    project_root, monkeypatch, config, sample_script, sample_metadata
):
    _write_final_video(project_root, "20260524-test-job")
    publish = _reload_publish(project_root)
    monkeypatch.setattr(
        sys, "argv", ["publish.py", "--job", "20260524-test-job", "--immediate"]
    )

    call_order = []

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.pre_upload_gate.run",
               side_effect=lambda: call_order.append("gate") or {"status": "PASS"}), \
         patch("tools.generate_metadata.run",
               side_effect=lambda *a: (call_order.append("metadata"),
                                       _write_metadata(project_root, "20260524-test-job",
                                                        sample_metadata),
                                       sample_metadata)[2]), \
         patch("tools.upload_youtube.run",
               side_effect=lambda *a: (call_order.append("upload"),
                                       {"video_id": "vid123",
                                        "url": "https://youtube.com/shorts/vid123"})[1]), \
         patch("tools.monitor_upload.run",
               side_effect=lambda *a: call_order.append("monitor")):
        publish.main(project_root)

    assert call_order == ["gate", "metadata", "upload", "monitor"]


# ── Analytics mode ────────────────────────────────────────────────────────────

def test_analytics_flag_calls_pull_analytics(project_root, monkeypatch, config):
    _write_state(project_root, "test-job", {
        "job_id": "test-job",
        "video_id": "vid456",
        "completed_steps": ["pre_upload_gate", "generate_metadata", "upload_youtube",
                            "monitor_upload"],
    })
    publish = _reload_publish(project_root)
    monkeypatch.setattr(sys, "argv", ["publish.py", "--job", "test-job", "--analytics"])

    mock_pull = MagicMock(return_value={
        "flag": "GREEN", "us_share": 0.62, "notes": "US share >50% — target met"
    })

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.pull_analytics.run", mock_pull):
        publish.main(project_root)

    mock_pull.assert_called_once_with("test-job", "vid456", project_root)


def test_analytics_without_video_id_exits(project_root, monkeypatch, config):
    _write_state(project_root, "test-job", {
        "job_id": "test-job",
        "completed_steps": [],
    })
    publish = _reload_publish(project_root)
    monkeypatch.setattr(sys, "argv", ["publish.py", "--job", "test-job", "--analytics"])

    with patch("tools.utils.config.load_config", return_value=config), \
         pytest.raises(SystemExit) as exc_info:
        publish.main(project_root)

    assert exc_info.value.code == 1
