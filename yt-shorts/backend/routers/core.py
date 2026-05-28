from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.core.jobs import job_manager
from backend.core.notifications import notification_bus

router = APIRouter(prefix="/core", tags=["core"])


@router.get("/jobs")
def list_jobs():
    return [j.model_dump() for j in job_manager.list()]


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    async def generate():
        job = job_manager.get(job_id)
        if job is None:
            yield 'data: {"error": "job not found"}\n\n'
            return
        for line in job.log:
            yield f'data: {{"log": {line!r}}}\n\n'
        yield f'data: {{"status": "{job.status}"}}\n\n'

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/events")
async def global_events():
    async def generate():
        async for event in notification_bus.subscribe():
            yield f"data: {event}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
