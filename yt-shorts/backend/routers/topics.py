from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from backend.config import settings
from backend.services.filesystem import read_json, write_json

router = APIRouter()


def _root() -> Path:
    return settings.project_root


@router.get("/pending")
def get_pending(root: Path = Depends(_root)):
    return read_json(root / "topics" / "pending.json")


@router.get("/queue")
def get_queue(root: Path = Depends(_root)):
    return read_json(root / "topics" / "queue.json")


@router.get("/published")
def get_published(root: Path = Depends(_root)):
    return read_json(root / "topics" / "published.json")


@router.post("/generate")
def generate(background_tasks: BackgroundTasks, root: Path = Depends(_root)):
    def _run():
        from tools.utils.config import load_config
        from tools.generate_topics import run, append_to_staging
        config = load_config()
        topics = run(config, root)
        append_to_staging(topics, root)

    background_tasks.add_task(_run)
    return {"status": "generating"}


@router.post("/{topic_id}/approve")
def approve(topic_id: str, root: Path = Depends(_root)):
    pending: list[dict] = read_json(root / "topics" / "pending.json")
    match = next((t for t in pending if t.get("id") == topic_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    write_json(root / "topics" / "pending.json",
               [t for t in pending if t.get("id") != topic_id])
    queue: list[dict] = read_json(root / "topics" / "queue.json")
    queue.append(match)
    write_json(root / "topics" / "queue.json", queue)
    return {"status": "approved", "id": topic_id}


@router.post("/{topic_id}/reject")
def reject(topic_id: str, root: Path = Depends(_root)):
    pending: list[dict] = read_json(root / "topics" / "pending.json")
    if not any(t.get("id") == topic_id for t in pending):
        raise HTTPException(status_code=404, detail="Topic not found")
    write_json(root / "topics" / "pending.json",
               [t for t in pending if t.get("id") != topic_id])
    return {"status": "rejected", "id": topic_id}
