from __future__ import annotations
import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from backend.config import settings
from backend.services.subprocess_runner import run_and_log

router = APIRouter()


def _root() -> Path:
    return settings.project_root


async def _launch_analytics(job_id: str, root: Path) -> None:
    log_path = root / ".tmp" / job_id / "analytics.log"
    cmd = ["python", str(root / "publish.py"), "--job", job_id, "--analytics"]
    try:
        await run_and_log(cmd, log_path, cwd=str(root))
    except Exception as exc:
        print(f"[analytics background task error] {exc}")


@router.get("/{job_id}")
def get_analytics(job_id: str, root: Path = Depends(_root)):
    report_file = root / "compliance-logs" / job_id / "audience-report.json"
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Analytics report not found")
    try:
        return json.loads(report_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to read report: {e}") from e


@router.post("/{job_id}/pull")
def pull_analytics(job_id: str, background_tasks: BackgroundTasks,
                   root: Path = Depends(_root)):
    background_tasks.add_task(_launch_analytics, job_id, root)
    return {"status": "pulling", "job_id": job_id}
