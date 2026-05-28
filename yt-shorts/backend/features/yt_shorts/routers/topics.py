from fastapi import APIRouter, HTTPException, Depends
from backend.core.store import ProjectStore, get_store
from backend.config import get_settings, Settings
from backend.features.yt_shorts.models.topic import Topic
from backend.features.yt_shorts.services.topics import generate_topics

router = APIRouter(tags=["yt-shorts-topics"])


@router.post("/generate", response_model=list[Topic])
def generate_topics_endpoint(
    project_id: str,
    store: ProjectStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    topics = generate_topics(settings.anthropic_api_key)
    store.update(project_id, {"topics": [t.model_dump() for t in topics]})
    return topics


@router.get("", response_model=list[Topic])
def list_topics(
    project_id: str,
    store: ProjectStore = Depends(get_store),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.get("topics", [])


@router.post("/{topic_id}/approve", response_model=Topic)
def approve_topic(
    project_id: str,
    topic_id: str,
    store: ProjectStore = Depends(get_store),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    topics = project.get("topics", [])
    topic = next((t for t in topics if t["id"] == topic_id), None)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    topic["status"] = "approved"
    store.update(project_id, {
        "topics": topics,
        "approved_topic": topic,
        "current_step": "script",
    })
    return topic
