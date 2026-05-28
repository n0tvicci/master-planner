from backend.features.yt_shorts.models.project import (
    Project,
    ProjectCreate,
    ProjectStep,
)
from datetime import datetime


def test_project_step_values():
    assert ProjectStep.TOPICS == "topics"
    assert ProjectStep.COMPLETE == "complete"


def test_project_create_schema():
    body = ProjectCreate(title="My Video")
    assert body.title == "My Video"


def test_project_serializes_to_dict():
    now = datetime.utcnow()
    project = Project(
        id="abc",
        title="My Video",
        current_step=ProjectStep.TOPICS,
        created_at=now,
        updated_at=now,
    )
    data = project.model_dump()
    assert data["current_step"] == "topics"
    assert data["title"] == "My Video"
