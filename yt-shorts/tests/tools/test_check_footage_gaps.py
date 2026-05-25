import pytest
from tools.check_footage_gaps import run


def add_clip(project_root, job_id, idx):
    d = project_root / "footage" / job_id
    d.mkdir(parents=True, exist_ok=True)
    (d / f"clip_{idx:02d}.mp4").write_bytes(b"fake")


def test_run_returns_empty_when_all_clips_present(project_root, sample_script):
    add_clip(project_root, "20260524-test-job", 0)
    add_clip(project_root, "20260524-test-job", 1)
    result = run("20260524-test-job", project_root)
    assert result == {"ai_gaps": [], "prop_library_gaps": []}


def test_run_routes_ai_gap_correctly(project_root, sample_script):
    # sentence 1 has needs_prop_library=False → should be an ai_gap
    add_clip(project_root, "20260524-test-job", 0)
    result = run("20260524-test-job", project_root)
    assert len(result["ai_gaps"]) == 1
    assert result["ai_gaps"][0]["sentence_idx"] == 1
    assert result["prop_library_gaps"] == []


def test_run_routes_prop_library_gap_correctly(project_root, sample_script):
    # sentence 0 has needs_prop_library=True → should be a prop_library_gap
    add_clip(project_root, "20260524-test-job", 1)
    result = run("20260524-test-job", project_root)
    assert len(result["prop_library_gaps"]) == 1
    assert result["prop_library_gaps"][0]["sentence_idx"] == 0
    assert result["ai_gaps"] == []


def test_run_writes_gaps_md_with_runway_prompt(project_root, sample_script):
    (project_root / "footage" / "20260524-test-job").mkdir(parents=True)
    run("20260524-test-job", project_root)
    content = (project_root / "assets" / "20260524-test-job" / "footage-gaps.md").read_text()
    assert "Runway" in content
    assert "Gap #" in content


def test_run_writes_no_gaps_message_when_all_found(project_root, sample_script):
    add_clip(project_root, "20260524-test-job", 0)
    add_clip(project_root, "20260524-test-job", 1)
    run("20260524-test-job", project_root)
    assert "No footage gaps" in (
        project_root / "assets" / "20260524-test-job" / "footage-gaps.md"
    ).read_text()


def test_run_accepts_gap_filled_clip_from_gaps_folder(project_root, sample_script):
    footage_dir = project_root / "footage" / "20260524-test-job"
    footage_dir.mkdir(parents=True)
    (footage_dir / "gaps").mkdir()
    (footage_dir / "gaps" / "clip_00.mp4").write_bytes(b"gap-fill")
    add_clip(project_root, "20260524-test-job", 1)
    result = run("20260524-test-job", project_root)
    assert result == {"ai_gaps": [], "prop_library_gaps": []}
