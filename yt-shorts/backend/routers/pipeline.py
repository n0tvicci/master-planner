from __future__ import annotations
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.config import settings
from backend.services.filesystem import read_json
from backend.services.subprocess_runner import run_and_log, tail_log

router = APIRouter()

_running_jobs: set[str] = set()


def _root() -> Path:
    return settings.project_root


def _launch_pipeline(job_id: str, topic_title: str, root: Path) -> None:
    log_path = root / ".tmp" / job_id / "pipeline.log"
    cmd = ["python", str(root / "pipeline.py"), "--job", job_id, "--topic", topic_title]
    asyncio.run(run_and_log(cmd, log_path, cwd=str(root)))
    _running_jobs.discard(job_id)


@router.get("/jobs")
def get_jobs(root: Path = Depends(_root)):
    tmp = root / ".tmp"
    if not tmp.exists():
        return []
    jobs = []
    for job_dir in sorted(tmp.iterdir()):
        state_file = job_dir / "state.json"
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
                jobs.append({
                    "job_id": job_dir.name,
                    "completed_steps": state.get("completed_steps", []),
                    "running": job_dir.name in _running_jobs,
                })
            except (json.JSONDecodeError, OSError):
                pass
    return jobs


@router.get("/{job_id}/state")
def get_state(job_id: str, root: Path = Depends(_root)):
    state_file = root / ".tmp" / job_id / "state.json"
    if not state_file.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    return json.loads(state_file.read_text(encoding="utf-8"))


@router.post("/run")
def run_pipeline(background_tasks: BackgroundTasks, root: Path = Depends(_root)):
    queue: list[dict] = read_json(root / "topics" / "queue.json")
    if not queue:
        raise HTTPException(status_code=400, detail="Topic queue is empty")
    topic = queue[0]
    topic_title = topic.get("title", "")
    job_id = f"job-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    _running_jobs.add(job_id)
    background_tasks.add_task(_launch_pipeline, job_id, topic_title, root)
    return {"job_id": job_id, "topic": topic_title}


@router.get("/{job_id}/stream")
async def stream_log(job_id: str, root: Path = Depends(_root)):
    log_path = root / ".tmp" / job_id / "pipeline.log"

    async def generator():
        async for chunk in tail_log(log_path):
            yield chunk
        yield "data: [DONE]\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")
