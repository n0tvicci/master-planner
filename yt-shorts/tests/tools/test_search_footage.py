import pytest
from unittest.mock import MagicMock, patch, call
from tools.search_footage import run, search_pexels, best_pexels_url


def test_search_pexels_returns_videos(config):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"videos": [{"id": 1, "video_files": []}]}
    with patch("requests.get", return_value=mock_resp):
        result = search_pexels("sniper rifle", config["pexels_api_key"])
    assert len(result) == 1


def test_best_pexels_url_picks_720p_or_higher():
    videos = [{"video_files": [
        {"height": 480, "link": "http://low.mp4"},
        {"height": 1080, "link": "http://high.mp4"},
    ]}]
    url = best_pexels_url(videos)
    assert url == "http://high.mp4"


def test_best_pexels_url_returns_none_when_no_videos():
    assert best_pexels_url([]) is None


def test_run_downloads_clips_for_each_sentence(project_root, config, sample_script):
    pexels_resp = MagicMock()
    pexels_resp.json.return_value = {
        "videos": [{"video_files": [{"height": 1080, "link": "http://clip.mp4"}]}]
    }
    download_resp = MagicMock()
    download_resp.status_code = 200
    download_resp.content = b"fake-video"

    with patch("requests.get", side_effect=[pexels_resp, download_resp, pexels_resp, download_resp]):
        results = run("20260524-test-job", config, project_root)

    assert len(results) == 2
    clips = list((project_root / "footage" / "20260524-test-job").glob("clip_*.mp4"))
    assert len(clips) == 2


def test_run_falls_back_to_pixabay_when_pexels_empty(project_root, config, sample_script):
    pexels_empty = MagicMock()
    pexels_empty.json.return_value = {"videos": []}

    pixabay_resp = MagicMock()
    pixabay_resp.json.return_value = {
        "hits": [{"videos": {"large": {"url": "http://pixabay-clip.mp4"}}}]
    }
    download_resp = MagicMock()
    download_resp.status_code = 200
    download_resp.content = b"pixabay-video"

    with patch("requests.get", side_effect=[pexels_empty, pixabay_resp, download_resp,
                                             pexels_empty, pixabay_resp, download_resp]):
        results = run("20260524-test-job", config, project_root)

    found = [r for r in results if r["status"] == "found"]
    assert all(r.get("source") == "pixabay" for r in found)


def test_run_generates_fallback_queries_via_claude_when_both_apis_empty(project_root, config, sample_script):
    pexels_empty = MagicMock()
    pexels_empty.json.return_value = {"videos": []}
    pixabay_empty = MagicMock()
    pixabay_empty.json.return_value = {"hits": []}

    pexels_fallback = MagicMock()
    pexels_fallback.json.return_value = {
        "videos": [{"video_files": [{"height": 1080, "link": "http://fallback.mp4"}]}]
    }
    download_resp = MagicMock()
    download_resp.status_code = 200
    download_resp.content = b"fallback-video"

    mock_claude_resp = MagicMock()
    mock_claude_resp.content = [MagicMock(text='["military scope closeup", "tactical equipment macro"]')]

    with patch("requests.get", side_effect=[
        pexels_empty, pixabay_empty, pexels_fallback, download_resp,
        pexels_empty, pixabay_empty, pexels_fallback, download_resp,
    ]), patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = mock_claude_resp

        results = run("20260524-test-job", config, project_root)

    found = [r for r in results if r["status"] == "found"]
    assert len(found) == 2
    assert all(r.get("source") == "pexels_fallback" for r in found)
