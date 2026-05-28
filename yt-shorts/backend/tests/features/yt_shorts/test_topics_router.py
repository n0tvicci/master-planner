import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch
from backend.core.store import ProjectStore, get_store
from backend.config import get_settings, Settings
from backend.features.yt_shorts.routers.topics import router
from backend.features.yt_shorts.models.topic import Topic


def _make_topic(i: int = 0) -> Topic:
    return Topic(
        id=f"topic-{i}",
        title=f"Why snipers never {i}",
        misconception="Movies show center mass",
        real_answer="CNS targeting",
        us_curiosity_score=9 - i,
    )


@pytest.fixture
def setup(tmp_path):
    store = ProjectStore(base_dir=str(tmp_path))
    project = store.create({
        "title": "Test Video",
        "current_step": "topics",
        "topics": [],
        "approved_topic": None,
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
    app.include_router(router, prefix="/projects/{project_id}/topics")
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: Settings(anthropic_api_key="test-key")

    return TestClient(app), project_id, store


def test_generate_topics_returns_list(setup):
    client, project_id, _ = setup
    mock_topics = [_make_topic(i) for i in range(10)]

    with patch("backend.features.yt_shorts.routers.topics.generate_topics") as mock_gen:
        mock_gen.return_value = mock_topics
        response = client.post(f"/projects/{project_id}/topics/generate")

    assert response.status_code == 200
    assert len(response.json()) == 10


def test_generate_topics_stores_in_project(setup):
    client, project_id, store = setup
    mock_topics = [_make_topic(i) for i in range(3)]

    with patch("backend.features.yt_shorts.routers.topics.generate_topics") as mock_gen:
        mock_gen.return_value = mock_topics
        client.post(f"/projects/{project_id}/topics/generate")

    project = store.get(project_id)
    assert len(project["topics"]) == 3


def test_generate_topics_project_not_found(setup):
    client, _, _ = setup

    with patch("backend.features.yt_shorts.routers.topics.generate_topics") as mock_gen:
        mock_gen.return_value = []
        response = client.post("/projects/nonexistent/topics/generate")

    assert response.status_code == 404


def test_list_topics_empty(setup):
    client, project_id, _ = setup
    response = client.get(f"/projects/{project_id}/topics")
    assert response.status_code == 200
    assert response.json() == []


def test_list_topics_after_generate(setup):
    client, project_id, _ = setup
    mock_topics = [_make_topic(i) for i in range(5)]

    with patch("backend.features.yt_shorts.routers.topics.generate_topics") as mock_gen:
        mock_gen.return_value = mock_topics
        client.post(f"/projects/{project_id}/topics/generate")

    response = client.get(f"/projects/{project_id}/topics")
    assert response.status_code == 200
    assert len(response.json()) == 5


def test_approve_topic_returns_approved(setup):
    client, project_id, _ = setup
    mock_topics = [_make_topic(0), _make_topic(1)]

    with patch("backend.features.yt_shorts.routers.topics.generate_topics") as mock_gen:
        mock_gen.return_value = mock_topics
        client.post(f"/projects/{project_id}/topics/generate")

    topic_id = mock_topics[0].id
    response = client.post(f"/projects/{project_id}/topics/{topic_id}/approve")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == topic_id
    assert data["status"] == "approved"


def test_approve_topic_advances_step_to_script(setup):
    client, project_id, store = setup
    mock_topics = [_make_topic(0)]

    with patch("backend.features.yt_shorts.routers.topics.generate_topics") as mock_gen:
        mock_gen.return_value = mock_topics
        client.post(f"/projects/{project_id}/topics/generate")

    topic_id = mock_topics[0].id
    client.post(f"/projects/{project_id}/topics/{topic_id}/approve")

    project = store.get(project_id)
    assert project["current_step"] == "script"
    assert project["approved_topic"]["id"] == topic_id


def test_approve_nonexistent_topic(setup):
    client, project_id, _ = setup
    response = client.post(f"/projects/{project_id}/topics/fake-id/approve")
    assert response.status_code == 404
