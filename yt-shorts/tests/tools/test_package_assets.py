import pytest
from unittest.mock import MagicMock, patch
from tools.package_assets import run


def add_footage(project_root, job_id, count=2):
    d = project_root / "footage" / job_id
    d.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (d / f"clip_{i:02d}.mp4").write_bytes(b"clip")


def add_voiceover(project_root, job_id):
    d = project_root / "voiceover" / job_id
    d.mkdir(parents=True)
    (d / "voiceover.mp3").write_bytes(b"audio")


def add_music(project_root, job_id):
    d = project_root / "assets" / job_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "music.mp3").write_bytes(b"music")


def test_run_copies_clips_numbered(project_root, sample_script):
    add_footage(project_root, "20260524-test-job", count=2)
    add_voiceover(project_root, "20260524-test-job")
    add_music(project_root, "20260524-test-job")

    run("20260524-test-job", project_root)

    assets = project_root / "assets" / "20260524-test-job"
    assert (assets / "01_clip.mp4").exists()
    assert (assets / "02_clip.mp4").exists()


def test_run_copies_voiceover(project_root, sample_script):
    add_footage(project_root, "20260524-test-job", count=2)
    add_voiceover(project_root, "20260524-test-job")
    add_music(project_root, "20260524-test-job")

    run("20260524-test-job", project_root)

    assert (project_root / "assets" / "20260524-test-job" / "voiceover.mp3").exists()


def test_run_writes_script_txt(project_root, sample_script):
    add_footage(project_root, "20260524-test-job", count=2)
    add_voiceover(project_root, "20260524-test-job")
    add_music(project_root, "20260524-test-job")

    run("20260524-test-job", project_root)

    script_txt = project_root / "assets" / "20260524-test-job" / "script.txt"
    assert script_txt.exists()
    content = script_txt.read_text()
    assert "You've seen them" in content


def test_run_writes_overlays_with_timestamps_and_color_pops(project_root, sample_script):
    add_footage(project_root, "20260524-test-job", count=2)
    add_voiceover(project_root, "20260524-test-job")
    add_music(project_root, "20260524-test-job")

    run("20260524-test-job", project_root)

    overlays = (project_root / "assets" / "20260524-test-job" / "overlays.txt").read_text()
    assert "[0:00]" in overlays
    assert "EVERY MOVIE" in overlays
    assert "color pop" in overlays  # color pop hint included


def test_run_writes_music_timing_and_loop_files(project_root, sample_script):
    add_footage(project_root, "20260524-test-job", count=2)
    add_voiceover(project_root, "20260524-test-job")
    add_music(project_root, "20260524-test-job")

    run("20260524-test-job", project_root)

    assets = project_root / "assets" / "20260524-test-job"
    assert (assets / "music-timing.txt").exists()
    assert "DIP" in (assets / "music-timing.txt").read_text()
    assert (assets / "loop.txt").exists()
    assert "OPENING SHOT" in (assets / "loop.txt").read_text()


def test_run_prefers_gap_clip_over_stock(project_root, sample_script):
    footage_dir = project_root / "footage" / "20260524-test-job"
    footage_dir.mkdir(parents=True)
    (footage_dir / "clip_00.mp4").write_bytes(b"stock")
    (footage_dir / "gaps").mkdir()
    (footage_dir / "gaps" / "clip_00.mp4").write_bytes(b"runway-fill")
    (footage_dir / "clip_01.mp4").write_bytes(b"stock2")
    add_voiceover(project_root, "20260524-test-job")
    add_music(project_root, "20260524-test-job")

    run("20260524-test-job", project_root)

    clip = (project_root / "assets" / "20260524-test-job" / "01_clip.mp4").read_bytes()
    assert clip == b"runway-fill"


def test_run_extracts_thumbnail_from_first_clip(project_root, sample_script):
    add_footage(project_root, "20260524-test-job", count=2)
    add_voiceover(project_root, "20260524-test-job")
    add_music(project_root, "20260524-test-job")

    with patch("subprocess.run") as mock_sub:
        mock_sub.return_value = MagicMock(returncode=0)
        run("20260524-test-job", project_root)

    ffmpeg_calls = [str(c.args) for c in mock_sub.call_args_list]
    assert any("vframes" in c for c in ffmpeg_calls)
