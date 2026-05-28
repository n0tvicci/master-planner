# Platform Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the repo into a shared-core + feature-module platform, implement the project state store, job manager, SSE notification bus, and YT Shorts project CRUD endpoints — everything Plans 2–4 build on.

**Architecture:** FastAPI backend under `backend/` with a `core/` layer (store, jobs, notifications, config) and a `features/yt_shorts/` module. Each feature registers its own router under `/api/{feature}/`. Project state persists as JSON at `.tmp/projects/{id}/state.json`. Dependency injection wires the store into routers so tests can override it with a temp directory.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, pytest, uvicorn. Frontend: React 18, TypeScript, Vite, MUI v5 (frontend scaffold only in this plan — no pages yet).

**Reference:** `fastapi-best-practices.md` in project root for backend conventions.

---

## File Map

### Created
- `backend/__init__.py` — package marker
- `backend/config.py` — Pydantic Settings, loads `.env`
- `backend/main.py` — FastAPI app, CORS, router registration
- `backend/core/__init__.py`
- `backend/core/models.py` — `Job`, `JobStatus` shared Pydantic models
- `backend/core/store.py` — `ProjectStore`, `get_store` DI function
- `backend/core/jobs.py` — `JobManager`, `job_manager` singleton
- `backend/core/notifications.py` — `NotificationBus`, `notification_bus` singleton
- `backend/routers/__init__.py`
- `backend/routers/core.py` — `/api/core/jobs`, `/api/core/events`, `/api/core/jobs/{id}/stream`
- `backend/features/__init__.py`
- `backend/features/yt_shorts/__init__.py`
- `backend/features/yt_shorts/router.py` — registers all YT Shorts sub-routers
- `backend/features/yt_shorts/models/__init__.py`
- `backend/features/yt_shorts/models/project.py` — `ProjectStep`, `Project`, `ProjectCreate`
- `backend/features/yt_shorts/routers/__init__.py`
- `backend/features/yt_shorts/routers/projects.py` — project CRUD
- `backend/features/yt_shorts/services/__init__.py`
- `backend/requirements.txt` — verified/updated
- `backend/tests/__init__.py`
- `backend/tests/core/__init__.py`
- `backend/tests/core/test_store.py`
- `backend/tests/core/test_jobs.py`
- `backend/tests/core/test_notifications.py`
- `backend/tests/features/__init__.py`
- `backend/tests/features/yt_shorts/__init__.py`
- `backend/tests/features/yt_shorts/test_projects.py`

### Deleted
- `tools/` — entire directory (logic migrates to services/ in Plans 2–3)
- `backend/routers/topics.py`, `backend/routers/pipeline.py`, `backend/routers/publish.py`, `backend/routers/analytics.py`
- `backend/services/filesystem.py`, `backend/services/subprocess_runner.py`
- `backend/services/__init__.py` (old)
- `backend/tests/test_pipeline.py`, `backend/tests/test_publish.py`, `backend/tests/test_topics.py`, `backend/tests/test_analytics.py` (old tests — replaced by new ones in `tests/features/` and `tests/core/`)

---

## Task 1: Create New Directory Scaffold

**Files:** Create empty `__init__.py` markers and directories.

- [ ] **Step 1: Create backend package directories**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts
mkdir -p backend/core
mkdir -p backend/routers
mkdir -p backend/features/yt_shorts/models
mkdir -p backend/features/yt_shorts/routers
mkdir -p backend/features/yt_shorts/services
mkdir -p backend/tests/core
mkdir -p backend/tests/features/yt_shorts
```

- [ ] **Step 2: Add `__init__.py` markers**

Create empty files at:
- `backend/core/__init__.py`
- `backend/routers/__init__.py`
- `backend/features/__init__.py`
- `backend/features/yt_shorts/__init__.py`
- `backend/features/yt_shorts/models/__init__.py`
- `backend/features/yt_shorts/routers/__init__.py`
- `backend/features/yt_shorts/services/__init__.py`
- `backend/tests/core/__init__.py`
- `backend/tests/features/__init__.py`
- `backend/tests/features/yt_shorts/__init__.py`

Each file is empty. Use Write tool to create them.

- [ ] **Step 3: Commit scaffold**

```bash
git add backend/
git commit -m "chore: create feature-module directory scaffold"
```

---

## Task 2: Config

**Files:**
- Create: `backend/config.py`

- [ ] **Step 1: Write `backend/config.py`**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    elevenlabs_api_key: str = ""
    pexels_api_key: str = ""
    pixabay_api_key: str = ""
    tmp_dir: str = ".tmp"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 2: Verify `pydantic-settings` is in requirements**

Open `backend/requirements.txt`. If `pydantic-settings` is not present, add it. The file should include at minimum:

```
fastapi
uvicorn[standard]
pydantic
pydantic-settings
python-dotenv
httpx
pytest
pytest-asyncio
```

- [ ] **Step 3: Confirm settings load (manual check)**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts
.venv/Scripts/activate
python -c "from backend.config import get_settings; s = get_settings(); print('tmp_dir:', s.tmp_dir)"
```

Expected output: `tmp_dir: .tmp`

- [ ] **Step 4: Commit**

```bash
git add backend/config.py backend/requirements.txt
git commit -m "feat: add Pydantic Settings config module"
```

---

## Task 3: Core Models

**Files:**
- Create: `backend/core/models.py`
- Create: `backend/tests/core/test_models.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/core/test_models.py`:

```python
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
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest backend/tests/core/test_models.py -v
```

Expected: `ImportError` — module not found.

- [ ] **Step 3: Write `backend/core/models.py`**

```python
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
```

- [ ] **Step 4: Run test — expect PASS**

```bash
pytest backend/tests/core/test_models.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/core/models.py backend/tests/core/test_models.py
git commit -m "feat: add core Job and JobStatus models"
```

---

## Task 4: Project Store

**Files:**
- Create: `backend/core/store.py`
- Create: `backend/tests/core/test_store.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/core/test_store.py`:

```python
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
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest backend/tests/core/test_store.py -v
```

Expected: `ImportError` — module not found.

- [ ] **Step 3: Write `backend/core/store.py`**

```python
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone


class ProjectStore:
    def __init__(self, base_dir: str = ".tmp/projects"):
        self.base = Path(base_dir)

    def _path(self, project_id: str) -> Path:
        return self.base / project_id / "state.json"

    def create(self, data: dict) -> dict:
        project_id = str(uuid.uuid4())
        project_dir = self.base / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        state = {**data, "id": project_id, "created_at": now, "updated_at": now}
        self._path(project_id).write_text(json.dumps(state))
        return state

    def get(self, project_id: str) -> dict | None:
        path = self._path(project_id)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def update(self, project_id: str, data: dict) -> dict:
        state = self.get(project_id)
        if state is None:
            raise ValueError(f"Project {project_id} not found")
        now = datetime.now(timezone.utc).isoformat()
        updated = {**state, **data, "updated_at": now}
        self._path(project_id).write_text(json.dumps(updated))
        return updated

    def list(self) -> list[dict]:
        if not self.base.exists():
            return []
        results = []
        for entry in self.base.iterdir():
            state_file = entry / "state.json"
            if entry.is_dir() and state_file.exists():
                results.append(json.loads(state_file.read_text()))
        return sorted(results, key=lambda x: x["created_at"], reverse=True)


def get_store() -> ProjectStore:
    return ProjectStore()
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest backend/tests/core/test_store.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/core/store.py backend/tests/core/test_store.py
git commit -m "feat: add ProjectStore with JSON-on-disk persistence"
```

---

## Task 5: Job Manager

**Files:**
- Create: `backend/core/jobs.py`
- Create: `backend/tests/core/test_jobs.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/core/test_jobs.py`:

```python
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
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest backend/tests/core/test_jobs.py -v
```

Expected: `ImportError` — module not found.

- [ ] **Step 3: Write `backend/core/jobs.py`**

```python
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
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest backend/tests/core/test_jobs.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/core/jobs.py backend/tests/core/test_jobs.py
git commit -m "feat: add in-memory JobManager with thread-safe updates"
```

---

## Task 6: Notification Bus

**Files:**
- Create: `backend/core/notifications.py`
- Create: `backend/tests/core/test_notifications.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/core/test_notifications.py`:

```python
import asyncio
import pytest
from backend.core.notifications import NotificationBus


@pytest.mark.asyncio
async def test_subscriber_receives_event():
    bus = NotificationBus()
    received = []

    async def collect():
        async for event in bus.subscribe():
            received.append(event)
            break  # collect one event then stop

    task = asyncio.create_task(collect())
    await asyncio.sleep(0)  # let subscriber register
    await bus.publish("step_complete", {"step": "topics"})
    await task

    assert len(received) == 1
    assert "step_complete" in received[0]


@pytest.mark.asyncio
async def test_multiple_subscribers_all_receive():
    bus = NotificationBus()
    received_a = []
    received_b = []

    async def collect_a():
        async for event in bus.subscribe():
            received_a.append(event)
            break

    async def collect_b():
        async for event in bus.subscribe():
            received_b.append(event)
            break

    t1 = asyncio.create_task(collect_a())
    t2 = asyncio.create_task(collect_b())
    await asyncio.sleep(0)
    await bus.publish("test_event", {"x": 1})
    await t1
    await t2

    assert len(received_a) == 1
    assert len(received_b) == 1
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest backend/tests/core/test_notifications.py -v
```

Expected: `ImportError` — module not found.

- [ ] **Step 3: Write `backend/core/notifications.py`**

```python
import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator


class NotificationBus:
    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    async def publish(self, event_type: str, data: dict) -> None:
        payload = json.dumps(
            {
                "type": event_type,
                "data": data,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )
        for queue in self._subscribers:
            await queue.put(payload)

    async def subscribe(self) -> AsyncGenerator[str, None]:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self._subscribers.remove(queue)


notification_bus = NotificationBus()
```

- [ ] **Step 4: Add `pytest-asyncio` to requirements and configure**

In `backend/requirements.txt`, add `pytest-asyncio` if not present.

Create `backend/pytest.ini` (or `backend/pyproject.toml` section if it exists):

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
pytest backend/tests/core/test_notifications.py -v
```

Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/core/notifications.py backend/tests/core/test_notifications.py backend/requirements.txt backend/pytest.ini
git commit -m "feat: add async SSE notification bus"
```

---

## Task 7: YT Shorts Project Models

**Files:**
- Create: `backend/features/yt_shorts/models/project.py`
- Create: `backend/tests/features/yt_shorts/test_project_models.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/features/yt_shorts/test_project_models.py`:

```python
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
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest backend/tests/features/yt_shorts/test_project_models.py -v
```

Expected: `ImportError` — module not found.

- [ ] **Step 3: Write `backend/features/yt_shorts/models/project.py`**

```python
from enum import Enum
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Any


class ProjectStep(str, Enum):
    TOPICS = "topics"
    SCRIPT = "script"
    VOICEOVER = "voiceover"
    FOOTAGE_SEARCH = "footage_search"
    FOOTAGE_AI = "footage_ai"
    MUSIC = "music"
    ASSETS = "assets"
    GATE = "gate"
    METADATA = "metadata"
    PUBLISH = "publish"
    MONITOR = "monitor"
    COMPLETE = "complete"


class ProjectCreate(BaseModel):
    title: str


class Project(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    current_step: ProjectStep
    created_at: datetime
    updated_at: datetime
    # Step outputs — populated as project advances
    approved_topic: Optional[dict] = None
    script_draft: Optional[dict] = None
    compliance_report: Optional[dict] = None
    voiceover: Optional[dict] = None
    footage_clips: list[dict] = []
    ai_clips: list[dict] = []
    selected_track: Optional[dict] = None
    assets_path: Optional[str] = None
    gate_result: Optional[dict] = None
    metadata: Optional[dict] = None
    youtube_video_id: Optional[str] = None
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest backend/tests/features/yt_shorts/test_project_models.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/features/yt_shorts/models/project.py backend/tests/features/yt_shorts/test_project_models.py
git commit -m "feat: add YT Shorts Project and ProjectStep models"
```

---

## Task 8: Project CRUD Router

**Files:**
- Create: `backend/features/yt_shorts/routers/projects.py`
- Create: `backend/tests/features/yt_shorts/test_projects_router.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/features/yt_shorts/test_projects_router.py`:

```python
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.core.store import ProjectStore, get_store
from backend.features.yt_shorts.routers.projects import router


@pytest.fixture
def client(tmp_path):
    app = FastAPI()
    app.include_router(router, prefix="/projects")

    def override_store():
        return ProjectStore(base_dir=str(tmp_path))

    app.dependency_overrides[get_store] = override_store
    return TestClient(app)


def test_create_project(client):
    response = client.post("/projects", json={"title": "My Video"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My Video"
    assert data["current_step"] == "topics"
    assert "id" in data
    assert "created_at" in data


def test_create_project_missing_title(client):
    response = client.post("/projects", json={})
    assert response.status_code == 422


def test_list_projects_empty(client):
    response = client.get("/projects")
    assert response.status_code == 200
    assert response.json() == []


def test_list_projects_returns_created(client):
    client.post("/projects", json={"title": "Video 1"})
    client.post("/projects", json={"title": "Video 2"})
    response = client.get("/projects")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_project(client):
    create_resp = client.post("/projects", json={"title": "My Video"})
    project_id = create_resp.json()["id"]
    response = client.get(f"/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["id"] == project_id


def test_get_missing_project(client):
    response = client.get("/projects/nonexistent-id")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest backend/tests/features/yt_shorts/test_projects_router.py -v
```

Expected: `ImportError` — router not found.

- [ ] **Step 3: Write `backend/features/yt_shorts/routers/projects.py`**

```python
from fastapi import APIRouter, HTTPException, Depends
from backend.core.store import ProjectStore, get_store
from backend.features.yt_shorts.models.project import (
    Project,
    ProjectCreate,
    ProjectStep,
)

router = APIRouter(tags=["yt-shorts-projects"])


def _initial_state(title: str) -> dict:
    return {
        "title": title,
        "current_step": ProjectStep.TOPICS,
        "approved_topic": None,
        "script_draft": None,
        "compliance_report": None,
        "voiceover": None,
        "footage_clips": [],
        "ai_clips": [],
        "selected_track": None,
        "assets_path": None,
        "gate_result": None,
        "metadata": None,
        "youtube_video_id": None,
    }


@router.post("", response_model=Project, status_code=201)
def create_project(
    body: ProjectCreate,
    store: ProjectStore = Depends(get_store),
):
    data = _initial_state(body.title)
    return store.create(data)


@router.get("", response_model=list[Project])
def list_projects(store: ProjectStore = Depends(get_store)):
    return store.list()


@router.get("/{project_id}", response_model=Project)
def get_project(
    project_id: str,
    store: ProjectStore = Depends(get_store),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest backend/tests/features/yt_shorts/test_projects_router.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/features/yt_shorts/routers/projects.py backend/tests/features/yt_shorts/test_projects_router.py
git commit -m "feat: add YT Shorts project CRUD endpoints"
```

---

## Task 9: Feature Router + Core API Routes

**Files:**
- Create: `backend/features/yt_shorts/router.py`
- Create: `backend/routers/core.py`

- [ ] **Step 1: Write `backend/features/yt_shorts/router.py`**

```python
from fastapi import APIRouter
from backend.features.yt_shorts.routers import projects

router = APIRouter(prefix="/yt-shorts")
router.include_router(projects.router, prefix="/projects")
```

- [ ] **Step 2: Write `backend/routers/core.py`**

```python
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
```

- [ ] **Step 3: Write `backend/tests/core/test_core_router.py`**

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.routers.core import router
from backend.core.jobs import JobManager, job_manager
from backend.core.models import JobStatus


def test_list_jobs_empty():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    response = client.get("/core/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_jobs_returns_created():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    job_manager.create("yt_shorts", "proj-1", "topics")
    response = client.get("/core/jobs")
    assert response.status_code == 200
    jobs = response.json()
    assert any(j["feature"] == "yt_shorts" for j in jobs)
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest backend/tests/core/test_core_router.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/features/yt_shorts/router.py backend/routers/core.py backend/tests/core/test_core_router.py
git commit -m "feat: add feature router and core API routes (jobs, SSE events)"
```

---

## Task 10: Wire main.py

**Files:**
- Modify: `backend/main.py`
- Create: `backend/tests/test_main.py`

- [ ] **Step 1: Write failing integration test**

Create `backend/tests/test_main.py`:

```python
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_projects_route_exists():
    response = client.get("/api/yt-shorts/projects")
    assert response.status_code == 200


def test_core_jobs_route_exists():
    response = client.get("/api/core/jobs")
    assert response.status_code == 200


def test_cors_headers():
    response = client.options(
        "/api/yt-shorts/projects",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code in (200, 204)
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest backend/tests/test_main.py -v
```

Expected: failures due to missing routes or imports.

- [ ] **Step 3: Rewrite `backend/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import get_settings
from backend.features.yt_shorts.router import router as yt_shorts_router
from backend.routers.core import router as core_router

settings = get_settings()

app = FastAPI(title="Automation Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(yt_shorts_router, prefix="/api")
app.include_router(core_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest backend/tests/test_main.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Run the full test suite**

```bash
pytest backend/tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Confirm server starts**

```bash
uvicorn backend.main:app --reload
```

Open `http://localhost:8000/docs` — you should see the Swagger UI with `/api/yt-shorts/projects` and `/api/core/jobs` endpoints listed.

- [ ] **Step 7: Commit**

```bash
git add backend/main.py backend/tests/test_main.py
git commit -m "feat: wire feature routers into main FastAPI app"
```

---

## Task 11: Delete Old Structure

**Files:** Delete old flat backend files and the entire tools/ directory.

- [ ] **Step 1: Delete old backend files**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts
rm backend/routers/topics.py
rm backend/routers/pipeline.py
rm backend/routers/publish.py
rm backend/routers/analytics.py
rm backend/services/filesystem.py
rm backend/services/subprocess_runner.py
rm backend/services/__init__.py
rm backend/tests/test_pipeline.py
rm backend/tests/test_publish.py
rm backend/tests/test_topics.py
rm backend/tests/test_analytics.py
# Do NOT delete backend/tests/test_main.py — Task 10 creates a new version of it.
```

If any of these files don't exist (already gone), skip silently.

- [ ] **Step 2: Delete old backend/__init__.py if it re-exports old structure**

Open `backend/__init__.py`. If it imports from the old routers/services, clear its contents. If it's already empty or doesn't exist, skip.

- [ ] **Step 3: Delete tools/ directory**

```bash
rm -rf tools/
```

- [ ] **Step 4: Run full test suite to confirm nothing broke**

```bash
pytest backend/tests/ -v
```

Expected: all tests still pass.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove old flat routers, services, and tools/ directory"
```

---

## Task 12: Frontend Scaffold Update

**Files:**
- Modify: `frontend/src/App.tsx` — add feature routing structure
- Create: `frontend/src/core/ProjectContext.tsx` — active project_id in context
- Create: `frontend/src/features/yt-shorts/.gitkeep` — placeholder

> **Note:** This task only updates the frontend scaffold to match the new directory structure. Actual pages are built in Plan 4. No tests needed here — the frontend build succeeding is the verification.

- [ ] **Step 1: Create frontend feature directory**

```bash
mkdir -p frontend/src/core
mkdir -p frontend/src/features/yt-shorts/pages
mkdir -p frontend/src/features/yt-shorts/components
mkdir -p frontend/src/features/yt-shorts/api
```

- [ ] **Step 2: Create `frontend/src/core/ProjectContext.tsx`**

```tsx
import { createContext, useContext, useState, ReactNode } from "react";

interface ProjectContextValue {
  projectId: string | null;
  setProjectId: (id: string | null) => void;
}

const ProjectContext = createContext<ProjectContextValue>({
  projectId: null,
  setProjectId: () => {},
});

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [projectId, setProjectId] = useState<string | null>(null);
  return (
    <ProjectContext.Provider value={{ projectId, setProjectId }}>
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  return useContext(ProjectContext);
}
```

- [ ] **Step 3: Create `frontend/src/core/api/client.ts`**

```typescript
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail ?? `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function createSSEStream(path: string): EventSource {
  return new EventSource(`${BASE_URL}${path}`);
}
```

- [ ] **Step 4: Confirm frontend still builds**

```bash
cd frontend
npm run build
```

Expected: build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/core/ frontend/src/features/
git commit -m "feat: add frontend core scaffold — ProjectContext and API client"
```

---

## Final Verification

- [ ] **Run the full backend test suite**

```bash
pytest backend/tests/ -v --tb=short
```

Expected: all tests pass, no warnings about imports from deleted files.

- [ ] **Start backend and verify Swagger**

```bash
uvicorn backend.main:app --reload
```

Open `http://localhost:8000/docs`. Confirm:
- `POST /api/yt-shorts/projects` exists
- `GET /api/yt-shorts/projects` exists
- `GET /api/yt-shorts/projects/{project_id}` exists
- `GET /api/core/jobs` exists
- `GET /api/core/events` exists

- [ ] **Smoke test project CRUD**

```bash
# create
curl -s -X POST http://localhost:8000/api/yt-shorts/projects \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Video"}' | python -m json.tool

# list
curl -s http://localhost:8000/api/yt-shorts/projects | python -m json.tool
```

Expected: project created with `id`, `current_step: "topics"`, timestamps.

- [ ] **Final commit**

```bash
git add -A
git commit -m "chore: Plan 1 complete — platform foundation shipped"
```
