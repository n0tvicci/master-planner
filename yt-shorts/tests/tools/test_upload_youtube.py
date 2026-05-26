import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import tools.upload_youtube as upload_youtube

EST = ZoneInfo("America/New_York")


def test_is_in_upload_window_true_tuesday_morning():
    tue_8am = datetime(2026, 5, 26, 8, 0, tzinfo=EST)
    with patch("tools.upload_youtube._now", return_value=tue_8am):
        assert upload_youtube.is_in_upload_window() is True


def test_is_in_upload_window_false_monday():
    mon_8am = datetime(2026, 5, 25, 8, 0, tzinfo=EST)
    with patch("tools.upload_youtube._now", return_value=mon_8am):
        assert upload_youtube.is_in_upload_window() is False


def test_is_in_upload_window_false_outside_hours():
    tue_10am = datetime(2026, 5, 26, 10, 0, tzinfo=EST)
    with patch("tools.upload_youtube._now", return_value=tue_10am):
        assert upload_youtube.is_in_upload_window() is False


def test_is_in_upload_window_true_saturday_morning():
    sat_10am = datetime(2026, 5, 30, 10, 0, tzinfo=EST)
    with patch("tools.upload_youtube._now", return_value=sat_10am):
        assert upload_youtube.is_in_upload_window() is True


def test_next_upload_window_from_monday_returns_tuesday():
    mon_9am = datetime(2026, 5, 25, 9, 0, tzinfo=EST)
    with patch("tools.upload_youtube._now", return_value=mon_9am):
        nw = upload_youtube.next_upload_window()
    assert nw.isoweekday() == 2
    assert nw.hour == 7


def test_next_upload_window_from_tuesday_after_window():
    tue_930am = datetime(2026, 5, 26, 9, 30, tzinfo=EST)
    with patch("tools.upload_youtube._now", return_value=tue_930am):
        nw = upload_youtube.next_upload_window()
    assert nw.isoweekday() == 3
    assert nw.hour == 7


def test_next_upload_window_from_tuesday_before_window():
    tue_630am = datetime(2026, 5, 26, 6, 30, tzinfo=EST)
    with patch("tools.upload_youtube._now", return_value=tue_630am):
        nw = upload_youtube.next_upload_window()
    assert nw.isoweekday() == 2
    assert nw.hour == 7


def _make_mock_youtube():
    mock_yt = MagicMock()
    mock_yt.videos.return_value.insert.return_value.execute.return_value = {"id": "abc123"}
    mock_yt.commentThreads.return_value.insert.return_value.execute.return_value = {}
    return mock_yt


def test_run_uploads_and_returns_video_id(tmp_path, sample_metadata):
    video_path = tmp_path / "final.mp4"
    video_path.write_bytes(b"fake video data")
    (tmp_path / "credentials.json").write_text("{}")
    (tmp_path / "token.json").write_text("{}")
    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_yt = _make_mock_youtube()
    with patch("tools.utils.youtube_auth.Credentials.from_authorized_user_file",
               return_value=mock_creds), \
         patch("tools.utils.youtube_auth.build", return_value=mock_yt), \
         patch("tools.upload_youtube.MediaFileUpload"):
        result = upload_youtube.run("test-job", video_path, sample_metadata, tmp_path)
    assert result["video_id"] == "abc123"
    assert result["url"] == "https://youtube.com/shorts/abc123"


def test_run_pins_comment_after_upload(tmp_path, sample_metadata):
    video_path = tmp_path / "final.mp4"
    video_path.write_bytes(b"fake")
    (tmp_path / "credentials.json").write_text("{}")
    (tmp_path / "token.json").write_text("{}")
    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_yt = _make_mock_youtube()
    with patch("tools.utils.youtube_auth.Credentials.from_authorized_user_file",
               return_value=mock_creds), \
         patch("tools.utils.youtube_auth.build", return_value=mock_yt), \
         patch("tools.upload_youtube.MediaFileUpload"):
        upload_youtube.run("test-job", video_path, sample_metadata, tmp_path)
    mock_yt.commentThreads.return_value.insert.assert_called_once()
    call_kwargs = mock_yt.commentThreads.return_value.insert.call_args[1]
    pinned_text = call_kwargs["body"]["snippet"]["topLevelComment"]["snippet"]["textOriginal"]
    assert pinned_text == sample_metadata["pinned_comment"]


def test_run_pin_failure_is_non_fatal(tmp_path, sample_metadata):
    video_path = tmp_path / "final.mp4"
    video_path.write_bytes(b"fake")
    (tmp_path / "credentials.json").write_text("{}")
    (tmp_path / "token.json").write_text("{}")
    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_yt = _make_mock_youtube()
    mock_yt.commentThreads.return_value.insert.return_value.execute.side_effect = Exception("video still processing")
    with patch("tools.utils.youtube_auth.Credentials.from_authorized_user_file",
               return_value=mock_creds), \
         patch("tools.utils.youtube_auth.build", return_value=mock_yt), \
         patch("tools.upload_youtube.MediaFileUpload"):
        result = upload_youtube.run("test-job", video_path, sample_metadata, tmp_path)
    assert result["video_id"] == "abc123"


def test_run_raises_if_credentials_json_missing(tmp_path, sample_metadata):
    video_path = tmp_path / "final.mp4"
    video_path.write_bytes(b"fake")
    with pytest.raises(FileNotFoundError, match="credentials.json"):
        upload_youtube.run("test-job", video_path, sample_metadata, tmp_path)
