from fastapi import APIRouter
from backend.features.yt_shorts.routers import projects, topics

router = APIRouter(prefix="/yt-shorts")
router.include_router(projects.router, prefix="/projects")
router.include_router(topics.router, prefix="/projects/{project_id}/topics")
