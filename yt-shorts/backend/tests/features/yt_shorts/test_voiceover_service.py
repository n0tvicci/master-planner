from pathlib import Path
from unittest.mock import MagicMock, patch, call
from backend.features.yt_shorts.services.voiceover import generate_voiceover


def test_generate_voiceover_creates_audio_file(tmp_path):
    audio_path = str(tmp_path / "voiceover.mp3")
    mock_chunks = [b"chunk1", b"chunk2"]

    with patch("backend.features.yt_shorts.services.voiceover.ElevenLabs") as MockClass:
        mock_client = MagicMock()
        MockClass.return_value = mock_client
        mock_client.text_to_speech.convert.return_value = iter(mock_chunks)

        result = generate_voiceover(
            text="This is the script.",
            api_key="fake-key",
            voice_id="fake-voice-id",
            output_path=audio_path,
        )

    assert Path(audio_path).exists()
    assert Path(audio_path).read_bytes() == b"chunk1chunk2"
    assert result.audio_path == audio_path
    assert result.status == "generated"


def test_generate_voiceover_uses_correct_settings(tmp_path):
    audio_path = str(tmp_path / "voiceover.mp3")

    with patch("backend.features.yt_shorts.services.voiceover.ElevenLabs") as MockClass:
        mock_client = MagicMock()
        MockClass.return_value = mock_client
        mock_client.text_to_speech.convert.return_value = iter([b"audio"])

        generate_voiceover(
            text="Script text.",
            api_key="my-key",
            voice_id="voice-abc",
            output_path=audio_path,
        )

    MockClass.assert_called_once_with(api_key="my-key")
    call_kwargs = mock_client.text_to_speech.convert.call_args.kwargs
    assert call_kwargs["voice_id"] == "voice-abc"
    assert call_kwargs["text"] == "Script text."
    assert call_kwargs["output_format"] == "mp3_44100_192"


def test_generate_voiceover_skips_empty_chunks(tmp_path):
    audio_path = str(tmp_path / "voiceover.mp3")
    mock_chunks = [b"real", b"", None, b"data"]

    with patch("backend.features.yt_shorts.services.voiceover.ElevenLabs") as MockClass:
        mock_client = MagicMock()
        MockClass.return_value = mock_client
        mock_client.text_to_speech.convert.return_value = iter(mock_chunks)

        generate_voiceover("Text.", "key", "voice", audio_path)

    assert Path(audio_path).read_bytes() == b"realdata"
