import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch
from backend.core.store import ProjectStore, get_store
from backend.config import get_settings, Settings
from backend.features.yt_shorts.routers.voiceover import router
from backend.features.yt_shorts.models.voiceover import Voiceover
from backend.features.yt_shorts.models.script import Script, ScriptSentence

_SENTENCE = ScriptSentence(
    id="s1", text="Hook sentence.", pexels_query="q", pixabay_query="q",
    ai_needed=False, keyword_overlay="TEST",
)
_SCRIPT_DICT = Script(
    sentences=[_SENTENCE],
    full_text="Hook sentence.",
    originality_score=8,
    advertiser_friendliness_score=9,
    us_resonance_score=8,
    music_mood="tense",
    status="approved",
).model_dump()


@pytest.fixture
def setup(tmp_path):
    store = ProjectStore(base_dir=str(tmp_path))
    project = store.create({
        "title": "Test Video",
        "current_step": "voiceover",
        "topics": [],
        "approved_topic": {"id": "t1", "title": "Why snipers", "misconception": "X", "real_answer": "Y", "us_curiosity_score": 9, "status": "approved"},
        "script_draft": _SCRIPT_DICT,
        "compliance_report": None,
        "voiceover": None,
        "footage_clips": [],
        "ai_clips": [],
        "selected_track": None,
        "assets_path": None,
        "gate_result": None,
        "metadata": None,
        "youtube_video_id": None,
    })
    project_id = project["id"]

    app = FastAPI()
    app.include_router(router, prefix="/projects/{project_id}/voiceover")
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: Settings(
        elevenlabs_api_key="test-key",
        elevenlabs_voice_id="test-voice",
        tmp_dir=str(tmp_path),
    )

    return TestClient(app), project_id, store


def test_generate_voiceover_returns_voiceover(setup):
    client, project_id, _ = setup
    mock_vo = Voiceover(audio_path="/tmp/test/voiceover.mp3")

    with patch("backend.features.yt_shorts.routers.voiceover.generate_voiceover") as mock_gen:
        mock_gen.return_value = mock_vo
        response = client.post(f"/projects/{project_id}/voiceover/generate")

    assert response.status_code == 200
    assert response.json()["status"] == "generated"


def test_generate_voiceover_stores_in_project(setup):
    client, project_id, store = setup
    mock_vo = Voiceover(audio_path="/tmp/test/voiceover.mp3")

    with patch("backend.features.yt_shorts.routers.voiceover.generate_voiceover") as mock_gen:
        mock_gen.return_value = mock_vo
        client.post(f"/projects/{project_id}/voiceover/generate")

    project = store.get(project_id)
    assert project["voiceover"] is not None
    assert project["voiceover"]["audio_path"] == "/tmp/test/voiceover.mp3"


def test_generate_voiceover_no_script_returns_400(setup):
    client, project_id, store = setup
    store.update(project_id, {"script_draft": None})

    with patch("backend.features.yt_shorts.routers.voiceover.generate_voiceover"):
        response = client.post(f"/projects/{project_id}/voiceover/generate")

    assert response.status_code == 400


def test_get_voiceover_returns_none_when_not_generated(setup):
    client, project_id, _ = setup
    response = client.get(f"/projects/{project_id}/voiceover")
    assert response.status_code == 200
    assert response.json() is None


def test_get_voiceover_after_generate(setup):
    client, project_id, _ = setup
    mock_vo = Voiceover(audio_path="/tmp/test/voiceover.mp3")

    with patch("backend.features.yt_shorts.routers.voiceover.generate_voiceover") as mock_gen:
        mock_gen.return_value = mock_vo
        client.post(f"/projects/{project_id}/voiceover/generate")

    response = client.get(f"/projects/{project_id}/voiceover")
    assert response.status_code == 200
    assert response.json()["audio_path"] == "/tmp/test/voiceover.mp3"


def test_approve_voiceover_advances_to_footage_search(setup):
    client, project_id, store = setup
    mock_vo = Voiceover(audio_path="/tmp/test/voiceover.mp3")

    with patch("backend.features.yt_shorts.routers.voiceover.generate_voiceover") as mock_gen:
        mock_gen.return_value = mock_vo
        client.post(f"/projects/{project_id}/voiceover/generate")

    response = client.post(f"/projects/{project_id}/voiceover/approve")

    assert response.status_code == 200
    project = store.get(project_id)
    assert project["current_step"] == "footage_search"
    assert project["voiceover"]["status"] == "approved"


def test_approve_voiceover_no_voiceover_returns_400(setup):
    client, project_id, _ = setup
    response = client.post(f"/projects/{project_id}/voiceover/approve")
    assert response.status_code == 400
