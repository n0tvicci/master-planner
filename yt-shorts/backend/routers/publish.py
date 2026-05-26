from __future__ import annotations
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.config import settings
from backend.services.subprocess_runner import run_and_log, tail_log

# config.py adds project_root to sys.path at import time, so tools imports work here
try:
    from tools.upload_youtube import is_in_upload_window, next_upload_window
    _UPLOAD_YOUTUBE_AVAILABLE = True
except Exception:
    _UPLOAD_YOUTUBE_AVAILABLE = False

router = APIRouter()

_publishing_jobs: set[str] = set()


def _root() -> Path:
    return settings.project_root


def _write_gate_to_state(job_id: str, root: Path) -> None:
    state_file = root / ".tmp" / job_id / "state.json"
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            state = {"job_id": job_id, "completed_steps": []}
    else:
        state = {"job_id": job_id, "completed_steps": []}
    if "pre_upload_gate" not in state.get("completed_steps", []):
        state.setdefault("completed_steps", []).append("pre_upload_gate")
    (root / ".tmp" / job_id).mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")


async def _launch_publish(job_id: str, root: Path, dry_run: bool = False) -> None:
    log_path = root / ".tmp" / job_id / "publish.log"
    cmd = ["python", str(root / "publish.py"), "--job", job_id, "--immediate"]
    if dry_run:
        cmd.append("--dry-run")
    try:
        await run_and_log(cmd, log_path, cwd=str(root))
    except Exception as exc:
        print(f"[publish background task error] {exc}")
    finally:
        _publishing_jobs.discard(job_id)


@router.get("/window")
def get_window():
    if _UPLOAD_YOUTUBE_AVAILABLE:
        try:
            return {"in_window": is_in_upload_window(), "next_window": next_upload_window().isoformat()}
        except Exception:
            pass
    now = datetime.now(timezone.utc)
    return {"in_window": False, "next_window": (now + timedelta(hours=1)).isoformat()}


@router.get("/{job_id}/metadata")
def get_metadata(job_id: str, root: Path = Depends(_root)):
    meta_file = root / "metadata" / job_id / "metadata.json"
    if not meta_file.exists():
        raise HTTPException(status_code=404, detail="Metadata not found")
    try:
        return json.loads(meta_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to read metadata: {e}") from e


@router.post("/{job_id}/upload")
def upload(job_id: str, background_tasks: BackgroundTasks,
           dry_run: bool = False, root: Path = Depends(_root)):
    if job_id in _publishing_jobs:
        raise HTTPException(status_code=409, detail="Publish already in progress for this job")
    final = root / "output" / job_id / "final.mp4"
    if not final.exists():
        raise HTTPException(
            status_code=400,
            detail=f"final.mp4 not found at output/{job_id}/final.mp4 — export from CapCut first",
        )
    _write_gate_to_state(job_id, root)
    _publishing_jobs.add(job_id)
    background_tasks.add_task(_launch_publish, job_id, root, dry_run)
    return {"status": "uploading", "job_id": job_id}


@router.get("/{job_id}/stream")
async def stream_publish(job_id: str, root: Path = Depends(_root)):
    log_path = root / ".tmp" / job_id / "publish.log"

    async def generator():
        async for chunk in tail_log(log_path):
            yield chunk
        yield "data: [DONE]\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")
