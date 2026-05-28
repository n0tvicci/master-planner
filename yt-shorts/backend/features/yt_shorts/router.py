from fastapi import APIRouter
from backend.features.yt_shorts.routers import projects

router = APIRouter(prefix="/yt-shorts")
router.include_router(projects.router, prefix="/projects")
