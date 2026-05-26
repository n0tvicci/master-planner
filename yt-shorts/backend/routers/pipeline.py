from __future__ import annotations
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


def _lock(root: Path, job_id: str) -> Path:
    return root / ".tmp" / job_id / ".running"


def _any_running(root: Path) -> bool:
    if _running_jobs:
        return True
    tmp = root / ".tmp"
    return tmp.exists() and any(
        d.is_dir() and (d / ".running").exists() for d in tmp.iterdir()
    )


async def _launch_pipeline(job_id: str, topic_title: str, root: Path) -> None:
    lock = _lock(root, job_id)
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.touch()
    log_path = root / ".tmp" / job_id / "pipeline.log"
    cmd = ["python", str(root / "pipeline.py"), "--job", job_id, "--topic", topic_title]
    try:
        await run_and_log(cmd, log_path, cwd=str(root))
    except Exception as exc:
        print(f"[pipeline background task error] {exc}")
    finally:
        _running_jobs.discard(job_id)
        lock.unlink(missing_ok=True)


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
                    "running": job_dir.name in _running_jobs or (job_dir / ".running").exists(),
                })
            except (json.JSONDecodeError, OSError):
                pass
    return jobs


@router.get("/{job_id}/state")
def get_state(job_id: str, root: Path = Depends(_root)):
    state_file = root / ".tmp" / job_id / "state.json"
    if not state_file.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to read job state: {e}") from e


@router.post("/run")
def run_pipeline(background_tasks: BackgroundTasks, root: Path = Depends(_root)):
    if _any_running(root):
        raise HTTPException(status_code=409, detail="A pipeline job is already running")
    queue: list[dict] = read_json(root / "topics" / "queue.json")
    approved = [t for t in queue if t.get("status") == "approved"]
    if not approved:
        raise HTTPException(status_code=400, detail="No approved topics in queue")
    topic = approved[0]
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
