from backend.features.yt_shorts.models.voiceover import Voiceover


def test_voiceover_defaults_to_generated():
    v = Voiceover(audio_path="/tmp/projects/abc/voiceover.mp3")
    assert v.status == "generated"
    assert v.duration_seconds is None


def test_voiceover_serializes():
    v = Voiceover(
        audio_path="/tmp/projects/abc/voiceover.mp3",
        duration_seconds=47.3,
    )
    data = v.model_dump()
    assert data["status"] == "generated"
    assert data["duration_seconds"] == 47.3


def test_voiceover_approved_status():
    v = Voiceover(audio_path="/tmp/test.mp3", status="approved")
    assert v.status == "approved"
