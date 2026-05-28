from fastapi import APIRouter, HTTPException, Depends
from backend.core.store import ProjectStore, get_store
from backend.features.yt_shorts.models.project import (
    Project,
    ProjectCreate,
    ProjectStep,
)

router = APIRouter(tags=["yt-shorts-projects"])


def _initial_state(title: str) -> dict:
    return {
        "title": title,
        "current_step": ProjectStep.TOPICS,
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
    }


@router.post("", response_model=Project, status_code=201)
def create_project(
    body: ProjectCreate,
    store: ProjectStore = Depends(get_store),
):
    data = _initial_state(body.title)
    return store.create(data)


@router.get("", response_model=list[Project])
def list_projects(store: ProjectStore = Depends(get_store)):
    return store.list()


@router.get("/{project_id}", response_model=Project)
def get_project(
    project_id: str,
    store: ProjectStore = Depends(get_store),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
