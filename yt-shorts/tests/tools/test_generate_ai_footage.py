import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from tools.generate_ai_footage import run


SAMPLE_GAPS = [
    {
        "sentence_idx": 1,
        "text": "But real snipers never use them in combat.",
        "overlay": "REAL SNIPERS",
        "runway_prompt": "Close-up of sniper rifle scope, cinematic, 4K, no people",
        "needs_prop_library": False,
        "prop_description": None,
    }
]


def make_mock_task(video_url="https://cdn.runwayml.com/fake-video.mp4"):
    task = MagicMock()
    task.output = [video_url]
    return task


def test_run_generates_and_downloads_clip(project_root):
    mock_task = make_mock_task()
    mock_download = MagicMock()
    mock_download.status_code = 200
    mock_download.content = b"fake-video-bytes"

    with patch("runwayml.RunwayML") as mock_cls, \
         patch("requests.get", return_value=mock_download):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.image_to_video.create.return_value.wait_for_task_output.return_value = mock_task

        results = run("20260524-test-job", SAMPLE_GAPS, project_root)

    assert len(results) == 1
    assert results[0]["status"] == "generated"
    out = project_root / "footage" / "20260524-test-job" / "gaps" / "clip_01.mp4"
    assert out.exists()
    assert out.read_bytes() == b"fake-video-bytes"


def test_run_uses_correct_api_params(project_root):
    mock_task = make_mock_task()
    mock_download = MagicMock()
    mock_download.status_code = 200
    mock_download.content = b"bytes"

    with patch("runwayml.RunwayML") as mock_cls, \
         patch("requests.get", return_value=mock_download):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.image_to_video.create.return_value.wait_for_task_output.return_value = mock_task

        run("20260524-test-job", SAMPLE_GAPS, project_root)

    call_kwargs = mock_client.image_to_video.create.call_args[1]
    assert call_kwargs["model"] == "gen4_turbo"
    assert call_kwargs["ratio"] == "720:1280"
    assert call_kwargs["duration"] == 5
    assert "sniper" in call_kwargs["prompt_text"].lower()


def test_run_skips_cached_clip(project_root):
    gap_dir = project_root / "footage" / "20260524-test-job" / "gaps"
    gap_dir.mkdir(parents=True)
    (gap_dir / "clip_01.mp4").write_bytes(b"already-there")

    with patch("runwayml.RunwayML") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        results = run("20260524-test-job", SAMPLE_GAPS, project_root)

    mock_client.image_to_video.create.assert_not_called()
    assert results[0]["status"] == "cached"


def test_run_records_failure_without_raising(project_root):
    from runwayml import TaskFailedError

    with patch("runwayml.RunwayML") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.image_to_video.create.return_value.wait_for_task_output.side_effect = (
            TaskFailedError({"status": "failed", "reason": "content_policy"})
        )

        results = run("20260524-test-job", SAMPLE_GAPS, project_root)

    assert results[0]["status"] == "failed"
    assert "content_policy" in str(results[0].get("error", ""))


def test_run_returns_empty_for_empty_gaps(project_root):
    results = run("20260524-test-job", [], project_root)
    assert results == []


def test_run_halts_before_generating_when_cap_exceeded(project_root):
    # 6 uncached gaps, cap is 5 -> should raise before calling Runway at all
    gaps = [
        {
            "sentence_idx": i,
            "text": f"Sentence {i}.",
            "overlay": "TEST",
            "runway_prompt": f"prompt {i}",
            "needs_prop_library": False,
            "prop_description": None,
        }
        for i in range(6)
    ]
    with patch("runwayml.RunwayML") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="cost cap"):
            run("20260524-test-job", gaps, project_root, max_clips=5)

    mock_client.image_to_video.create.assert_not_called()


def test_run_cached_clips_do_not_count_toward_cap(project_root):
    # 6 gaps but 2 are already cached -> only 4 need generation -> under cap of 5
    gap_dir = project_root / "footage" / "20260524-test-job" / "gaps"
    gap_dir.mkdir(parents=True)
    (gap_dir / "clip_00.mp4").write_bytes(b"cached")
    (gap_dir / "clip_01.mp4").write_bytes(b"cached")

    gaps = [
        {
            "sentence_idx": i,
            "text": f"Sentence {i}.",
            "overlay": "TEST",
            "runway_prompt": f"prompt {i}",
            "needs_prop_library": False,
            "prop_description": None,
        }
        for i in range(6)
    ]
    mock_task = make_mock_task()
    mock_download = MagicMock()
    mock_download.status_code = 200
    mock_download.content = b"video"

    with patch("runwayml.RunwayML") as mock_cls, \
         patch("requests.get", return_value=mock_download):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.image_to_video.create.return_value.wait_for_task_output.return_value = mock_task

        results = run("20260524-test-job", gaps, project_root, max_clips=5)

    # 2 cached + 4 generated = 6 results, no cap error
    assert len(results) == 6
    assert mock_client.image_to_video.create.call_count == 4
