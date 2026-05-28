from backend.core.models import Job, JobStatus
from datetime import datetime


def test_job_defaults():
    job = Job(
        id="abc",
        feature="yt_shorts",
        project_id="proj-1",
        step="topics",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    assert job.status == JobStatus.QUEUED
    assert job.progress == 0
    assert job.log == []


def test_job_status_values():
    assert JobStatus.QUEUED == "queued"
    assert JobStatus.RUNNING == "running"
    assert JobStatus.COMPLETE == "complete"
    assert JobStatus.FAILED == "failed"
