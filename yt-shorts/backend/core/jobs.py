import uuid
from datetime import datetime, timezone
from threading import Lock
from backend.core.models import Job, JobStatus


class JobManager:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = Lock()

    def create(self, feature: str, project_id: str, step: str) -> Job:
        now = datetime.now(timezone.utc)
        job = Job(
            id=str(uuid.uuid4()),
            feature=feature,
            project_id=project_id,
            step=step,
            status=JobStatus.QUEUED,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._jobs[job.id] = job
        return job

    def update(self, job_id: str, **kwargs) -> Job:
        with self._lock:
            job = self._jobs[job_id]
            updated = job.model_copy(
                update={**kwargs, "updated_at": datetime.now(timezone.utc)}
            )
            self._jobs[job_id] = updated
            return updated

    def append_log(self, job_id: str, message: str) -> Job:
        with self._lock:
            job = self._jobs[job_id]
            updated = job.model_copy(
                update={
                    "log": [*job.log, message],
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            self._jobs[job_id] = updated
            return updated

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        return list(self._jobs.values())


job_manager = JobManager()
