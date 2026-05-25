import pytest
from unittest.mock import MagicMock, patch
from tools.generate_voiceover import run


def test_run_saves_mp3(project_root, config, sample_script):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"fake-mp3-bytes"

    with patch("requests.post", return_value=mock_response):
        out_path = run("20260524-test-job", config, project_root)

    assert out_path.exists()
    assert out_path.suffix == ".mp3"
    assert out_path.read_bytes() == b"fake-mp3-bytes"


def test_run_uses_voice_override(project_root, config, sample_script):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"fake-mp3-bytes"

    with patch("requests.post", return_value=mock_response) as mock_post:
        run("20260524-test-job", config, project_root, voice_id="custom-voice-xyz")

    call_url = mock_post.call_args[0][0]
    assert "custom-voice-xyz" in call_url


def test_run_uses_env_voice_when_no_override(project_root, config, sample_script):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"bytes"

    with patch("requests.post", return_value=mock_response) as mock_post:
        run("20260524-test-job", config, project_root)

    call_url = mock_post.call_args[0][0]
    assert config["elevenlabs_voice_id"] in call_url


def test_run_concatenates_all_sentences(project_root, config, sample_script):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"bytes"

    with patch("requests.post", return_value=mock_response) as mock_post:
        run("20260524-test-job", config, project_root)

    call_body = mock_post.call_args[1]["json"]
    assert "You've seen them" in call_body["text"]
    assert "real snipers" in call_body["text"]
