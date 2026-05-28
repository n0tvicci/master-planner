from datetime import datetime
from backend.features.yt_shorts.models.project import Project, ProjectStep


def test_project_defaults():
    now = datetime.utcnow()
    project = Project(
        id="123",
        title="Test",
        current_step=ProjectStep.TOPICS,
        created_at=now,
        updated_at=now,
    )
    assert project.approved_topic is None
    assert project.topics == []
    assert project.script_draft is None
    assert project.footage_clips == []


def test_project_step_enum():
    assert ProjectStep.TOPICS.value == "topics"
    assert ProjectStep.SCRIPT.value == "script"
    assert ProjectStep.COMPLETE.value == "complete"


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
    assert data["topics"] == []
