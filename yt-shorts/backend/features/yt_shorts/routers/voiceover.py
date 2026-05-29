from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from backend.core.store import ProjectStore, get_store
from backend.config import get_settings, Settings
from backend.features.yt_shorts.models.voiceover import Voiceover
from backend.features.yt_shorts.models.script import Script
from backend.features.yt_shorts.services.voiceover import generate_voiceover

router = APIRouter(tags=["yt-shorts-voiceover"])


@router.post("/generate", response_model=Voiceover)
def generate_voiceover_endpoint(
    project_id: str,
    store: ProjectStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    script_dict = project.get("script_draft")
    if not script_dict:
        raise HTTPException(status_code=400, detail="No script draft. Generate and approve script first.")

    script = Script(**script_dict)
    audio_path = str(
        Path(settings.tmp_dir) / "projects" / project_id / "voiceover.mp3"
    )
    voiceover = generate_voiceover(
        text=script.full_text,
        api_key=settings.elevenlabs_api_key,
        voice_id=settings.elevenlabs_voice_id,
        output_path=audio_path,
    )
    store.update(project_id, {"voiceover": voiceover.model_dump()})
    return voiceover


@router.get("", response_model=Voiceover | None)
def get_voiceover(
    project_id: str,
    store: ProjectStore = Depends(get_store),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    vo_dict = project.get("voiceover")
    return Voiceover(**vo_dict) if vo_dict else None


@router.post("/approve", response_model=Voiceover)
def approve_voiceover(
    project_id: str,
    store: ProjectStore = Depends(get_store),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    vo_dict = project.get("voiceover")
    if not vo_dict:
        raise HTTPException(status_code=400, detail="No voiceover. Generate voiceover first.")

    vo_dict["status"] = "approved"
    store.update(project_id, {
        "voiceover": vo_dict,
        "current_step": "footage_search",
    })
    return Voiceover(**vo_dict)
