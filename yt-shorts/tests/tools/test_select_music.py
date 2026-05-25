import pytest
from tools.select_music import run


def add_track(project_root, folder: str, name: str = "track.mp3"):
    (project_root / "music" / folder / name).write_bytes(b"fake-mp3")


def test_run_copies_track_to_asset_bundle(project_root, sample_script):
    add_track(project_root, "tense")
    out_path = run("20260524-test-job", project_root)
    assert out_path.exists()
    assert out_path.name == "music.mp3"
    assert (project_root / "assets" / "20260524-test-job" / "music.mp3").exists()


def test_run_selects_from_correct_mood_folder(project_root, sample_script):
    add_track(project_root, "tense", "dark_tension.mp3")
    add_track(project_root, "dramatic", "epic_drama.mp3")
    # script mood is "tense"
    out_path = run("20260524-test-job", project_root)
    assert out_path.read_bytes() == b"fake-mp3"


def test_run_falls_back_to_any_track_when_mood_folder_empty(project_root, sample_script):
    add_track(project_root, "dramatic", "epic.mp3")
    out_path = run("20260524-test-job", project_root)
    assert out_path.exists()


def test_run_raises_when_no_music_at_all(project_root, sample_script):
    with pytest.raises(FileNotFoundError, match="No music tracks found"):
        run("20260524-test-job", project_root)
