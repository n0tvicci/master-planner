from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import get_settings
from backend.features.yt_shorts.router import router as yt_shorts_router
from backend.routers.core import router as core_router

settings = get_settings()

app = FastAPI(title="Automation Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(yt_shorts_router, prefix="/api")
app.include_router(core_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
