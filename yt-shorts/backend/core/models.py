from enum import Enum
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class Job(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    feature: str
    project_id: str
    step: str
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    log: list[str] = []
    created_at: datetime
    updated_at: datetime
