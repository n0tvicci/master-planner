import pytest
from backend.core.store import ProjectStore


@pytest.fixture
def store(tmp_path):
    return ProjectStore(base_dir=str(tmp_path))


def test_create_returns_id(store):
    project = store.create({"title": "Test Video", "current_step": "topics"})
    assert "id" in project
    assert project["title"] == "Test Video"
    assert project["current_step"] == "topics"


def test_create_adds_timestamps(store):
    project = store.create({"title": "Test Video", "current_step": "topics"})
    assert "created_at" in project
    assert "updated_at" in project


def test_get_returns_project(store):
    created = store.create({"title": "Test Video", "current_step": "topics"})
    retrieved = store.get(created["id"])
    assert retrieved is not None
    assert retrieved["id"] == created["id"]


def test_get_missing_returns_none(store):
    assert store.get("nonexistent-id") is None


def test_update_merges_fields(store):
    created = store.create({"title": "Test Video", "current_step": "topics"})
    updated = store.update(created["id"], {"current_step": "script"})
    assert updated["current_step"] == "script"
    assert updated["title"] == "Test Video"


def test_update_missing_raises(store):
    with pytest.raises(ValueError, match="not found"):
        store.update("nonexistent-id", {"current_step": "script"})


def test_list_returns_all(store):
    store.create({"title": "A", "current_step": "topics"})
    store.create({"title": "B", "current_step": "topics"})
    projects = store.list()
    assert len(projects) == 2


def test_list_empty(store):
    assert store.list() == []
