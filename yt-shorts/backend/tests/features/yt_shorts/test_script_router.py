import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch
from backend.core.store import ProjectStore, get_store
from backend.config import get_settings, Settings
from backend.features.yt_shorts.routers.script import router
from backend.features.yt_shorts.models.script import Script, ScriptSentence, ComplianceReport

_SENTENCE = ScriptSentence(
    id="s1",
    text="Test sentence.",
    pexels_query="test",
    pixabay_query="test",
    ai_needed=False,
    keyword_overlay="TEST",
)
_SCRIPT = Script(
    sentences=[_SENTENCE],
    full_text="Test sentence.",
    originality_score=8,
    advertiser_friendliness_score=9,
    us_resonance_score=8,
    music_mood="tense",
)
_COMPLIANCE_DICT = {
    "sensitive_content": "CLEAR",
    "sensitive_content_details": None,
    "ai_disclosure_required": True,
    "revision_notes": None,
}


@pytest.fixture
def setup(tmp_path):
    store = ProjectStore(base_dir=str(tmp_path))
    project = store.create({
        "title": "Test Video",
        "current_step": "script",
        "topics": [],
        "approved_topic": {
            "id": "t1",
            "title": "Why snipers never aim for center mass",
            "misconception": "Movies show chest shots",
            "real_answer": "CNS targeting",
            "us_curiosity_score": 9,
            "status": "approved",
        },
        "script_draft": None,
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
    app.include_router(router, prefix="/projects/{project_id}/script")
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: Settings(anthropic_api_key="test-key")

    return TestClient(app), project_id, store


def test_generate_script_returns_script_response(setup):
    client, project_id, _ = setup

    with patch("backend.features.yt_shorts.routers.script.generate_script") as mock_gen:
        mock_gen.return_value = (_SCRIPT, _COMPLIANCE_DICT)
        response = client.post(f"/projects/{project_id}/script/generate")

    assert response.status_code == 200
    data = response.json()
    assert "script" in data
    assert "compliance" in data
    assert data["script"]["originality_score"] == 8


def test_generate_script_no_approved_topic(setup):
    client, project_id, store = setup
    store.update(project_id, {"approved_topic": None})

    with patch("backend.features.yt_shorts.routers.script.generate_script"):
        response = client.post(f"/projects/{project_id}/script/generate")

    assert response.status_code == 400


def test_get_script_returns_none_when_no_draft(setup):
    client, project_id, _ = setup
    response = client.get(f"/projects/{project_id}/script")
    assert response.status_code == 200
    data = response.json()
    assert data["script"] is None


def test_get_script_after_generate(setup):
    client, project_id, _ = setup

    with patch("backend.features.yt_shorts.routers.script.generate_script") as mock_gen:
        mock_gen.return_value = (_SCRIPT, _COMPLIANCE_DICT)
        client.post(f"/projects/{project_id}/script/generate")

    response = client.get(f"/projects/{project_id}/script")
    assert response.status_code == 200
    assert response.json()["script"]["full_text"] == "Test sentence."


def test_compliance_check_returns_report(setup):
    client, project_id, store = setup
    store.update(project_id, {"script_draft": _SCRIPT.model_dump()})

    response = client.post(f"/projects/{project_id}/script/compliance")

    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is True
    assert data["originality_status"] == "PASS"


def test_compliance_check_no_script_returns_400(setup):
    client, project_id, _ = setup
    response = client.post(f"/projects/{project_id}/script/compliance")
    assert response.status_code == 400


def test_approve_script_advances_to_voiceover(setup):
    client, project_id, store = setup
    store.update(project_id, {"script_draft": _SCRIPT.model_dump()})

    response = client.post(f"/projects/{project_id}/script/approve")

    assert response.status_code == 200
    project = store.get(project_id)
    assert project["current_step"] == "voiceover"
    assert project["script_draft"]["status"] == "approved"


def test_approve_script_no_draft_returns_400(setup):
    client, project_id, _ = setup
    response = client.post(f"/projects/{project_id}/script/approve")
    assert response.status_code == 400
