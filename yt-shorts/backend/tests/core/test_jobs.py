import pytest
from backend.core.jobs import JobManager
from backend.core.models import JobStatus


@pytest.fixture
def manager():
    return JobManager()


def test_create_job(manager):
    job = manager.create("yt_shorts", "proj-1", "topics")
    assert job.status == JobStatus.QUEUED
    assert job.progress == 0
    assert job.log == []
    assert job.feature == "yt_shorts"
    assert job.step == "topics"


def test_update_status(manager):
    job = manager.create("yt_shorts", "proj-1", "topics")
    updated = manager.update(job.id, status=JobStatus.RUNNING, progress=25)
    assert updated.status == JobStatus.RUNNING
    assert updated.progress == 25


def test_append_log(manager):
    job = manager.create("yt_shorts", "proj-1", "topics")
    manager.append_log(job.id, "Starting topic generation")
    manager.append_log(job.id, "Done")
    result = manager.get(job.id)
    assert result.log == ["Starting topic generation", "Done"]


def test_get_missing_returns_none(manager):
    assert manager.get("nonexistent") is None


def test_list_all_jobs(manager):
    manager.create("yt_shorts", "proj-1", "topics")
    manager.create("yt_shorts", "proj-2", "script")
    assert len(manager.list()) == 2
