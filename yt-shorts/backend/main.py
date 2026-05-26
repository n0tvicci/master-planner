from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import backend.config  # noqa: F401
from backend.routers import topics as topics_router
from backend.routers import pipeline as pipeline_router
from backend.routers import publish as publish_router
from backend.routers import analytics as analytics_router

app = FastAPI(title="YT Shorts Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(topics_router.router, prefix="/api/v1/topics", tags=["topics"])
app.include_router(pipeline_router.router, prefix="/api/v1/pipeline", tags=["pipeline"])
app.include_router(publish_router.router, prefix="/api/v1/publish", tags=["publish"])
app.include_router(analytics_router.router, prefix="/api/v1/analytics", tags=["analytics"])


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
