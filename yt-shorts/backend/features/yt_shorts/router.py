from fastapi import APIRouter
from backend.features.yt_shorts.routers import projects, topics, script, voiceover

router = APIRouter(prefix="/yt-shorts")
router.include_router(projects.router, prefix="/projects")
router.include_router(topics.router, prefix="/projects/{project_id}/topics")
router.include_router(script.router, prefix="/projects/{project_id}/script")
router.include_router(voiceover.router, prefix="/projects/{project_id}/voiceover")
