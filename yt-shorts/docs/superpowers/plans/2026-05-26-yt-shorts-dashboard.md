# YT Shorts Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local React 18 + FastAPI web dashboard replacing CLI interactions for topic approval, pipeline monitoring, YouTube upload, and audience analytics.

**Architecture:** FastAPI backend (port 8000) wraps `pipeline.py` / `publish.py` subprocess calls and exposes local filesystem JSON as REST + SSE endpoints. React 18 + MUI frontend (port 5173) proxies `/api` to FastAPI. No auth, no database — both layers read/write the same filesystem the CLI tools use.

**Tech Stack:** Python 3.13 · FastAPI 0.115 · uvicorn · pydantic-settings · React 18 · TypeScript · Vite 6 · MUI v5 · axios · React Router v6

---

## File Map

**Backend (new)**
- `backend/__init__.py` — empty
- `backend/requirements.txt`
- `backend/config.py` — Pydantic BaseSettings + sys.path setup
- `backend/main.py` — FastAPI app + CORS + all routers
- `backend/routers/__init__.py` — empty
- `backend/routers/topics.py` — /api/v1/topics/* (6 endpoints)
- `backend/routers/pipeline.py` — /api/v1/pipeline/* (4 endpoints + SSE)
- `backend/routers/publish.py` — /api/v1/publish/* (4 endpoints + SSE)
- `backend/routers/analytics.py` — /api/v1/analytics/* (2 endpoints)
- `backend/services/__init__.py` — empty
- `backend/services/filesystem.py` — read_json / write_json
- `backend/services/subprocess_runner.py` — run_and_log + tail_log (SSE)
- `backend/tests/__init__.py` — empty
- `backend/tests/test_main.py`
- `backend/tests/test_topics.py`
- `backend/tests/test_pipeline.py`
- `backend/tests/test_publish.py`
- `backend/tests/test_analytics.py`

**Tools (modified)**
- `tools/generate_topics.py` — add `append_to_staging()` function

**Frontend (new)**
- `frontend/index.html`
- `frontend/package.json`
- `frontend/vite.config.ts` — proxy /api → localhost:8000
- `frontend/tsconfig.json`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx` — ThemeProvider + PipelineProvider + PublishProvider
- `frontend/src/theme/index.ts` — MUI dark theme
- `frontend/src/types/index.ts` — shared TypeScript interfaces
- `frontend/src/api/client.ts` — axios instance
- `frontend/src/api/topics.ts`
- `frontend/src/api/pipeline.ts`
- `frontend/src/api/publish.ts`
- `frontend/src/api/analytics.ts`
- `frontend/src/hooks/useSSE.ts`
- `frontend/src/hooks/useJobState.ts`
- `frontend/src/store/PipelineContext.tsx`
- `frontend/src/store/PublishContext.tsx`
- `frontend/src/layouts/AppShell.tsx` — sidebar + topbar
- `frontend/src/components/TopicCard.tsx`
- `frontend/src/components/StatusBadge.tsx`
- `frontend/src/components/StepTracker.tsx`
- `frontend/src/components/LogPanel.tsx`
- `frontend/src/pages/TopicsPage.tsx`
- `frontend/src/pages/PipelinePage.tsx`
- `frontend/src/pages/PublishPage.tsx`
- `frontend/src/pages/AnalyticsPage.tsx`
- `frontend/src/router/index.tsx`

---

### Task 1: Backend Foundation

**Files:**
- Create: `backend/__init__.py`, `backend/services/__init__.py`, `backend/routers/__init__.py`, `backend/tests/__init__.py`
- Create: `backend/requirements.txt`
- Create: `backend/config.py`
- Create: `backend/services/filesystem.py`
- Create: `backend/services/subprocess_runner.py`
- Create: `backend/main.py`
- Create: `backend/tests/test_main.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_main.py`:
```python
from fastapi.testclient import TestClient


def test_health_returns_ok():
    from backend.main import app
    client = TestClient(app)
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_cors_header_present():
    from backend.main import app
    client = TestClient(app)
    r = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts
python -m pytest backend/tests/test_main.py -v
```
Expected: `ModuleNotFoundError: No module named 'backend'`

- [ ] **Step 3: Create empty init files**

`backend/__init__.py` — empty  
`backend/services/__init__.py` — empty  
`backend/routers/__init__.py` — empty  
`backend/tests/__init__.py` — empty

- [ ] **Step 4: Create `backend/requirements.txt`**

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
pydantic-settings==2.6.1
httpx==0.27.2
pytest==9.0.3
```

Install: `pip install -r backend/requirements.txt`

- [ ] **Step 5: Create `backend/config.py`**

```python
import sys
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    project_root: Path = Path(__file__).parent.parent

    model_config = {
        "env_prefix": "YT_",
        "env_file": str(Path(__file__).parent.parent / ".env"),
    }


settings = Settings()

if str(settings.project_root) not in sys.path:
    sys.path.insert(0, str(settings.project_root))
```

- [ ] **Step 6: Create `backend/services/filesystem.py`**

```python
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
```

- [ ] **Step 7: Create `backend/services/subprocess_runner.py`**

```python
import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path


async def run_and_log(cmd: list[str], log_path: Path, cwd: str | None = None) -> None:
    """Run subprocess, write all stdout+stderr to log_path, append [DONE] when finished."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=cwd,
    )
    with log_path.open("w", encoding="utf-8", buffering=1) as f:
        async for line in proc.stdout:
            f.write(line.decode(errors="replace").rstrip() + "\n")
    await proc.wait()
    with log_path.open("a", encoding="utf-8") as f:
        f.write("[DONE]\n")


async def tail_log(log_path: Path, poll_interval: float = 0.1) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted lines from log_path. Stops when [DONE] is seen."""
    position = 0
    while True:
        if log_path.exists():
            with log_path.open("r", encoding="utf-8") as f:
                f.seek(position)
                content = f.read()
            if content:
                for line in content.splitlines():
                    if line == "[DONE]":
                        return
                    yield f"data: {line}\n\n"
                position += len(content.encode("utf-8"))
        await asyncio.sleep(poll_interval)
```

- [ ] **Step 8: Create `backend/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import backend.config  # noqa: F401 — triggers sys.path setup

app = FastAPI(title="YT Shorts Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 9: Run tests — verify both pass**

```bash
python -m pytest backend/tests/test_main.py -v
```
Expected: `2 passed`

- [ ] **Step 10: Commit**

```bash
git add backend/
git commit -m "feat: backend foundation — FastAPI app, filesystem service, subprocess runner"
```

---

### Task 2: Topics API

**Files:**
- Modify: `tools/generate_topics.py` — add `append_to_staging()`
- Create: `backend/routers/topics.py`
- Create: `backend/tests/test_topics.py`
- Modify: `backend/main.py` — register topics router

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_topics.py`:
```python
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_project(tmp_path):
    (tmp_path / "topics").mkdir()
    return tmp_path


@pytest.fixture
def client(tmp_project, monkeypatch):
    monkeypatch.setenv("YT_PROJECT_ROOT", str(tmp_project))
    import importlib
    import backend.config
    importlib.reload(backend.config)
    from backend.main import app
    return TestClient(app)


def _write(path: Path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def test_get_pending_empty(client, tmp_project):
    r = client.get("/api/v1/topics/pending")
    assert r.status_code == 200
    assert r.json() == []


def test_get_pending_returns_data(client, tmp_project):
    _write(tmp_project / "topics" / "pending.json", [{"id": "abc", "title": "Test"}])
    r = client.get("/api/v1/topics/pending")
    assert r.json()[0]["title"] == "Test"


def test_get_queue_empty(client, tmp_project):
    r = client.get("/api/v1/topics/queue")
    assert r.json() == []


def test_get_published_empty(client, tmp_project):
    r = client.get("/api/v1/topics/published")
    assert r.json() == []


def test_approve_moves_topic_to_queue(client, tmp_project):
    _write(tmp_project / "topics" / "pending.json",
           [{"id": "abc123", "title": "Test Topic", "score": 9}])
    r = client.post("/api/v1/topics/abc123/approve")
    assert r.status_code == 200
    remaining = json.loads((tmp_project / "topics" / "pending.json").read_text())
    assert remaining == []
    queue = json.loads((tmp_project / "topics" / "queue.json").read_text())
    assert queue[0]["title"] == "Test Topic"


def test_approve_unknown_id_returns_404(client, tmp_project):
    _write(tmp_project / "topics" / "pending.json", [])
    assert client.post("/api/v1/topics/notexist/approve").status_code == 404


def test_reject_removes_topic(client, tmp_project):
    _write(tmp_project / "topics" / "pending.json",
           [{"id": "abc123", "title": "Test Topic"}])
    r = client.post("/api/v1/topics/abc123/reject")
    assert r.status_code == 200
    remaining = json.loads((tmp_project / "topics" / "pending.json").read_text())
    assert remaining == []


def test_reject_unknown_id_returns_404(client, tmp_project):
    _write(tmp_project / "topics" / "pending.json", [])
    assert client.post("/api/v1/topics/notexist/reject").status_code == 404
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest backend/tests/test_topics.py -v
```
Expected: errors (no topics router registered)

- [ ] **Step 3: Add `append_to_staging()` to `tools/generate_topics.py`**

After the closing line of `append_to_queue()` (after line 116 `queue_file.write_text(...)`), add this new function:

```python
def append_to_staging(topics: list[dict], project_root: Path) -> None:
    staging_file = project_root / "topics" / "pending.json"
    staging_file.parent.mkdir(exist_ok=True)
    if staging_file.exists():
        try:
            existing = json.loads(staging_file.read_text())
        except (json.JSONDecodeError, OSError):
            existing = []
    else:
        existing = []
    now = datetime.now(timezone.utc).isoformat()
    for topic in topics:
        topic["id"] = str(uuid.uuid4())[:8]
        topic["status"] = "pending"
        topic["created_at"] = now
        if "title_options" in topic and not topic.get("title"):
            topic["title"] = topic["title_options"][0]
    existing.extend(topics)
    staging_file.write_text(json.dumps(existing, indent=2))
```

- [ ] **Step 4: Create `backend/routers/topics.py`**

```python
from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from backend.config import settings
from backend.services.filesystem import read_json, write_json

router = APIRouter()


def _root() -> Path:
    return settings.project_root


@router.get("/pending")
def get_pending(root: Path = Depends(_root)):
    return read_json(root / "topics" / "pending.json")


@router.get("/queue")
def get_queue(root: Path = Depends(_root)):
    return read_json(root / "topics" / "queue.json")


@router.get("/published")
def get_published(root: Path = Depends(_root)):
    return read_json(root / "topics" / "published.json")


@router.post("/generate")
def generate(background_tasks: BackgroundTasks, root: Path = Depends(_root)):
    def _run():
        from tools.utils.config import load_config
        from tools.generate_topics import run, append_to_staging
        config = load_config()
        topics = run(config, root)
        append_to_staging(topics, root)

    background_tasks.add_task(_run)
    return {"status": "generating"}


@router.post("/{topic_id}/approve")
def approve(topic_id: str, root: Path = Depends(_root)):
    pending: list[dict] = read_json(root / "topics" / "pending.json")
    match = next((t for t in pending if t.get("id") == topic_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    write_json(root / "topics" / "pending.json",
               [t for t in pending if t.get("id") != topic_id])
    queue: list[dict] = read_json(root / "topics" / "queue.json")
    queue.append(match)
    write_json(root / "topics" / "queue.json", queue)
    return {"status": "approved", "id": topic_id}


@router.post("/{topic_id}/reject")
def reject(topic_id: str, root: Path = Depends(_root)):
    pending: list[dict] = read_json(root / "topics" / "pending.json")
    if not any(t.get("id") == topic_id for t in pending):
        raise HTTPException(status_code=404, detail="Topic not found")
    write_json(root / "topics" / "pending.json",
               [t for t in pending if t.get("id") != topic_id])
    return {"status": "rejected", "id": topic_id}
```

- [ ] **Step 5: Register topics router in `backend/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import backend.config  # noqa: F401
from backend.routers import topics as topics_router

app = FastAPI(title="YT Shorts Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(topics_router.router, prefix="/api/v1/topics", tags=["topics"])


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Run all backend tests — verify they pass**

```bash
python -m pytest backend/tests/test_main.py backend/tests/test_topics.py -v
```
Expected: `9 passed`

- [ ] **Step 7: Commit**

```bash
git add backend/ tools/generate_topics.py
git commit -m "feat: topics API + generate_topics staging flag"
```

---

### Task 3: Pipeline API

**Files:**
- Create: `backend/routers/pipeline.py`
- Create: `backend/tests/test_pipeline.py`
- Modify: `backend/main.py` — register pipeline router

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_pipeline.py`:
```python
import json
import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_project(tmp_path):
    (tmp_path / ".tmp").mkdir()
    (tmp_path / "topics").mkdir()
    return tmp_path


@pytest.fixture
def client(tmp_project, monkeypatch):
    monkeypatch.setenv("YT_PROJECT_ROOT", str(tmp_project))
    import importlib
    import backend.config
    importlib.reload(backend.config)
    from backend.main import app
    return TestClient(app)


def _write_state(root: Path, job_id: str, state: dict):
    job_dir = root / ".tmp" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")


def test_get_jobs_empty(client, tmp_project):
    assert client.get("/api/v1/pipeline/jobs").json() == []


def test_get_jobs_lists_existing_jobs(client, tmp_project):
    _write_state(tmp_project, "job-001", {"job_id": "job-001", "completed_steps": []})
    jobs = client.get("/api/v1/pipeline/jobs").json()
    assert any(j["job_id"] == "job-001" for j in jobs)


def test_get_state_returns_state(client, tmp_project):
    _write_state(tmp_project, "job-001", {"job_id": "job-001", "completed_steps": ["generate_script"]})
    r = client.get("/api/v1/pipeline/job-001/state")
    assert r.status_code == 200
    assert r.json()["completed_steps"] == ["generate_script"]


def test_get_state_missing_returns_404(client, tmp_project):
    assert client.get("/api/v1/pipeline/missing/state").status_code == 404


def test_run_returns_job_id(client, tmp_project):
    queue = [{"id": "t1", "title": "Test Topic", "score": 9}]
    (tmp_project / "topics" / "queue.json").write_text(json.dumps(queue), encoding="utf-8")
    with patch("backend.routers.pipeline._launch_pipeline"):
        r = client.post("/api/v1/pipeline/run")
    assert r.status_code == 200
    assert "job_id" in r.json()


def test_run_empty_queue_returns_400(client, tmp_project):
    (tmp_project / "topics" / "queue.json").write_text("[]", encoding="utf-8")
    r = client.post("/api/v1/pipeline/run")
    assert r.status_code == 400
    assert "empty" in r.json()["detail"].lower()
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest backend/tests/test_pipeline.py -v
```
Expected: errors (no pipeline router)

- [ ] **Step 3: Create `backend/routers/pipeline.py`**

```python
from __future__ import annotations
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.config import settings
from backend.services.filesystem import read_json
from backend.services.subprocess_runner import run_and_log, tail_log

router = APIRouter()

_running_jobs: set[str] = set()


def _root() -> Path:
    return settings.project_root


def _launch_pipeline(job_id: str, topic_title: str, root: Path) -> None:
    log_path = root / ".tmp" / job_id / "pipeline.log"
    cmd = ["python", str(root / "pipeline.py"), "--job", job_id, "--topic", topic_title]
    asyncio.run(run_and_log(cmd, log_path, cwd=str(root)))
    _running_jobs.discard(job_id)


@router.get("/jobs")
def get_jobs(root: Path = Depends(_root)):
    tmp = root / ".tmp"
    if not tmp.exists():
        return []
    jobs = []
    for job_dir in sorted(tmp.iterdir()):
        state_file = job_dir / "state.json"
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
                jobs.append({
                    "job_id": job_dir.name,
                    "completed_steps": state.get("completed_steps", []),
                    "running": job_dir.name in _running_jobs,
                })
            except (json.JSONDecodeError, OSError):
                pass
    return jobs


@router.get("/{job_id}/state")
def get_state(job_id: str, root: Path = Depends(_root)):
    state_file = root / ".tmp" / job_id / "state.json"
    if not state_file.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    return json.loads(state_file.read_text(encoding="utf-8"))


@router.post("/run")
def run_pipeline(background_tasks: BackgroundTasks, root: Path = Depends(_root)):
    queue: list[dict] = read_json(root / "topics" / "queue.json")
    if not queue:
        raise HTTPException(status_code=400, detail="Topic queue is empty")
    topic = queue[0]
    topic_title = topic.get("title", "")
    job_id = f"job-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    _running_jobs.add(job_id)
    background_tasks.add_task(_launch_pipeline, job_id, topic_title, root)
    return {"job_id": job_id, "topic": topic_title}


@router.get("/{job_id}/stream")
async def stream_log(job_id: str, root: Path = Depends(_root)):
    log_path = root / ".tmp" / job_id / "pipeline.log"

    async def generator():
        async for chunk in tail_log(log_path):
            yield chunk
        yield "data: [DONE]\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")
```

- [ ] **Step 4: Register pipeline router in `backend/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import backend.config  # noqa: F401
from backend.routers import topics as topics_router
from backend.routers import pipeline as pipeline_router

app = FastAPI(title="YT Shorts Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(topics_router.router, prefix="/api/v1/topics", tags=["topics"])
app.include_router(pipeline_router.router, prefix="/api/v1/pipeline", tags=["pipeline"])


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Run all tests — verify they pass**

```bash
python -m pytest backend/tests/test_main.py backend/tests/test_topics.py backend/tests/test_pipeline.py -v
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: pipeline API — jobs, state, run, SSE log streaming"
```

---

### Task 4: Publish + Analytics API

**Files:**
- Create: `backend/routers/publish.py`
- Create: `backend/routers/analytics.py`
- Create: `backend/tests/test_publish.py`
- Create: `backend/tests/test_analytics.py`
- Modify: `backend/main.py` — register both routers

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_publish.py`:
```python
import json
import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_project(tmp_path):
    for d in ["output", "metadata", ".tmp"]:
        (tmp_path / d).mkdir()
    return tmp_path


@pytest.fixture
def client(tmp_project, monkeypatch):
    monkeypatch.setenv("YT_PROJECT_ROOT", str(tmp_project))
    import importlib
    import backend.config
    importlib.reload(backend.config)
    from backend.main import app
    return TestClient(app)


def test_get_window_returns_shape(client):
    r = client.get("/api/v1/publish/window")
    assert r.status_code == 200
    data = r.json()
    assert "in_window" in data
    assert isinstance(data["in_window"], bool)
    assert "next_window" in data


def test_get_metadata_not_found_returns_404(client, tmp_project):
    assert client.get("/api/v1/publish/job-001/metadata").status_code == 404


def test_get_metadata_returns_data(client, tmp_project):
    meta_dir = tmp_project / "metadata" / "job-001"
    meta_dir.mkdir(parents=True)
    (meta_dir / "metadata.json").write_text(json.dumps({"title": "Test"}), encoding="utf-8")
    r = client.get("/api/v1/publish/job-001/metadata")
    assert r.json()["title"] == "Test"


def test_upload_missing_final_mp4_returns_400(client, tmp_project):
    r = client.post("/api/v1/publish/job-001/upload")
    assert r.status_code == 400
    assert "final.mp4" in r.json()["detail"]


def test_upload_writes_gate_to_state(client, tmp_project):
    job_id = "job-001"
    (tmp_project / "output" / job_id).mkdir(parents=True)
    (tmp_project / "output" / job_id / "final.mp4").touch()
    tmp_dir = tmp_project / ".tmp" / job_id
    tmp_dir.mkdir(parents=True)
    (tmp_dir / "state.json").write_text(
        json.dumps({"job_id": job_id, "completed_steps": []}), encoding="utf-8"
    )
    with patch("backend.routers.publish._launch_publish"):
        r = client.post(f"/api/v1/publish/{job_id}/upload")
    assert r.status_code == 200
    state = json.loads((tmp_dir / "state.json").read_text())
    assert "pre_upload_gate" in state["completed_steps"]
```

Create `backend/tests/test_analytics.py`:
```python
import json
import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_project(tmp_path):
    (tmp_path / "compliance-logs").mkdir()
    return tmp_path


@pytest.fixture
def client(tmp_project, monkeypatch):
    monkeypatch.setenv("YT_PROJECT_ROOT", str(tmp_project))
    import importlib
    import backend.config
    importlib.reload(backend.config)
    from backend.main import app
    return TestClient(app)


def test_get_analytics_not_found_returns_404(client):
    assert client.get("/api/v1/analytics/job-001").status_code == 404


def test_get_analytics_returns_report(client, tmp_project):
    report_dir = tmp_project / "compliance-logs" / "job-001"
    report_dir.mkdir(parents=True)
    (report_dir / "audience-report.json").write_text(
        json.dumps({"us_share": 0.62, "flag": "GREEN"}), encoding="utf-8"
    )
    r = client.get("/api/v1/analytics/job-001")
    assert r.json()["flag"] == "GREEN"


def test_pull_triggers_background_task(client):
    with patch("backend.routers.analytics._launch_analytics") as mock:
        r = client.post("/api/v1/analytics/job-001/pull")
    assert r.status_code == 200
    assert mock.called
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python -m pytest backend/tests/test_publish.py backend/tests/test_analytics.py -v
```
Expected: errors (no routers)

- [ ] **Step 3: Create `backend/routers/publish.py`**

```python
from __future__ import annotations
import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.config import settings
from backend.services.subprocess_runner import run_and_log, tail_log

router = APIRouter()


def _root() -> Path:
    return settings.project_root


def _write_gate_to_state(job_id: str, root: Path) -> None:
    state_file = root / ".tmp" / job_id / "state.json"
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            state = {"job_id": job_id, "completed_steps": []}
    else:
        state = {"job_id": job_id, "completed_steps": []}
    if "pre_upload_gate" not in state.get("completed_steps", []):
        state.setdefault("completed_steps", []).append("pre_upload_gate")
    (root / ".tmp" / job_id).mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _launch_publish(job_id: str, root: Path, dry_run: bool = False) -> None:
    log_path = root / ".tmp" / job_id / "publish.log"
    cmd = ["python", str(root / "publish.py"), "--job", job_id, "--immediate"]
    if dry_run:
        cmd.append("--dry-run")
    asyncio.run(run_and_log(cmd, log_path, cwd=str(root)))


@router.get("/window")
def get_window(root: Path = Depends(_root)):
    import sys
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from tools.upload_youtube import is_in_upload_window, next_upload_window
    return {"in_window": is_in_upload_window(), "next_window": next_upload_window().isoformat()}


@router.get("/{job_id}/metadata")
def get_metadata(job_id: str, root: Path = Depends(_root)):
    meta_file = root / "metadata" / job_id / "metadata.json"
    if not meta_file.exists():
        raise HTTPException(status_code=404, detail="Metadata not found")
    return json.loads(meta_file.read_text(encoding="utf-8"))


@router.post("/{job_id}/upload")
def upload(job_id: str, background_tasks: BackgroundTasks,
           dry_run: bool = False, root: Path = Depends(_root)):
    final = root / "output" / job_id / "final.mp4"
    if not final.exists():
        raise HTTPException(
            status_code=400,
            detail=f"final.mp4 not found at output/{job_id}/final.mp4 — export from CapCut first",
        )
    _write_gate_to_state(job_id, root)
    background_tasks.add_task(_launch_publish, job_id, root, dry_run)
    return {"status": "uploading", "job_id": job_id}


@router.get("/{job_id}/stream")
async def stream_publish(job_id: str, root: Path = Depends(_root)):
    log_path = root / ".tmp" / job_id / "publish.log"

    async def generator():
        async for chunk in tail_log(log_path):
            yield chunk
        yield "data: [DONE]\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")
```

- [ ] **Step 4: Create `backend/routers/analytics.py`**

```python
from __future__ import annotations
import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from backend.config import settings
from backend.services.subprocess_runner import run_and_log

router = APIRouter()


def _root() -> Path:
    return settings.project_root


def _launch_analytics(job_id: str, root: Path) -> None:
    log_path = root / ".tmp" / job_id / "analytics.log"
    cmd = ["python", str(root / "publish.py"), "--job", job_id, "--analytics"]
    asyncio.run(run_and_log(cmd, log_path, cwd=str(root)))


@router.get("/{job_id}")
def get_analytics(job_id: str, root: Path = Depends(_root)):
    report_file = root / "compliance-logs" / job_id / "audience-report.json"
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Analytics report not found")
    return json.loads(report_file.read_text(encoding="utf-8"))


@router.post("/{job_id}/pull")
def pull_analytics(job_id: str, background_tasks: BackgroundTasks,
                   root: Path = Depends(_root)):
    background_tasks.add_task(_launch_analytics, job_id, root)
    return {"status": "pulling", "job_id": job_id}
```

- [ ] **Step 5: Register both routers — final `backend/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import backend.config  # noqa: F401
from backend.routers import topics as topics_router
from backend.routers import pipeline as pipeline_router
from backend.routers import publish as publish_router
from backend.routers import analytics as analytics_router

app = FastAPI(title="YT Shorts Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(topics_router.router, prefix="/api/v1/topics", tags=["topics"])
app.include_router(pipeline_router.router, prefix="/api/v1/pipeline", tags=["pipeline"])
app.include_router(publish_router.router, prefix="/api/v1/publish", tags=["publish"])
app.include_router(analytics_router.router, prefix="/api/v1/analytics", tags=["analytics"])


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Run all backend tests**

```bash
python -m pytest backend/tests/ -v
```
Expected: all pass (14+ tests)

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: publish and analytics API — gate state write, upload SSE, analytics pull"
```

---

### Task 5: Frontend Foundation

**Files:** Entire `frontend/` scaffold + AppShell layout + stub pages

- [ ] **Step 1: Scaffold Vite project**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install @mui/material @mui/icons-material @emotion/react @emotion/styled axios react-router-dom
```

- [ ] **Step 2: Replace `frontend/vite.config.ts`**

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
```

- [ ] **Step 3: Create `frontend/src/theme/index.ts`**

```ts
import { createTheme } from '@mui/material/styles'

export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#4f79ff' },
    secondary: { main: '#22c55e' },
    background: { default: '#0d1117', paper: '#1e2533' },
    warning: { main: '#f59e0b' },
    error: { main: '#ef4444' },
    success: { main: '#22c55e' },
  },
  typography: { fontFamily: 'Inter, system-ui, sans-serif' },
  components: {
    MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
  },
})
```

- [ ] **Step 4: Create `frontend/src/types/index.ts`**

```ts
export interface Topic {
  id: string
  title: string
  tier: number
  tier_score?: number
  hook_object?: string
  status?: string
  created_at?: string
  title_options?: string[]
}

export interface PipelineState {
  job_id: string
  completed_steps: string[]
  running?: boolean
  video_id?: string
}

export interface JobInfo {
  job_id: string
  completed_steps: string[]
  running: boolean
}

export interface Metadata {
  title: string
  description: string
  tags: string[]
  pinned_comment: string
}

export interface UploadWindow {
  in_window: boolean
  next_window: string
}

export interface AnalyticsReport {
  us_share: number
  flag: 'GREEN' | 'YELLOW' | 'RED'
  notes?: string
  country_breakdown?: Record<string, number>
}
```

- [ ] **Step 5: Create `frontend/src/api/client.ts`**

```ts
import axios from 'axios'

const client = axios.create({ baseURL: '/api/v1' })
export default client
```

- [ ] **Step 6: Create stub pages**

`frontend/src/pages/TopicsPage.tsx`:
```tsx
export default function TopicsPage() { return <div>Topics</div> }
```

`frontend/src/pages/PipelinePage.tsx`:
```tsx
export default function PipelinePage() { return <div>Pipeline</div> }
```

`frontend/src/pages/PublishPage.tsx`:
```tsx
export default function PublishPage() { return <div>Publish</div> }
```

`frontend/src/pages/AnalyticsPage.tsx`:
```tsx
export default function AnalyticsPage() { return <div>Analytics</div> }
```

- [ ] **Step 7: Create `frontend/src/router/index.tsx`**

```tsx
import { createBrowserRouter } from 'react-router-dom'
import AppShell from '../layouts/AppShell'
import TopicsPage from '../pages/TopicsPage'
import PipelinePage from '../pages/PipelinePage'
import PublishPage from '../pages/PublishPage'
import AnalyticsPage from '../pages/AnalyticsPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <TopicsPage /> },
      { path: 'pipeline', element: <PipelinePage /> },
      { path: 'publish', element: <PublishPage /> },
      { path: 'analytics', element: <AnalyticsPage /> },
    ],
  },
])
```

- [ ] **Step 8: Create `frontend/src/layouts/AppShell.tsx`**

```tsx
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import Box from '@mui/material/Box'
import Drawer from '@mui/material/Drawer'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemIcon from '@mui/material/ListItemIcon'
import ListItemText from '@mui/material/ListItemText'
import Typography from '@mui/material/Typography'
import Divider from '@mui/material/Divider'
import ListAltIcon from '@mui/icons-material/ListAlt'
import BoltIcon from '@mui/icons-material/Bolt'
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch'
import BarChartIcon from '@mui/icons-material/BarChart'

const W = 192
const NAV = [
  { label: 'Topics', path: '/', Icon: ListAltIcon },
  { label: 'Pipeline', path: '/pipeline', Icon: BoltIcon },
  { label: 'Publish', path: '/publish', Icon: RocketLaunchIcon },
  { label: 'Analytics', path: '/analytics', Icon: BarChartIcon },
]

export default function AppShell() {
  const navigate = useNavigate()
  const { pathname } = useLocation()

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <Drawer
        variant="permanent"
        sx={{
          width: W, flexShrink: 0,
          '& .MuiDrawer-paper': { width: W, bgcolor: '#1a1f2e', borderRight: '1px solid', borderColor: 'divider' },
        }}
      >
        <Box sx={{ p: 2, pb: 1.5 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 800, color: 'primary.main', letterSpacing: 1 }}>SHORTS</Typography>
          <Typography variant="caption" color="text.secondary">YT Automation</Typography>
        </Box>
        <Divider />
        <List dense sx={{ pt: 1 }}>
          {NAV.map(({ label, path, Icon }) => {
            const active = pathname === path
            return (
              <ListItemButton
                key={path}
                selected={active}
                onClick={() => navigate(path)}
                sx={{
                  borderLeft: '2px solid',
                  borderColor: active ? 'primary.main' : 'transparent',
                  '&.Mui-selected': { bgcolor: 'primary.main' + '15' },
                }}
              >
                <ListItemIcon sx={{ minWidth: 32, color: active ? 'text.primary' : 'text.secondary' }}>
                  <Icon fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary={label}
                  primaryTypographyProps={{ fontSize: 13, color: active ? 'text.primary' : 'text.secondary' }}
                />
              </ListItemButton>
            )
          })}
        </List>
      </Drawer>
      <Box component="main" sx={{ flex: 1, p: 3, overflow: 'auto' }}>
        <Outlet />
      </Box>
    </Box>
  )
}
```

- [ ] **Step 9: Create `frontend/src/App.tsx`**

```tsx
import { RouterProvider } from 'react-router-dom'
import { ThemeProvider, CssBaseline } from '@mui/material'
import { theme } from './theme'
import { router } from './router'

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <RouterProvider router={router} />
    </ThemeProvider>
  )
}
```

- [ ] **Step 10: Update `frontend/src/main.tsx`**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><App /></React.StrictMode>,
)
```

- [ ] **Step 11: Delete Vite default files**

Delete: `frontend/src/App.css`, `frontend/src/index.css`, `frontend/src/assets/react.svg`, `frontend/public/vite.svg`

Remove the `<link rel="stylesheet" ...>` lines from `frontend/index.html` that reference deleted CSS files.

- [ ] **Step 12: Start servers and verify app loads**

Terminal 1 (backend):
```bash
cd E:/digital-sorcery/master-planner/yt-shorts
.venv/Scripts/activate
uvicorn backend.main:app --reload --port 8000
```

Terminal 2 (frontend):
```bash
cd E:/digital-sorcery/master-planner/yt-shorts/frontend
npm run dev
```

Open http://localhost:5173 — verify dark sidebar with 4 nav items, clicking each renders stub text.

- [ ] **Step 13: Commit**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts
git add frontend/
git commit -m "feat: frontend foundation — Vite + MUI scaffold, AppShell sidebar, router, stubs"
```

---

### Task 6: Topics Page

**Files:**
- Create: `frontend/src/api/topics.ts`
- Create: `frontend/src/components/StatusBadge.tsx`
- Create: `frontend/src/components/TopicCard.tsx`
- Modify: `frontend/src/pages/TopicsPage.tsx`

- [ ] **Step 1: Create `frontend/src/api/topics.ts`**

```ts
import client from './client'
import type { Topic } from '../types'

export const topicsApi = {
  getPending: () => client.get<Topic[]>('/topics/pending').then(r => r.data),
  getQueue: () => client.get<Topic[]>('/topics/queue').then(r => r.data),
  generate: () => client.post('/topics/generate').then(r => r.data),
  approve: (id: string) => client.post(`/topics/${id}/approve`).then(r => r.data),
  reject: (id: string) => client.post(`/topics/${id}/reject`).then(r => r.data),
}
```

- [ ] **Step 2: Create `frontend/src/components/StatusBadge.tsx`**

```tsx
import Chip from '@mui/material/Chip'

export default function StatusBadge({ tier, score }: { tier: number; score?: number }) {
  const color = tier === 1 ? 'success' : tier === 2 ? 'warning' : 'default'
  const label = score != null ? `Tier ${tier} · ${score}/10` : `Tier ${tier}`
  return <Chip label={label} color={color} size="small" variant="outlined" />
}
```

- [ ] **Step 3: Create `frontend/src/components/TopicCard.tsx`**

```tsx
import { useState } from 'react'
import Box from '@mui/material/Box'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import CheckIcon from '@mui/icons-material/Check'
import CloseIcon from '@mui/icons-material/Close'
import StatusBadge from './StatusBadge'
import type { Topic } from '../types'

interface Props {
  topic: Topic
  onApprove: (id: string) => Promise<void>
  onReject: (id: string) => Promise<void>
}

export default function TopicCard({ topic, onApprove, onReject }: Props) {
  const [busy, setBusy] = useState<'approve' | 'reject' | null>(null)

  const handle = (action: 'approve' | 'reject') => async () => {
    setBusy(action)
    try { action === 'approve' ? await onApprove(topic.id) : await onReject(topic.id) }
    finally { setBusy(null) }
  }

  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 1, display: 'flex', alignItems: 'center', gap: 2 }}>
      <Box sx={{
        width: 40, height: 40, borderRadius: '50%', flexShrink: 0,
        border: '2px solid', borderColor: topic.tier === 1 ? 'success.main' : 'warning.main',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Typography variant="subtitle2" color={topic.tier === 1 ? 'success.main' : 'warning.main'}>
          {topic.tier_score ?? topic.tier}
        </Typography>
      </Box>
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography variant="body2" fontWeight={600} noWrap>{topic.title}</Typography>
        <Box sx={{ display: 'flex', gap: 1, mt: 0.5, alignItems: 'center' }}>
          <StatusBadge tier={topic.tier} score={topic.tier_score} />
          {topic.hook_object && (
            <Typography variant="caption" color="text.secondary">Hook: {topic.hook_object}</Typography>
          )}
        </Box>
      </Box>
      <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
        <Button size="small" variant="outlined" color="success" startIcon={<CheckIcon />}
          disabled={busy !== null} onClick={handle('approve')}>Approve</Button>
        <Button size="small" variant="outlined" color="error" startIcon={<CloseIcon />}
          disabled={busy !== null} onClick={handle('reject')}>Reject</Button>
      </Box>
    </Paper>
  )
}
```

- [ ] **Step 4: Implement `frontend/src/pages/TopicsPage.tsx`**

```tsx
import { useCallback, useEffect, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import AddIcon from '@mui/icons-material/Add'
import TopicCard from '../components/TopicCard'
import { topicsApi } from '../api/topics'
import type { Topic } from '../types'

export default function TopicsPage() {
  const [pending, setPending] = useState<Topic[]>([])
  const [queue, setQueue] = useState<Topic[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  const refresh = useCallback(async () => {
    const [p, q] = await Promise.all([topicsApi.getPending(), topicsApi.getQueue()])
    setPending(p)
    setQueue(q)
  }, [])

  useEffect(() => { refresh().finally(() => setLoading(false)) }, [refresh])

  const handleGenerate = async () => {
    setGenerating(true)
    await topicsApi.generate()
    const before = pending.length
    const poll = setInterval(async () => {
      const p = await topicsApi.getPending()
      if (p.length > before) { setPending(p); clearInterval(poll); setGenerating(false) }
    }, 2000)
    setTimeout(() => { clearInterval(poll); setGenerating(false) }, 90000)
  }

  const handleApprove = async (id: string) => { await topicsApi.approve(id); await refresh() }
  const handleReject = async (id: string) => { await topicsApi.reject(id); await refresh() }

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', pt: 8 }}><CircularProgress /></Box>

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" fontWeight={700}>Topics</Typography>
        <Button variant="contained" startIcon={generating ? <CircularProgress size={14} color="inherit" /> : <AddIcon />}
          disabled={generating} onClick={handleGenerate}>
          {generating ? 'Generating...' : 'Generate Topics'}
        </Button>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 3 }}>
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}>
            Pending Approval ({pending.length})
          </Typography>
          {pending.length === 0
            ? <Typography variant="body2" color="text.secondary">No pending topics. Click Generate to create new ones.</Typography>
            : pending.map(t => <TopicCard key={t.id} topic={t} onApprove={handleApprove} onReject={handleReject} />)
          }
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}>
            Approved Queue ({queue.length})
          </Typography>
          {queue.map((t, i) => (
            <Paper key={t.id ?? i} variant="outlined" sx={{ p: 1.5, mb: 1, display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Typography variant="caption" color="primary.main" fontWeight={700} sx={{ minWidth: 16 }}>{i + 1}</Typography>
              <Typography variant="body2" noWrap sx={{ flex: 1 }}>{t.title}</Typography>
              {t.tier_score && <Typography variant="caption" color="text.secondary">Score {t.tier_score}</Typography>}
            </Paper>
          ))}
          {queue.length === 0 && <Typography variant="body2" color="text.secondary">No approved topics yet.</Typography>}
        </Box>
      </Box>
    </Box>
  )
}
```

- [ ] **Step 5: Manual test**

Seed `topics/pending.json` in the project root:
```json
[{"id": "test01", "title": "AK-47 vs M16 — Myths Americans Believe", "tier": 1, "tier_score": 9, "hook_object": "AK-47 rifle"}]
```

Open http://localhost:5173 → Topics. Verify card renders. Click Approve → card disappears, appears in queue column.

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: Topics page — TopicCard, approve/reject, generate, queue display"
```

---

### Task 7: Pipeline Page

**Files:**
- Create: `frontend/src/api/pipeline.ts`
- Create: `frontend/src/hooks/useSSE.ts`
- Create: `frontend/src/hooks/useJobState.ts`
- Create: `frontend/src/store/PipelineContext.tsx`
- Create: `frontend/src/components/StepTracker.tsx`
- Create: `frontend/src/components/LogPanel.tsx`
- Modify: `frontend/src/pages/PipelinePage.tsx`
- Modify: `frontend/src/App.tsx` — add PipelineProvider

- [ ] **Step 1: Create `frontend/src/api/pipeline.ts`**

```ts
import client from './client'
import type { JobInfo, PipelineState } from '../types'

export const pipelineApi = {
  getJobs: () => client.get<JobInfo[]>('/pipeline/jobs').then(r => r.data),
  getState: (jobId: string) => client.get<PipelineState>(`/pipeline/${jobId}/state`).then(r => r.data),
  run: () => client.post<{ job_id: string; topic: string }>('/pipeline/run').then(r => r.data),
  streamUrl: (jobId: string) => `/api/v1/pipeline/${jobId}/stream`,
}
```

- [ ] **Step 2: Create `frontend/src/hooks/useSSE.ts`**

```ts
import { useEffect, useRef } from 'react'

export function useSSE(url: string | null, onMessage: (line: string) => void, onDone?: () => void) {
  const msgRef = useRef(onMessage)
  const doneRef = useRef(onDone)
  msgRef.current = onMessage
  doneRef.current = onDone

  useEffect(() => {
    if (!url) return
    const es = new EventSource(url)
    es.onmessage = (e) => {
      if (e.data === '[DONE]') { doneRef.current?.(); es.close() }
      else msgRef.current(e.data)
    }
    es.onerror = () => es.close()
    return () => es.close()
  }, [url])
}
```

- [ ] **Step 3: Create `frontend/src/hooks/useJobState.ts`**

```ts
import { useEffect, useState } from 'react'
import { pipelineApi } from '../api/pipeline'
import type { PipelineState } from '../types'

export function useJobState(jobId: string | null, ms = 3000) {
  const [state, setState] = useState<PipelineState | null>(null)
  useEffect(() => {
    if (!jobId) return
    const fetch = () => pipelineApi.getState(jobId).then(setState).catch(() => {})
    fetch()
    const id = setInterval(fetch, ms)
    return () => clearInterval(id)
  }, [jobId, ms])
  return state
}
```

- [ ] **Step 4: Create `frontend/src/store/PipelineContext.tsx`**

```tsx
import { createContext, useCallback, useContext, useState } from 'react'

interface Ctx {
  activeJobId: string | null
  isRunning: boolean
  setActiveJob: (id: string) => void
  setRunning: (v: boolean) => void
}

const PipelineContext = createContext<Ctx | null>(null)

export function PipelineProvider({ children }: { children: React.ReactNode }) {
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const setActiveJob = useCallback((id: string) => setActiveJobId(id), [])
  const setRunning = useCallback((v: boolean) => setIsRunning(v), [])
  return (
    <PipelineContext.Provider value={{ activeJobId, isRunning, setActiveJob, setRunning }}>
      {children}
    </PipelineContext.Provider>
  )
}

export function usePipelineContext() {
  const ctx = useContext(PipelineContext)
  if (!ctx) throw new Error('usePipelineContext must be inside PipelineProvider')
  return ctx
}
```

- [ ] **Step 5: Create `frontend/src/components/StepTracker.tsx`**

```tsx
import Box from '@mui/material/Box'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import CircularProgress from '@mui/material/CircularProgress'
import CheckIcon from '@mui/icons-material/Check'

const STEPS = [
  { key: 'generate_script', label: 'Generate Script' },
  { key: 'generate_voiceover', label: 'Generate Voiceover' },
  { key: 'search_footage', label: 'Search Footage' },
  { key: 'generate_ai_footage', label: 'Generate AI Footage' },
  { key: 'check_footage_gaps', label: 'Check Footage Gaps' },
  { key: 'package_assets', label: 'Package Assets' },
]

export default function StepTracker({ completedSteps, isRunning }: { completedSteps: string[]; isRunning: boolean }) {
  const done = new Set(completedSteps)
  const nextIdx = STEPS.findIndex(s => !done.has(s.key))

  return (
    <Box>
      {STEPS.map((step, i) => {
        const isDone = done.has(step.key)
        const isActive = isRunning && i === nextIdx
        return (
          <Paper key={step.key} variant="outlined" sx={{
            display: 'flex', alignItems: 'center', gap: 1.5, p: 1.25, mb: 0.5,
            borderColor: isActive ? 'primary.main' : 'divider',
          }}>
            <Box sx={{
              width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              border: '1.5px solid',
              borderColor: isDone ? 'success.main' : isActive ? 'primary.main' : 'divider',
              bgcolor: isDone ? 'success.main' + '20' : isActive ? 'primary.main' + '20' : 'transparent',
            }}>
              {isDone ? <CheckIcon sx={{ fontSize: 12, color: 'success.main' }} />
                : isActive ? <CircularProgress size={10} thickness={5} />
                : <Typography variant="caption" color="text.disabled">{i + 1}</Typography>}
            </Box>
            <Typography variant="body2" color={isDone ? 'text.secondary' : isActive ? 'text.primary' : 'text.disabled'}
              fontWeight={isActive ? 600 : 400}>
              {step.label}
            </Typography>
          </Paper>
        )
      })}
    </Box>
  )
}
```

- [ ] **Step 6: Create `frontend/src/components/LogPanel.tsx`**

```tsx
import { useEffect, useRef } from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'

export default function LogPanel({ lines, height = 280 }: { lines: string[]; height?: number | string }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => { ref.current?.scrollIntoView({ behavior: 'smooth' }) }, [lines])

  return (
    <Box sx={{
      bgcolor: '#111827', border: '1px solid #1f2937', borderRadius: 1,
      p: 1.5, height, overflowY: 'auto',
      fontFamily: '"Fira Code", "Courier New", monospace',
    }}>
      {lines.length === 0
        ? <Typography variant="caption" color="text.disabled">Waiting for output...</Typography>
        : lines.map((line, i) => (
            <Typography key={i} variant="caption" component="div" sx={{ lineHeight: 1.7, color: '#94a3b8', whiteSpace: 'pre-wrap' }}>
              {line}
            </Typography>
          ))
      }
      <div ref={ref} />
    </Box>
  )
}
```

- [ ] **Step 7: Implement `frontend/src/pages/PipelinePage.tsx`**

```tsx
import { useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import Alert from '@mui/material/Alert'
import BoltIcon from '@mui/icons-material/Bolt'
import { pipelineApi } from '../api/pipeline'
import { usePipelineContext } from '../store/PipelineContext'
import { useJobState } from '../hooks/useJobState'
import { useSSE } from '../hooks/useSSE'
import StepTracker from '../components/StepTracker'
import LogPanel from '../components/LogPanel'

export default function PipelinePage() {
  const { activeJobId, isRunning, setActiveJob, setRunning } = usePipelineContext()
  const [logLines, setLogLines] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const jobState = useJobState(activeJobId)

  useSSE(
    activeJobId && isRunning ? pipelineApi.streamUrl(activeJobId) : null,
    (line) => setLogLines(prev => [...prev, line]),
    () => setRunning(false),
  )

  const handleRun = async () => {
    setError(null); setLogLines([])
    try {
      const { job_id } = await pipelineApi.run()
      setActiveJob(job_id); setRunning(true)
    } catch (e: any) {
      setError(e.response?.data?.detail ?? 'Failed to start pipeline')
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" fontWeight={700}>Pipeline</Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Paper variant="outlined" sx={{ p: 2, mb: 2, display: 'flex', alignItems: 'center', gap: 2, borderColor: 'primary.main' + '40', bgcolor: 'primary.main' + '08' }}>
        <Box sx={{ flex: 1 }}>
          <Typography variant="body2" fontWeight={700}>{activeJobId ?? 'Ready to run'}</Typography>
          <Typography variant="caption" color="text.secondary">
            {isRunning ? 'Pipeline running...' : activeJobId ? 'Completed' : 'Runs the next topic in the approved queue (~5–8 min)'}
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<BoltIcon />} disabled={isRunning} onClick={handleRun}>
          {isRunning ? 'Running...' : 'Run Pipeline'}
        </Button>
      </Paper>

      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}>Steps</Typography>
          <StepTracker completedSteps={jobState?.completed_steps ?? []} isRunning={isRunning} />
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}>
            Live Log {isRunning && <span style={{ color: '#4f79ff' }}>● LIVE</span>}
          </Typography>
          <LogPanel lines={logLines} height={340} />
        </Box>
      </Box>
    </Box>
  )
}
```

- [ ] **Step 8: Add PipelineProvider to `frontend/src/App.tsx`**

```tsx
import { RouterProvider } from 'react-router-dom'
import { ThemeProvider, CssBaseline } from '@mui/material'
import { theme } from './theme'
import { router } from './router'
import { PipelineProvider } from './store/PipelineContext'

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <PipelineProvider>
        <RouterProvider router={router} />
      </PipelineProvider>
    </ThemeProvider>
  )
}
```

- [ ] **Step 9: Manual test**

1. Add a topic to `topics/queue.json`:
```json
[{"id": "t1", "title": "AK-47 Myths", "tier": 1, "tier_score": 9}]
```
2. Navigate to Pipeline page → click Run Pipeline
3. Verify job ID appears, step 1 shows as running
4. Watch log panel for lines

- [ ] **Step 10: Commit**

```bash
git add frontend/
git commit -m "feat: Pipeline page — step tracker, SSE live log, run button, PipelineContext"
```

---

### Task 8: Publish Page

**Files:**
- Create: `frontend/src/api/publish.ts`
- Create: `frontend/src/store/PublishContext.tsx`
- Modify: `frontend/src/pages/PublishPage.tsx`
- Modify: `frontend/src/App.tsx` — add PublishProvider

- [ ] **Step 1: Create `frontend/src/api/publish.ts`**

```ts
import client from './client'
import type { Metadata, UploadWindow } from '../types'

export const publishApi = {
  getWindow: () => client.get<UploadWindow>('/publish/window').then(r => r.data),
  getMetadata: (jobId: string) => client.get<Metadata>(`/publish/${jobId}/metadata`).then(r => r.data),
  upload: (jobId: string, dryRun = false) =>
    client.post(`/publish/${jobId}/upload`, null, { params: { dry_run: dryRun } }).then(r => r.data),
  streamUrl: (jobId: string) => `/api/v1/publish/${jobId}/stream`,
}
```

- [ ] **Step 2: Create `frontend/src/store/PublishContext.tsx`**

```tsx
import { createContext, useContext, useState } from 'react'

const GATE_ITEMS = [
  'Video plays start to finish without issues',
  'Hook lands in the first 3 seconds',
  'Captions are readable and accurate',
  'No copyrighted music or footage',
  'Loop is seamless (first = last clip)',
]

interface Ctx {
  jobId: string | null; setJobId: (id: string | null) => void
  checks: boolean[]; toggleCheck: (i: number) => void
  allChecked: boolean; gateItems: string[]; resetChecks: () => void
}

const PublishContext = createContext<Ctx | null>(null)

export function PublishProvider({ children }: { children: React.ReactNode }) {
  const [jobId, setJobId] = useState<string | null>(null)
  const [checks, setChecks] = useState<boolean[]>(Array(GATE_ITEMS.length).fill(false))
  const toggleCheck = (i: number) => setChecks(p => p.map((v, idx) => idx === i ? !v : v))
  const resetChecks = () => setChecks(Array(GATE_ITEMS.length).fill(false))
  return (
    <PublishContext.Provider value={{ jobId, setJobId, checks, toggleCheck, allChecked: checks.every(Boolean), gateItems: GATE_ITEMS, resetChecks }}>
      {children}
    </PublishContext.Provider>
  )
}

export function usePublishContext() {
  const ctx = useContext(PublishContext)
  if (!ctx) throw new Error('usePublishContext must be inside PublishProvider')
  return ctx
}
```

- [ ] **Step 3: Implement `frontend/src/pages/PublishPage.tsx`**

```tsx
import { useCallback, useEffect, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import Paper from '@mui/material/Paper'
import FormControlLabel from '@mui/material/FormControlLabel'
import Checkbox from '@mui/material/Checkbox'
import Alert from '@mui/material/Alert'
import Chip from '@mui/material/Chip'
import TextField from '@mui/material/TextField'
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch'
import { usePublishContext } from '../store/PublishContext'
import { publishApi } from '../api/publish'
import { useSSE } from '../hooks/useSSE'
import LogPanel from '../components/LogPanel'
import type { Metadata, UploadWindow } from '../types'

export default function PublishPage() {
  const { jobId, setJobId, checks, toggleCheck, allChecked, gateItems, resetChecks } = usePublishContext()
  const [window_, setWindow_] = useState<UploadWindow | null>(null)
  const [metadata, setMetadata] = useState<Metadata | null>(null)
  const [uploading, setUploading] = useState(false)
  const [streamJobId, setStreamJobId] = useState<string | null>(null)
  const [logLines, setLogLines] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    publishApi.getWindow().then(setWindow_)
    const id = setInterval(() => publishApi.getWindow().then(setWindow_), 60000)
    return () => clearInterval(id)
  }, [])

  const loadMeta = useCallback(async (id: string) => {
    try { setMetadata(await publishApi.getMetadata(id)) }
    catch { setMetadata(null) }
  }, [])

  useEffect(() => { if (jobId) loadMeta(jobId); else setMetadata(null) }, [jobId, loadMeta])

  useSSE(streamJobId ? publishApi.streamUrl(streamJobId) : null,
    (line) => setLogLines(p => [...p, line]),
    () => setUploading(false))

  const handleJobChange = (val: string) => {
    setJobId(val || null); resetChecks(); setLogLines([]); setError(null)
  }

  const handleUpload = async () => {
    if (!jobId || !allChecked) return
    setError(null); setLogLines([]); setUploading(true)
    try { await publishApi.upload(jobId); setStreamJobId(jobId) }
    catch (e: any) { setError(e.response?.data?.detail ?? 'Upload failed'); setUploading(false) }
  }

  const nextWindowStr = window_?.next_window
    ? new Date(window_.next_window).toLocaleString('en-US', { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' })
    : '...'

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" fontWeight={700}>Publish</Typography>
        <Button variant="outlined" size="small" disabled={!jobId}
          onClick={() => jobId && publishApi.upload(jobId, true)}>Dry Run</Button>
      </Box>

      <TextField label="Job ID" size="small" value={jobId ?? ''} placeholder="job-20260526-143021"
        onChange={e => handleJobChange(e.target.value)} sx={{ mb: 2, width: 300 }} />

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 3 }}>
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}>
            Pre-Upload Checklist
          </Typography>
          <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
            {gateItems.map((item, i) => (
              <Box key={i} sx={{ borderBottom: i < gateItems.length - 1 ? '1px solid' : 'none', borderColor: 'divider', py: 0.5 }}>
                <FormControlLabel control={<Checkbox size="small" checked={checks[i]} onChange={() => toggleCheck(i)} />}
                  label={<Typography variant="body2">{item}</Typography>} />
              </Box>
            ))}
          </Paper>

          {window_ && (
            <Alert severity={window_.in_window ? 'success' : 'warning'} sx={{ mb: 2 }}>
              {window_.in_window ? 'In optimal upload window now' : `Next window: ${nextWindowStr}`}
            </Alert>
          )}

          <Button variant="contained" size="large" startIcon={<RocketLaunchIcon />}
            disabled={!allChecked || uploading || !jobId} onClick={handleUpload}
            sx={{ background: 'linear-gradient(135deg, #4f79ff, #7c3aed)' }}>
            {uploading ? 'Uploading...' : 'Upload to YouTube'}
          </Button>
          {!allChecked && <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Complete checklist to enable upload
          </Typography>}
        </Box>

        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}>
            Metadata Preview
          </Typography>
          {metadata ? (
            <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
              <Typography variant="caption" color="text.secondary">Title</Typography>
              <Typography variant="body2" fontWeight={600} sx={{ mb: 1.5 }}>{metadata.title}</Typography>
              <Typography variant="caption" color="text.secondary">Description</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, fontSize: 11 }}>{metadata.description}</Typography>
              <Typography variant="caption" color="text.secondary">Tags</Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5, mb: 1.5 }}>
                {metadata.tags.map(tag => <Chip key={tag} label={tag} size="small" />)}
              </Box>
              <Typography variant="caption" color="text.secondary">Pinned Comment</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ fontSize: 11 }}>{metadata.pinned_comment}</Typography>
            </Paper>
          ) : (
            <Typography variant="body2" color="text.secondary">Enter a job ID to preview metadata.</Typography>
          )}
          {logLines.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}>Upload Log</Typography>
              <LogPanel lines={logLines} height={180} />
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  )
}
```

- [ ] **Step 4: Add PublishProvider to `frontend/src/App.tsx`**

```tsx
import { RouterProvider } from 'react-router-dom'
import { ThemeProvider, CssBaseline } from '@mui/material'
import { theme } from './theme'
import { router } from './router'
import { PipelineProvider } from './store/PipelineContext'
import { PublishProvider } from './store/PublishContext'

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <PipelineProvider>
        <PublishProvider>
          <RouterProvider router={router} />
        </PublishProvider>
      </PipelineProvider>
    </ThemeProvider>
  )
}
```

- [ ] **Step 5: Manual test**

Create `metadata/job-test/metadata.json`:
```json
{"title": "Test Title #shorts", "description": "Test desc.", "tags": ["test", "shorts", "military"], "pinned_comment": "AI-generated content."}
```

Open Publish page → enter `job-test` → verify metadata preview. Check all 5 boxes → Upload button enables. Verify window banner shows correct status.

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: Publish page — checklist gate, metadata preview, upload window, SSE log"
```

---

### Task 9: Analytics Page

**Files:**
- Create: `frontend/src/api/analytics.ts`
- Modify: `frontend/src/pages/AnalyticsPage.tsx`

- [ ] **Step 1: Create `frontend/src/api/analytics.ts`**

```ts
import client from './client'
import type { AnalyticsReport } from '../types'

export const analyticsApi = {
  getReport: (jobId: string) => client.get<AnalyticsReport>(`/analytics/${jobId}`).then(r => r.data),
  pull: (jobId: string) => client.post(`/analytics/${jobId}/pull`).then(r => r.data),
}
```

- [ ] **Step 2: Implement `frontend/src/pages/AnalyticsPage.tsx`**

```tsx
import { useEffect, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import Paper from '@mui/material/Paper'
import TextField from '@mui/material/TextField'
import Alert from '@mui/material/Alert'
import LinearProgress from '@mui/material/LinearProgress'
import RefreshIcon from '@mui/icons-material/Refresh'
import { analyticsApi } from '../api/analytics'
import type { AnalyticsReport } from '../types'

const FLAG_COLOR = { GREEN: 'success', YELLOW: 'warning', RED: 'error' } as const
const FLAG_EMOJI = { GREEN: '🟢', YELLOW: '🟡', RED: '🔴' }

export default function AnalyticsPage() {
  const [jobId, setJobId] = useState('')
  const [report, setReport] = useState<AnalyticsReport | null>(null)
  const [pulling, setPulling] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = async (id: string) => {
    setError(null)
    try { setReport(await analyticsApi.getReport(id)) }
    catch { setReport(null); setError('No report found. Click Pull Latest to fetch.') }
  }

  useEffect(() => { if (jobId) load(jobId) }, [jobId])

  const handlePull = async () => {
    if (!jobId) return
    setPulling(true); setError(null)
    try {
      await analyticsApi.pull(jobId)
      setTimeout(() => load(jobId).finally(() => setPulling(false)), 5000)
    } catch { setError('Failed to pull analytics'); setPulling(false) }
  }

  const usPct = report ? Math.round(report.us_share * 100) : 0
  const countries = report?.country_breakdown
    ? Object.entries(report.country_breakdown).sort((a, b) => b[1] - a[1]).slice(0, 6)
    : []

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" fontWeight={700}>Analytics</Typography>
        <Button variant="contained" startIcon={<RefreshIcon />} disabled={!jobId || pulling} onClick={handlePull}>
          {pulling ? 'Pulling...' : 'Pull Latest'}
        </Button>
      </Box>

      <TextField label="Job ID" size="small" value={jobId} placeholder="job-20260526-143021"
        onChange={e => setJobId(e.target.value)} sx={{ mb: 2, width: 300 }} />

      {error && <Alert severity="info" sx={{ mb: 2 }}>{error}</Alert>}

      {report && (
        <Box>
          <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
            <Paper variant="outlined" sx={{
              p: 3, width: 180, textAlign: 'center', flexShrink: 0,
              borderColor: `${FLAG_COLOR[report.flag]}.main`,
              bgcolor: `${FLAG_COLOR[report.flag]}.main` + '08',
            }}>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>
                US Audience Share
              </Typography>
              <Typography variant="h3" fontWeight={800} color={`${FLAG_COLOR[report.flag]}.main`} sx={{ my: 1 }}>
                {usPct}%
              </Typography>
              <Typography variant="caption" color={`${FLAG_COLOR[report.flag]}.main`} fontWeight={700}>
                {FLAG_EMOJI[report.flag]} {report.flag}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>Target: 50%+</Typography>
            </Paper>

            <Paper variant="outlined" sx={{ flex: 1, p: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1.5, display: 'block' }}>
                Report Details
              </Typography>
              {report.notes && <Typography variant="body2" color="text.secondary">{report.notes}</Typography>}
            </Paper>
          </Box>

          {countries.length > 0 && (
            <>
              <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', letterSpacing: 0.5, mb: 1, display: 'block' }}>
                Country Breakdown
              </Typography>
              <Paper variant="outlined">
                {countries.map(([country, share], i) => {
                  const pct = Math.round(share * 100)
                  return (
                    <Box key={country} sx={{
                      display: 'grid', gridTemplateColumns: '140px 60px 1fr',
                      alignItems: 'center', gap: 2, p: 1.5,
                      borderBottom: i < countries.length - 1 ? '1px solid' : 'none', borderColor: 'divider',
                    }}>
                      <Typography variant="body2">{country}</Typography>
                      <Typography variant="body2" fontWeight={600} color={country === 'US' ? 'success.main' : 'text.primary'}>
                        {pct}%
                      </Typography>
                      <LinearProgress variant="determinate" value={pct}
                        color={country === 'US' ? 'success' : 'primary'}
                        sx={{ height: 4, borderRadius: 2 }} />
                    </Box>
                  )
                })}
              </Paper>
            </>
          )}
        </Box>
      )}
    </Box>
  )
}
```

- [ ] **Step 3: Manual test**

Create `compliance-logs/job-test/audience-report.json`:
```json
{
  "us_share": 0.62,
  "flag": "GREEN",
  "notes": "Strong US audience performance.",
  "country_breakdown": {"US": 0.62, "GB": 0.11, "CA": 0.09, "AU": 0.06, "DE": 0.05, "Other": 0.07}
}
```

Open Analytics page → enter `job-test` → verify 62% GREEN flag card, country bars.

- [ ] **Step 4: Run all backend tests**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts
python -m pytest backend/tests/ -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: Analytics page — US share flag card, country breakdown, pull latest"
```

---

*Self-review — spec coverage check:*
- *Topics: pending list, queue list, approve/reject buttons, generate → ✅*
- *Pipeline: run button, 6-step tracker (keys match state.json), SSE live log → ✅*
- *Publish: 5-item checklist, upload button gate, metadata preview, window banner, SSE upload log → ✅*
- *Publish gate: backend writes pre_upload_gate to state.json before launching publish.py → ✅*
- *Analytics: US share %, GREEN/YELLOW/RED flag, country breakdown bars, pull latest → ✅*
- *AppShell sidebar nav (Approach A) → ✅*
- *SSE navigate-away: subprocess keeps running, reconnect works via log file tail → ✅*
- *pending.json staging: append_to_staging() in generate_topics.py → ✅*
- *All 14 backend API endpoints → ✅*
