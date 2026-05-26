from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import backend.config  # noqa: F401 — triggers sys.path setup

app = FastAPI(title="YT Shorts Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
