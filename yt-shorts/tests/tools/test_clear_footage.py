import json
import pytest
from unittest.mock import patch, MagicMock
from tools.clear_footage import run, strip_audio


def test_strip_audio_returns_true_on_success(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = strip_audio(tmp_path / "in.mp4", tmp_path / "out.mp4")
    assert result is True


def test_strip_audio_returns_false_on_ffmpeg_failure(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        result = strip_audio(tmp_path / "in.mp4", tmp_path / "out.mp4")
    assert result is False


def test_run_strips_all_clips_and_writes_log(project_root):
    footage_dir = project_root / "footage" / "test-job"
    footage_dir.mkdir(parents=True)
    (footage_dir / "clip_00.mp4").write_bytes(b"fake")
    (footage_dir / "clip_01.mp4").write_bytes(b"fake")

    def fake_strip(input_path, output_path):
        output_path.write_bytes(b"stripped")
        return True

    with patch("tools.clear_footage.strip_audio", side_effect=fake_strip):
        log = run("test-job", project_root)

    assert len(log["clips"]) == 2
    assert all(c["status"] == "cleared" for c in log["clips"])
    log_file = project_root / "compliance-logs" / "test-job" / "clearance.json"
    assert log_file.exists()


def test_run_raises_on_any_failure(project_root):
    footage_dir = project_root / "footage" / "test-job"
    footage_dir.mkdir(parents=True)
    (footage_dir / "clip_00.mp4").write_bytes(b"fake")

    with patch("tools.clear_footage.strip_audio", return_value=False):
        with pytest.raises(RuntimeError, match="Audio stripping failed"):
            run("test-job", project_root)
