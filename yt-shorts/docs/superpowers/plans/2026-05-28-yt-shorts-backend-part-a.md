# YT Shorts Backend Part A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Topics, Script, Compliance, and Voiceover endpoints for the YT Shorts pipeline — Steps 1–5 of the automation pipeline.

**Architecture:** Each pipeline step gets its own service (pure business logic, no HTTP), its own router (thin HTTP handler), and its own Pydantic models. Services take API keys/config as parameters so they can be tested without hitting external APIs. Routers inject `ProjectStore` and `Settings` via `Depends()`. Project state is mutated on each advance (`store.update`).

**Tech Stack:** FastAPI, Pydantic v2, `anthropic` (Claude API), `elevenlabs` (ElevenLabs v1 SDK), pytest, `unittest.mock`.

**Context you need:**
- Domain: Military/historical weapons education channel. Scripts follow Hook → Validation → Truth → Final Twist structure. 120–160 words per script. US-audience targeted.
- Compliance thresholds: originality >= 7/10, advertiser-friendliness >= 8/10. Below threshold → `REVISION_REQUIRED`.
- Voiceover: ElevenLabs, stability=0.70, similarity_boost=0.82, style=0.37, speaker_boost=True, output_format `mp3_44100_192`.
- Project state is stored as JSON at `.tmp/projects/{id}/state.json` via `ProjectStore`. All step outputs are stored under the project as fields.
- Existing code: `backend/config.py` (Settings with `anthropic_api_key`, `elevenlabs_api_key`), `backend/core/store.py` (`ProjectStore`, `get_store`), `backend/features/yt_shorts/models/project.py` (Project, ProjectStep), `backend/features/yt_shorts/routers/projects.py` (CRUD), `backend/features/yt_shorts/router.py` (registers sub-routers).

---

## File Map

### Created
- `backend/features/yt_shorts/models/topic.py` — `Topic` Pydantic model
- `backend/features/yt_shorts/models/script.py` — `ScriptSentence`, `Script`, `ComplianceReport`, `ScriptResponse`
- `backend/features/yt_shorts/models/voiceover.py` — `Voiceover`
- `backend/features/yt_shorts/services/topics.py` — `generate_topics(api_key) -> list[Topic]`
- `backend/features/yt_shorts/services/script.py` — `generate_script(api_key, title, misconception) -> tuple[Script, dict]`
- `backend/features/yt_shorts/services/compliance.py` — `check_compliance(script, ...) -> ComplianceReport`
- `backend/features/yt_shorts/services/voiceover.py` — `generate_voiceover(text, api_key, voice_id, output_path) -> Voiceover`
- `backend/features/yt_shorts/routers/topics.py`
- `backend/features/yt_shorts/routers/script.py`
- `backend/features/yt_shorts/routers/voiceover.py`
- Test files for all of the above

### Modified
- `backend/requirements.txt` — add `anthropic>=0.40.0`, `elevenlabs>=1.0.0`
- `backend/config.py` — add `elevenlabs_voice_id: str = ""`
- `backend/features/yt_shorts/models/project.py` — add `topics: list[dict] = []`
- `backend/features/yt_shorts/routers/projects.py` — add `"topics": []` to `_initial_state`
- `backend/features/yt_shorts/router.py` — register topics, script, voiceover sub-routers

---

## Task 1: Add `topics` Field to Project Model

**Files:**
- Modify: `backend/features/yt_shorts/models/project.py`
- Modify: `backend/features/yt_shorts/routers/projects.py`
- Modify: `backend/tests/features/yt_shorts/test_project_models.py`
- Modify: `backend/tests/features/yt_shorts/test_projects_router.py`

- [ ] **Step 1: Update the Project model**

In `backend/features/yt_shorts/models/project.py`, add `topics: list[dict] = []` after the `updated_at` field and before `approved_topic`:

```python
from enum import Enum
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


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
    topics: list[dict] = []
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

- [ ] **Step 2: Update `_initial_state` in projects router**

In `backend/features/yt_shorts/routers/projects.py`, add `"topics": []` to the dict returned by `_initial_state`:

```python
def _initial_state(title: str) -> dict:
    return {
        "title": title,
        "current_step": ProjectStep.TOPICS,
        "topics": [],
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
```

- [ ] **Step 3: Update the project model test to check the new field**

In `backend/tests/features/yt_shorts/test_project_models.py`, update `test_project_defaults` to assert `topics == []`:

```python
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
```

- [ ] **Step 4: Run all existing tests to confirm nothing broke**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts
.venv/Scripts/python -m pytest backend/tests/ -v
```

Expected: all 32 tests pass (plus the updated model test).

- [ ] **Step 5: Commit**

```bash
git add backend/features/yt_shorts/models/project.py backend/features/yt_shorts/routers/projects.py backend/tests/features/yt_shorts/test_project_models.py
git commit -m "feat: add topics list field to Project model"
```

---

## Task 2: Topic Pydantic Models

**Files:**
- Create: `backend/features/yt_shorts/models/topic.py`
- Create: `backend/tests/features/yt_shorts/test_topic_models.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/features/yt_shorts/test_topic_models.py`:

```python
from backend.features.yt_shorts.models.topic import Topic


def test_topic_defaults_to_pending():
    topic = Topic(
        id="t1",
        title="Why snipers never aim for center mass",
        misconception="Movies always show chest shots",
        real_answer="Real snipers target the medulla oblongata for instant stop",
        us_curiosity_score=9,
    )
    assert topic.status == "pending"


def test_topic_serializes_correctly():
    topic = Topic(
        id="t1",
        title="Test title",
        misconception="Test misconception",
        real_answer="Test answer",
        us_curiosity_score=8,
    )
    data = topic.model_dump()
    assert data["id"] == "t1"
    assert data["status"] == "pending"
    assert data["us_curiosity_score"] == 8


def test_topic_approved_status():
    topic = Topic(
        id="t2",
        title="Test",
        misconception="X",
        real_answer="Y",
        us_curiosity_score=7,
        status="approved",
    )
    assert topic.status == "approved"
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_topic_models.py -v
```

Expected: `ImportError` — module not found.

- [ ] **Step 3: Create `backend/features/yt_shorts/models/topic.py`**

```python
from pydantic import BaseModel, ConfigDict
from typing import Literal


class Topic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    misconception: str
    real_answer: str
    us_curiosity_score: int
    status: Literal["pending", "approved"] = "pending"
```

- [ ] **Step 4: Run test — expect PASS**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_topic_models.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/features/yt_shorts/models/topic.py backend/tests/features/yt_shorts/test_topic_models.py
git commit -m "feat: add Topic Pydantic model"
```

---

## Task 3: Topic Generation Service

**Files:**
- Create: `backend/features/yt_shorts/services/topics.py`
- Create: `backend/tests/features/yt_shorts/test_topics_service.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add `anthropic` to requirements.txt**

Open `backend/requirements.txt` and add:

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
pydantic==2.10.3
pydantic-settings==2.6.1
python-dotenv==1.0.1
httpx==0.27.2
pytest==9.0.3
pytest-asyncio==0.25.2
anthropic>=0.40.0
```

Then install it:

```bash
cd E:/digital-sorcery/master-planner/yt-shorts
.venv/Scripts/pip install anthropic>=0.40.0
```

- [ ] **Step 2: Write the failing tests**

Create `backend/tests/features/yt_shorts/test_topics_service.py`:

```python
import json
from unittest.mock import MagicMock, patch
from backend.features.yt_shorts.services.topics import generate_topics

_MOCK_TOPICS = {
    "topics": [
        {
            "title": f"Why do real snipers never target the chest — {i}",
            "misconception": "Movies show center-mass shots",
            "real_answer": "CNS targeting for instant incapacitation",
            "us_curiosity_score": 10 - i,
        }
        for i in range(10)
    ]
}


def _mock_anthropic(mock_class: MagicMock, response_json: dict) -> MagicMock:
    mock_client = MagicMock()
    mock_class.return_value = mock_client
    mock_client.messages.create.return_value.content[0].text = json.dumps(response_json)
    return mock_client


def test_generate_topics_returns_ten():
    with patch("backend.features.yt_shorts.services.topics.Anthropic") as MockClass:
        _mock_anthropic(MockClass, _MOCK_TOPICS)
        topics = generate_topics("fake-key")
        assert len(topics) == 10


def test_generate_topics_assigns_unique_ids():
    with patch("backend.features.yt_shorts.services.topics.Anthropic") as MockClass:
        _mock_anthropic(MockClass, _MOCK_TOPICS)
        topics = generate_topics("fake-key")
        ids = [t.id for t in topics]
        assert len(set(ids)) == 10


def test_generate_topics_status_is_pending():
    with patch("backend.features.yt_shorts.services.topics.Anthropic") as MockClass:
        _mock_anthropic(MockClass, _MOCK_TOPICS)
        topics = generate_topics("fake-key")
        assert all(t.status == "pending" for t in topics)


def test_generate_topics_uses_api_key():
    with patch("backend.features.yt_shorts.services.topics.Anthropic") as MockClass:
        mock_client = _mock_anthropic(MockClass, _MOCK_TOPICS)
        generate_topics("my-real-key")
        MockClass.assert_called_once_with(api_key="my-real-key")
```

- [ ] **Step 3: Run tests — expect FAIL**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_topics_service.py -v
```

Expected: `ImportError` — module not found.

- [ ] **Step 4: Create `backend/features/yt_shorts/services/topics.py`**

```python
import json
import uuid
from anthropic import Anthropic
from backend.features.yt_shorts.models.topic import Topic

_PROMPT = """Generate exactly 10 YouTube Shorts topic ideas for a military and historical weapons education channel targeting US audiences.

Respond with valid JSON only — no markdown, no prose:
{
  "topics": [
    {
      "title": "Why do real snipers never aim for center mass?",
      "misconception": "Movies always show snipers targeting the chest",
      "real_answer": "Real snipers target the medulla oblongata for instant incapacitation",
      "us_curiosity_score": 9
    }
  ]
}

Requirements:
- Exactly 10 topics
- Title formula: "Why do real [X] actually [Y]?" or "Why [common assumption] is completely wrong?"
- Focus: firearms engineering, historical warrior weapons, military tactics, equipment design, combat technology
- Avoid: active ongoing conflicts, graphic casualties, named political figures
- Sort by us_curiosity_score descending"""


def generate_topics(api_key: str) -> list[Topic]:
    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": _PROMPT}],
    )
    raw = json.loads(message.content[0].text)
    return [Topic(id=str(uuid.uuid4()), **item) for item in raw["topics"]]
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_topics_service.py -v
```

Expected: `4 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/features/yt_shorts/services/topics.py backend/tests/features/yt_shorts/test_topics_service.py backend/requirements.txt
git commit -m "feat: add topic generation service (Claude API)"
```

---

## Task 4: Topics Router

**Files:**
- Create: `backend/features/yt_shorts/routers/topics.py`
- Create: `backend/tests/features/yt_shorts/test_topics_router.py`
- Modify: `backend/features/yt_shorts/router.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/features/yt_shorts/test_topics_router.py`:

```python
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch
from backend.core.store import ProjectStore, get_store
from backend.config import get_settings, Settings
from backend.features.yt_shorts.routers.topics import router
from backend.features.yt_shorts.models.topic import Topic


def _make_topic(i: int = 0) -> Topic:
    return Topic(
        id=f"topic-{i}",
        title=f"Why snipers never {i}",
        misconception="Movies show center mass",
        real_answer="CNS targeting",
        us_curiosity_score=9 - i,
    )


@pytest.fixture
def setup(tmp_path):
    store = ProjectStore(base_dir=str(tmp_path))
    project = store.create({
        "title": "Test Video",
        "current_step": "topics",
        "topics": [],
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
    })
    project_id = project["id"]

    app = FastAPI()
    app.include_router(router, prefix="/projects/{project_id}/topics")
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: Settings(anthropic_api_key="test-key")

    return TestClient(app), project_id, store


def test_generate_topics_returns_list(setup):
    client, project_id, _ = setup
    mock_topics = [_make_topic(i) for i in range(10)]

    with patch("backend.features.yt_shorts.routers.topics.generate_topics") as mock_gen:
        mock_gen.return_value = mock_topics
        response = client.post(f"/projects/{project_id}/topics/generate")

    assert response.status_code == 200
    assert len(response.json()) == 10


def test_generate_topics_stores_in_project(setup):
    client, project_id, store = setup
    mock_topics = [_make_topic(i) for i in range(3)]

    with patch("backend.features.yt_shorts.routers.topics.generate_topics") as mock_gen:
        mock_gen.return_value = mock_topics
        client.post(f"/projects/{project_id}/topics/generate")

    project = store.get(project_id)
    assert len(project["topics"]) == 3


def test_generate_topics_project_not_found(setup):
    client, _, _ = setup

    with patch("backend.features.yt_shorts.routers.topics.generate_topics") as mock_gen:
        mock_gen.return_value = []
        response = client.post("/projects/nonexistent/topics/generate")

    assert response.status_code == 404


def test_list_topics_empty(setup):
    client, project_id, _ = setup
    response = client.get(f"/projects/{project_id}/topics")
    assert response.status_code == 200
    assert response.json() == []


def test_list_topics_after_generate(setup):
    client, project_id, _ = setup
    mock_topics = [_make_topic(i) for i in range(5)]

    with patch("backend.features.yt_shorts.routers.topics.generate_topics") as mock_gen:
        mock_gen.return_value = mock_topics
        client.post(f"/projects/{project_id}/topics/generate")

    response = client.get(f"/projects/{project_id}/topics")
    assert response.status_code == 200
    assert len(response.json()) == 5


def test_approve_topic_returns_approved(setup):
    client, project_id, _ = setup
    mock_topics = [_make_topic(0), _make_topic(1)]

    with patch("backend.features.yt_shorts.routers.topics.generate_topics") as mock_gen:
        mock_gen.return_value = mock_topics
        client.post(f"/projects/{project_id}/topics/generate")

    topic_id = mock_topics[0].id
    response = client.post(f"/projects/{project_id}/topics/{topic_id}/approve")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == topic_id
    assert data["status"] == "approved"


def test_approve_topic_advances_step_to_script(setup):
    client, project_id, store = setup
    mock_topics = [_make_topic(0)]

    with patch("backend.features.yt_shorts.routers.topics.generate_topics") as mock_gen:
        mock_gen.return_value = mock_topics
        client.post(f"/projects/{project_id}/topics/generate")

    topic_id = mock_topics[0].id
    client.post(f"/projects/{project_id}/topics/{topic_id}/approve")

    project = store.get(project_id)
    assert project["current_step"] == "script"
    assert project["approved_topic"]["id"] == topic_id


def test_approve_nonexistent_topic(setup):
    client, project_id, _ = setup
    response = client.post(f"/projects/{project_id}/topics/fake-id/approve")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_topics_router.py -v
```

Expected: `ImportError` — router not found.

- [ ] **Step 3: Create `backend/features/yt_shorts/routers/topics.py`**

```python
from fastapi import APIRouter, HTTPException, Depends
from backend.core.store import ProjectStore, get_store
from backend.config import get_settings, Settings
from backend.features.yt_shorts.models.topic import Topic
from backend.features.yt_shorts.services.topics import generate_topics

router = APIRouter(tags=["yt-shorts-topics"])


@router.post("/generate", response_model=list[Topic])
def generate_topics_endpoint(
    project_id: str,
    store: ProjectStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    topics = generate_topics(settings.anthropic_api_key)
    store.update(project_id, {"topics": [t.model_dump() for t in topics]})
    return topics


@router.get("", response_model=list[Topic])
def list_topics(
    project_id: str,
    store: ProjectStore = Depends(get_store),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.get("topics", [])


@router.post("/{topic_id}/approve", response_model=Topic)
def approve_topic(
    project_id: str,
    topic_id: str,
    store: ProjectStore = Depends(get_store),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    topics = project.get("topics", [])
    topic = next((t for t in topics if t["id"] == topic_id), None)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    topic["status"] = "approved"
    store.update(project_id, {
        "topics": topics,
        "approved_topic": topic,
        "current_step": "script",
    })
    return topic
```

- [ ] **Step 4: Update `backend/features/yt_shorts/router.py`**

```python
from fastapi import APIRouter
from backend.features.yt_shorts.routers import projects, topics

router = APIRouter(prefix="/yt-shorts")
router.include_router(projects.router, prefix="/projects")
router.include_router(topics.router, prefix="/projects/{project_id}/topics")
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_topics_router.py -v
```

Expected: `7 passed`

- [ ] **Step 6: Run full suite to confirm no regressions**

```bash
.venv/Scripts/python -m pytest backend/tests/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/features/yt_shorts/routers/topics.py backend/tests/features/yt_shorts/test_topics_router.py backend/features/yt_shorts/router.py
git commit -m "feat: add topics router (generate, list, approve)"
```

---

## Task 5: Script Pydantic Models

**Files:**
- Create: `backend/features/yt_shorts/models/script.py`
- Create: `backend/tests/features/yt_shorts/test_script_models.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/features/yt_shorts/test_script_models.py`:

```python
from backend.features.yt_shorts.models.script import (
    Script,
    ScriptSentence,
    ComplianceReport,
    ScriptResponse,
)


def _make_sentence(i: int = 0) -> ScriptSentence:
    return ScriptSentence(
        id=f"s{i}",
        text=f"Sentence {i} text here.",
        pexels_query=f"military weapon {i}",
        pixabay_query=f"army equipment {i}",
        ai_needed=False,
        keyword_overlay=f"WEAPON{i}",
    )


def test_script_sentence_defaults():
    s = _make_sentence(0)
    assert s.ai_needed is False
    assert s.ai_prompt is None


def test_script_defaults_to_draft():
    sentences = [_make_sentence(i) for i in range(4)]
    script = Script(
        sentences=sentences,
        full_text="Hook. Validation. Truth. Twist.",
        originality_score=8,
        advertiser_friendliness_score=9,
        us_resonance_score=8,
        music_mood="tense, dramatic",
    )
    assert script.status == "draft"


def test_script_serializes():
    sentences = [_make_sentence(0)]
    script = Script(
        sentences=sentences,
        full_text="Test sentence.",
        originality_score=8,
        advertiser_friendliness_score=9,
        us_resonance_score=7,
        music_mood="intense",
    )
    data = script.model_dump()
    assert data["status"] == "draft"
    assert data["originality_score"] == 8
    assert len(data["sentences"]) == 1


def test_compliance_report_passed_flag():
    report = ComplianceReport(
        originality_score=8,
        advertiser_friendliness_score=9,
        originality_status="PASS",
        advertiser_status="PASS",
        sensitive_content="CLEAR",
        ai_disclosure_required=True,
        passed=True,
    )
    assert report.passed is True
    assert report.sensitive_content_details is None


def test_script_response_wraps_both():
    sentences = [_make_sentence(0)]
    script = Script(
        sentences=sentences,
        full_text="Test.",
        originality_score=8,
        advertiser_friendliness_score=9,
        us_resonance_score=8,
        music_mood="dark",
    )
    report = ComplianceReport(
        originality_score=8,
        advertiser_friendliness_score=9,
        originality_status="PASS",
        advertiser_status="PASS",
        sensitive_content="CLEAR",
        ai_disclosure_required=True,
        passed=True,
    )
    resp = ScriptResponse(script=script, compliance=report)
    assert resp.script.status == "draft"
    assert resp.compliance.passed is True
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_script_models.py -v
```

Expected: `ImportError` — module not found.

- [ ] **Step 3: Create `backend/features/yt_shorts/models/script.py`**

```python
from pydantic import BaseModel, ConfigDict
from typing import Literal, Optional


class ScriptSentence(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    text: str
    pexels_query: str
    pixabay_query: str
    ai_needed: bool
    ai_prompt: Optional[str] = None
    keyword_overlay: str


class Script(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sentences: list[ScriptSentence]
    full_text: str
    originality_score: int
    advertiser_friendliness_score: int
    us_resonance_score: int
    music_mood: str
    status: Literal["draft", "approved"] = "draft"


class ComplianceReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    originality_score: int
    advertiser_friendliness_score: int
    originality_status: Literal["PASS", "REVISION_REQUIRED"]
    advertiser_status: Literal["PASS", "REVISION_REQUIRED"]
    sensitive_content: Literal["CLEAR", "FLAG"]
    sensitive_content_details: Optional[str] = None
    ai_disclosure_required: bool
    passed: bool
    revision_notes: Optional[str] = None


class ScriptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    script: Script
    compliance: Optional[ComplianceReport] = None
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_script_models.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/features/yt_shorts/models/script.py backend/tests/features/yt_shorts/test_script_models.py
git commit -m "feat: add Script, ScriptSentence, ComplianceReport, ScriptResponse models"
```

---

## Task 6: Script Generation Service

**Files:**
- Create: `backend/features/yt_shorts/services/script.py`
- Create: `backend/tests/features/yt_shorts/test_script_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/features/yt_shorts/test_script_service.py`:

```python
import json
from unittest.mock import MagicMock, patch
from backend.features.yt_shorts.services.script import generate_script

_MOCK_SCRIPT_RESPONSE = {
    "sentences": [
        {
            "text": "Most people think snipers always aim for the chest.",
            "pexels_query": "sniper rifle scope",
            "pixabay_query": "military sniper",
            "ai_needed": False,
            "ai_prompt": None,
            "keyword_overlay": "SNIPERS",
        },
        {
            "text": "It makes sense — Hollywood reinforces this every time.",
            "pexels_query": "movie action scene",
            "pixabay_query": "action film",
            "ai_needed": False,
            "ai_prompt": None,
            "keyword_overlay": "HOLLYWOOD",
        },
        {
            "text": "But real military snipers are trained to target the medulla oblongata.",
            "pexels_query": "military sniper training",
            "pixabay_query": "sniper training",
            "ai_needed": False,
            "ai_prompt": None,
            "keyword_overlay": "MEDULLA",
        },
        {
            "text": "Because it causes instant neurological shutdown — no muscle spasm, no trigger pull.",
            "pexels_query": "brain anatomy diagram",
            "pixabay_query": "neurology diagram",
            "ai_needed": True,
            "ai_prompt": "Close-up animation of brain stem being targeted",
            "keyword_overlay": "INSTANT STOP",
        },
    ],
    "originality_score": 8,
    "advertiser_friendliness_score": 9,
    "us_resonance_score": 8,
    "music_mood": "tense, suspenseful",
    "compliance": {
        "sensitive_content": "CLEAR",
        "sensitive_content_details": None,
        "ai_disclosure_required": True,
        "revision_notes": None,
    },
}


def _mock_anthropic(mock_class: MagicMock, response_json: dict) -> None:
    mock_client = MagicMock()
    mock_class.return_value = mock_client
    mock_client.messages.create.return_value.content[0].text = json.dumps(response_json)


def test_generate_script_returns_script_and_compliance():
    with patch("backend.features.yt_shorts.services.script.Anthropic") as MockClass:
        _mock_anthropic(MockClass, _MOCK_SCRIPT_RESPONSE)
        script, compliance_dict = generate_script(
            api_key="fake-key",
            topic_title="Why snipers never aim for the chest",
            misconception="Movies show center-mass shots",
        )
    assert len(script.sentences) == 4
    assert script.originality_score == 8
    assert script.status == "draft"
    assert isinstance(compliance_dict, dict)


def test_generate_script_computes_full_text():
    with patch("backend.features.yt_shorts.services.script.Anthropic") as MockClass:
        _mock_anthropic(MockClass, _MOCK_SCRIPT_RESPONSE)
        script, _ = generate_script("fake-key", "Title", "Misconception")
    expected = " ".join(s["text"] for s in _MOCK_SCRIPT_RESPONSE["sentences"])
    assert script.full_text == expected


def test_generate_script_assigns_sentence_ids():
    with patch("backend.features.yt_shorts.services.script.Anthropic") as MockClass:
        _mock_anthropic(MockClass, _MOCK_SCRIPT_RESPONSE)
        script, _ = generate_script("fake-key", "Title", "Misconception")
    ids = [s.id for s in script.sentences]
    assert len(set(ids)) == 4


def test_generate_script_uses_api_key():
    with patch("backend.features.yt_shorts.services.script.Anthropic") as MockClass:
        _mock_anthropic(MockClass, _MOCK_SCRIPT_RESPONSE)
        generate_script("my-real-key", "Title", "Misconception")
    MockClass.assert_called_once_with(api_key="my-real-key")
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_script_service.py -v
```

Expected: `ImportError` — module not found.

- [ ] **Step 3: Create `backend/features/yt_shorts/services/script.py`**

```python
import json
import uuid
from anthropic import Anthropic
from backend.features.yt_shorts.models.script import Script, ScriptSentence

_SYSTEM = (
    "You are a military and historical weapons education script writer "
    "for a YouTube Shorts channel. Target audience: US military enthusiasts aged 18-45. "
    "Tone: conversational, confident, slightly conspiratorial. "
    "Never use filler words. Never add a CTA. Always end on the twist."
)


def _prompt(title: str, misconception: str) -> str:
    return f"""Write a complete production package for this YouTube Shorts video.

TITLE: {title}
MISCONCEPTION TO CORRECT: {misconception}

Respond with valid JSON only — no markdown, no prose outside the JSON:
{{
  "sentences": [
    {{
      "text": "sentence text here",
      "pexels_query": "sniper rifle scope close up",
      "pixabay_query": "military sniper weapon",
      "ai_needed": false,
      "ai_prompt": null,
      "keyword_overlay": "SNIPERS"
    }}
  ],
  "originality_score": 8,
  "advertiser_friendliness_score": 9,
  "us_resonance_score": 8,
  "music_mood": "tense, suspenseful",
  "compliance": {{
    "sensitive_content": "CLEAR",
    "sensitive_content_details": null,
    "ai_disclosure_required": true,
    "revision_notes": null
  }}
}}

Script requirements:
- Structure: Hook (0-3s) → Common belief validation (3-10s) → Historical/technical truth (10-35s) → Final unexpected twist (35-50s)
- 120-160 words total across all sentences
- American English, confident tone, no filler words, no CTA, end on the twist
- Originality score 1-10 (minimum 7 to pass): corrects misconception, references specifics, reveals non-obvious fact, ends on stronger twist
- Advertiser-friendliness score 1-10 (minimum 8 to pass): no graphic violence, no glorification of casualties, no active conflict coverage
- US resonance score 1-10: US military references, American English
- keyword_overlay: 1-3 words ALL CAPS per sentence"""


def generate_script(
    api_key: str,
    topic_title: str,
    misconception: str,
) -> tuple[Script, dict]:
    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=_SYSTEM,
        messages=[{"role": "user", "content": _prompt(topic_title, misconception)}],
    )
    raw = json.loads(message.content[0].text)
    sentences = [
        ScriptSentence(id=str(uuid.uuid4()), **s)
        for s in raw["sentences"]
    ]
    full_text = " ".join(s.text for s in sentences)
    script = Script(
        sentences=sentences,
        full_text=full_text,
        originality_score=raw["originality_score"],
        advertiser_friendliness_score=raw["advertiser_friendliness_score"],
        us_resonance_score=raw["us_resonance_score"],
        music_mood=raw["music_mood"],
    )
    return script, raw.get("compliance", {})
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_script_service.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/features/yt_shorts/services/script.py backend/tests/features/yt_shorts/test_script_service.py
git commit -m "feat: add script generation service (Claude API)"
```

---

## Task 7: Compliance Service

**Files:**
- Create: `backend/features/yt_shorts/services/compliance.py`
- Create: `backend/tests/features/yt_shorts/test_compliance_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/features/yt_shorts/test_compliance_service.py`:

```python
from backend.features.yt_shorts.models.script import Script, ScriptSentence, ComplianceReport
from backend.features.yt_shorts.services.compliance import check_compliance

_SENTENCE = ScriptSentence(
    id="s1",
    text="Test sentence.",
    pexels_query="test",
    pixabay_query="test",
    ai_needed=False,
    keyword_overlay="TEST",
)


def _make_script(originality: int, advertiser: int) -> Script:
    return Script(
        sentences=[_SENTENCE],
        full_text="Test sentence.",
        originality_score=originality,
        advertiser_friendliness_score=advertiser,
        us_resonance_score=8,
        music_mood="tense",
    )


def test_compliance_passes_when_scores_meet_thresholds():
    script = _make_script(originality=7, advertiser=8)
    report = check_compliance(script)
    assert report.passed is True
    assert report.originality_status == "PASS"
    assert report.advertiser_status == "PASS"


def test_compliance_fails_when_originality_below_7():
    script = _make_script(originality=6, advertiser=9)
    report = check_compliance(script)
    assert report.passed is False
    assert report.originality_status == "REVISION_REQUIRED"
    assert report.advertiser_status == "PASS"


def test_compliance_fails_when_advertiser_below_8():
    script = _make_script(originality=8, advertiser=7)
    report = check_compliance(script)
    assert report.passed is False
    assert report.advertiser_status == "REVISION_REQUIRED"
    assert report.originality_status == "PASS"


def test_compliance_fails_when_both_below_threshold():
    script = _make_script(originality=5, advertiser=6)
    report = check_compliance(script)
    assert report.passed is False
    assert report.originality_status == "REVISION_REQUIRED"
    assert report.advertiser_status == "REVISION_REQUIRED"


def test_compliance_carries_scores():
    script = _make_script(originality=9, advertiser=9)
    report = check_compliance(script)
    assert report.originality_score == 9
    assert report.advertiser_friendliness_score == 9


def test_compliance_accepts_sensitive_content_from_claude():
    script = _make_script(originality=8, advertiser=8)
    report = check_compliance(
        script,
        sensitive_content="FLAG",
        sensitive_content_details="Mentions active conflict",
        revision_notes="Remove active conflict reference",
    )
    assert report.sensitive_content == "FLAG"
    assert report.sensitive_content_details == "Mentions active conflict"
    assert report.revision_notes == "Remove active conflict reference"


def test_compliance_ai_disclosure_always_true():
    script = _make_script(originality=8, advertiser=8)
    report = check_compliance(script)
    assert report.ai_disclosure_required is True
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_compliance_service.py -v
```

Expected: `ImportError` — module not found.

- [ ] **Step 3: Create `backend/features/yt_shorts/services/compliance.py`**

```python
from typing import Literal, Optional
from backend.features.yt_shorts.models.script import Script, ComplianceReport

_ORIGINALITY_MIN = 7
_ADVERTISER_MIN = 8


def check_compliance(
    script: Script,
    sensitive_content: Literal["CLEAR", "FLAG"] = "CLEAR",
    sensitive_content_details: Optional[str] = None,
    revision_notes: Optional[str] = None,
) -> ComplianceReport:
    originality_ok = script.originality_score >= _ORIGINALITY_MIN
    advertiser_ok = script.advertiser_friendliness_score >= _ADVERTISER_MIN
    return ComplianceReport(
        originality_score=script.originality_score,
        advertiser_friendliness_score=script.advertiser_friendliness_score,
        originality_status="PASS" if originality_ok else "REVISION_REQUIRED",
        advertiser_status="PASS" if advertiser_ok else "REVISION_REQUIRED",
        sensitive_content=sensitive_content,
        sensitive_content_details=sensitive_content_details,
        ai_disclosure_required=True,
        passed=originality_ok and advertiser_ok,
        revision_notes=revision_notes,
    )
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_compliance_service.py -v
```

Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/features/yt_shorts/services/compliance.py backend/tests/features/yt_shorts/test_compliance_service.py
git commit -m "feat: add compliance check service (score thresholds)"
```

---

## Task 8: Script Router

**Files:**
- Create: `backend/features/yt_shorts/routers/script.py`
- Create: `backend/tests/features/yt_shorts/test_script_router.py`
- Modify: `backend/features/yt_shorts/router.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/features/yt_shorts/test_script_router.py`:

```python
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch
from backend.core.store import ProjectStore, get_store
from backend.config import get_settings, Settings
from backend.features.yt_shorts.routers.script import router
from backend.features.yt_shorts.models.script import Script, ScriptSentence, ComplianceReport

_SENTENCE = ScriptSentence(
    id="s1",
    text="Test sentence.",
    pexels_query="test",
    pixabay_query="test",
    ai_needed=False,
    keyword_overlay="TEST",
)
_SCRIPT = Script(
    sentences=[_SENTENCE],
    full_text="Test sentence.",
    originality_score=8,
    advertiser_friendliness_score=9,
    us_resonance_score=8,
    music_mood="tense",
)
_COMPLIANCE_DICT = {
    "sensitive_content": "CLEAR",
    "sensitive_content_details": None,
    "ai_disclosure_required": True,
    "revision_notes": None,
}


@pytest.fixture
def setup(tmp_path):
    store = ProjectStore(base_dir=str(tmp_path))
    project = store.create({
        "title": "Test Video",
        "current_step": "script",
        "topics": [],
        "approved_topic": {
            "id": "t1",
            "title": "Why snipers never aim for center mass",
            "misconception": "Movies show chest shots",
            "real_answer": "CNS targeting",
            "us_curiosity_score": 9,
            "status": "approved",
        },
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
    })
    project_id = project["id"]

    app = FastAPI()
    app.include_router(router, prefix="/projects/{project_id}/script")
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: Settings(anthropic_api_key="test-key")

    return TestClient(app), project_id, store


def test_generate_script_returns_script_response(setup):
    client, project_id, _ = setup

    with patch("backend.features.yt_shorts.routers.script.generate_script") as mock_gen:
        mock_gen.return_value = (_SCRIPT, _COMPLIANCE_DICT)
        response = client.post(f"/projects/{project_id}/script/generate")

    assert response.status_code == 200
    data = response.json()
    assert "script" in data
    assert "compliance" in data
    assert data["script"]["originality_score"] == 8


def test_generate_script_no_approved_topic(setup):
    client, project_id, store = setup
    store.update(project_id, {"approved_topic": None})

    with patch("backend.features.yt_shorts.routers.script.generate_script"):
        response = client.post(f"/projects/{project_id}/script/generate")

    assert response.status_code == 400


def test_get_script_returns_none_when_no_draft(setup):
    client, project_id, _ = setup
    response = client.get(f"/projects/{project_id}/script")
    assert response.status_code == 200
    data = response.json()
    assert data["script"] is None


def test_get_script_after_generate(setup):
    client, project_id, _ = setup

    with patch("backend.features.yt_shorts.routers.script.generate_script") as mock_gen:
        mock_gen.return_value = (_SCRIPT, _COMPLIANCE_DICT)
        client.post(f"/projects/{project_id}/script/generate")

    response = client.get(f"/projects/{project_id}/script")
    assert response.status_code == 200
    assert response.json()["script"]["full_text"] == "Test sentence."


def test_compliance_check_returns_report(setup):
    client, project_id, store = setup
    store.update(project_id, {"script_draft": _SCRIPT.model_dump()})

    response = client.post(f"/projects/{project_id}/script/compliance")

    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is True
    assert data["originality_status"] == "PASS"


def test_compliance_check_no_script_returns_400(setup):
    client, project_id, _ = setup
    response = client.post(f"/projects/{project_id}/script/compliance")
    assert response.status_code == 400


def test_approve_script_advances_to_voiceover(setup):
    client, project_id, store = setup
    store.update(project_id, {"script_draft": _SCRIPT.model_dump()})

    response = client.post(f"/projects/{project_id}/script/approve")

    assert response.status_code == 200
    project = store.get(project_id)
    assert project["current_step"] == "voiceover"
    assert project["script_draft"]["status"] == "approved"


def test_approve_script_no_draft_returns_400(setup):
    client, project_id, _ = setup
    response = client.post(f"/projects/{project_id}/script/approve")
    assert response.status_code == 400
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_script_router.py -v
```

Expected: `ImportError` — router not found.

- [ ] **Step 3: Create `backend/features/yt_shorts/routers/script.py`**

```python
from fastapi import APIRouter, HTTPException, Depends
from backend.core.store import ProjectStore, get_store
from backend.config import get_settings, Settings
from backend.features.yt_shorts.models.script import Script, ComplianceReport, ScriptResponse
from backend.features.yt_shorts.services.script import generate_script
from backend.features.yt_shorts.services.compliance import check_compliance

router = APIRouter(tags=["yt-shorts-script"])


@router.post("/generate", response_model=ScriptResponse)
def generate_script_endpoint(
    project_id: str,
    store: ProjectStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    approved_topic = project.get("approved_topic")
    if not approved_topic:
        raise HTTPException(status_code=400, detail="No approved topic. Approve a topic first.")

    script, claude_compliance = generate_script(
        api_key=settings.anthropic_api_key,
        topic_title=approved_topic["title"],
        misconception=approved_topic["misconception"],
    )
    compliance = check_compliance(
        script,
        sensitive_content=claude_compliance.get("sensitive_content", "CLEAR"),
        sensitive_content_details=claude_compliance.get("sensitive_content_details"),
        revision_notes=claude_compliance.get("revision_notes"),
    )
    store.update(project_id, {
        "script_draft": script.model_dump(),
        "compliance_report": compliance.model_dump(),
    })
    return ScriptResponse(script=script, compliance=compliance)


@router.get("", response_model=ScriptResponse)
def get_script(
    project_id: str,
    store: ProjectStore = Depends(get_store),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    script_dict = project.get("script_draft")
    compliance_dict = project.get("compliance_report")
    script = Script(**script_dict) if script_dict else None
    compliance = ComplianceReport(**compliance_dict) if compliance_dict else None
    return ScriptResponse(script=script, compliance=compliance)


@router.post("/compliance", response_model=ComplianceReport)
def run_compliance(
    project_id: str,
    store: ProjectStore = Depends(get_store),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    script_dict = project.get("script_draft")
    if not script_dict:
        raise HTTPException(status_code=400, detail="No script draft. Generate script first.")

    script = Script(**script_dict)
    compliance = check_compliance(script)
    store.update(project_id, {"compliance_report": compliance.model_dump()})
    return compliance


@router.post("/approve", response_model=Script)
def approve_script(
    project_id: str,
    store: ProjectStore = Depends(get_store),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    script_dict = project.get("script_draft")
    if not script_dict:
        raise HTTPException(status_code=400, detail="No script draft. Generate script first.")

    script_dict["status"] = "approved"
    store.update(project_id, {
        "script_draft": script_dict,
        "current_step": "voiceover",
    })
    return Script(**script_dict)
```

- [ ] **Step 4: Update `backend/features/yt_shorts/router.py`**

```python
from fastapi import APIRouter
from backend.features.yt_shorts.routers import projects, topics, script

router = APIRouter(prefix="/yt-shorts")
router.include_router(projects.router, prefix="/projects")
router.include_router(topics.router, prefix="/projects/{project_id}/topics")
router.include_router(script.router, prefix="/projects/{project_id}/script")
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_script_router.py -v
```

Expected: `8 passed`

- [ ] **Step 6: Run full suite**

```bash
.venv/Scripts/python -m pytest backend/tests/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/features/yt_shorts/routers/script.py backend/tests/features/yt_shorts/test_script_router.py backend/features/yt_shorts/router.py
git commit -m "feat: add script router (generate, get, compliance, approve)"
```

---

## Task 9: Voiceover Pydantic Models + Config + Requirements

**Files:**
- Create: `backend/features/yt_shorts/models/voiceover.py`
- Create: `backend/tests/features/yt_shorts/test_voiceover_models.py`
- Modify: `backend/config.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add `elevenlabs` to requirements.txt and install it**

Update `backend/requirements.txt`:

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
pydantic==2.10.3
pydantic-settings==2.6.1
python-dotenv==1.0.1
httpx==0.27.2
pytest==9.0.3
pytest-asyncio==0.25.2
anthropic>=0.40.0
elevenlabs>=1.0.0
```

Install:

```bash
cd E:/digital-sorcery/master-planner/yt-shorts
.venv/Scripts/pip install "elevenlabs>=1.0.0"
```

- [ ] **Step 2: Add `elevenlabs_voice_id` to `backend/config.py`**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    pexels_api_key: str = ""
    pixabay_api_key: str = ""
    tmp_dir: str = ".tmp"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 3: Write the failing voiceover model tests**

Create `backend/tests/features/yt_shorts/test_voiceover_models.py`:

```python
from backend.features.yt_shorts.models.voiceover import Voiceover


def test_voiceover_defaults_to_generated():
    v = Voiceover(audio_path="/tmp/projects/abc/voiceover.mp3")
    assert v.status == "generated"
    assert v.duration_seconds is None


def test_voiceover_serializes():
    v = Voiceover(
        audio_path="/tmp/projects/abc/voiceover.mp3",
        duration_seconds=47.3,
    )
    data = v.model_dump()
    assert data["status"] == "generated"
    assert data["duration_seconds"] == 47.3


def test_voiceover_approved_status():
    v = Voiceover(audio_path="/tmp/test.mp3", status="approved")
    assert v.status == "approved"
```

- [ ] **Step 4: Run test — expect FAIL**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_voiceover_models.py -v
```

Expected: `ImportError` — module not found.

- [ ] **Step 5: Create `backend/features/yt_shorts/models/voiceover.py`**

```python
from pydantic import BaseModel, ConfigDict
from typing import Literal, Optional


class Voiceover(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audio_path: str
    duration_seconds: Optional[float] = None
    status: Literal["generated", "approved"] = "generated"
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_voiceover_models.py -v
```

Expected: `3 passed`

- [ ] **Step 7: Commit**

```bash
git add backend/features/yt_shorts/models/voiceover.py backend/tests/features/yt_shorts/test_voiceover_models.py backend/config.py backend/requirements.txt
git commit -m "feat: add Voiceover model, elevenlabs_voice_id config, elevenlabs dep"
```

---

## Task 10: Voiceover Generation Service

**Files:**
- Create: `backend/features/yt_shorts/services/voiceover.py`
- Create: `backend/tests/features/yt_shorts/test_voiceover_service.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/features/yt_shorts/test_voiceover_service.py`:

```python
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from backend.features.yt_shorts.services.voiceover import generate_voiceover


def test_generate_voiceover_creates_audio_file(tmp_path):
    audio_path = str(tmp_path / "voiceover.mp3")
    mock_chunks = [b"chunk1", b"chunk2"]

    with patch("backend.features.yt_shorts.services.voiceover.ElevenLabs") as MockClass:
        mock_client = MagicMock()
        MockClass.return_value = mock_client
        mock_client.text_to_speech.convert.return_value = iter(mock_chunks)

        result = generate_voiceover(
            text="This is the script.",
            api_key="fake-key",
            voice_id="fake-voice-id",
            output_path=audio_path,
        )

    assert Path(audio_path).exists()
    assert Path(audio_path).read_bytes() == b"chunk1chunk2"
    assert result.audio_path == audio_path
    assert result.status == "generated"


def test_generate_voiceover_uses_correct_settings(tmp_path):
    audio_path = str(tmp_path / "voiceover.mp3")

    with patch("backend.features.yt_shorts.services.voiceover.ElevenLabs") as MockClass:
        mock_client = MagicMock()
        MockClass.return_value = mock_client
        mock_client.text_to_speech.convert.return_value = iter([b"audio"])

        generate_voiceover(
            text="Script text.",
            api_key="my-key",
            voice_id="voice-abc",
            output_path=audio_path,
        )

    MockClass.assert_called_once_with(api_key="my-key")
    call_kwargs = mock_client.text_to_speech.convert.call_args.kwargs
    assert call_kwargs["voice_id"] == "voice-abc"
    assert call_kwargs["text"] == "Script text."
    assert call_kwargs["output_format"] == "mp3_44100_192"


def test_generate_voiceover_skips_empty_chunks(tmp_path):
    audio_path = str(tmp_path / "voiceover.mp3")
    mock_chunks = [b"real", b"", None, b"data"]

    with patch("backend.features.yt_shorts.services.voiceover.ElevenLabs") as MockClass:
        mock_client = MagicMock()
        MockClass.return_value = mock_client
        mock_client.text_to_speech.convert.return_value = iter(mock_chunks)

        generate_voiceover("Text.", "key", "voice", audio_path)

    assert Path(audio_path).read_bytes() == b"realdata"
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_voiceover_service.py -v
```

Expected: `ImportError` — module not found.

- [ ] **Step 3: Create `backend/features/yt_shorts/services/voiceover.py`**

```python
from pathlib import Path
from elevenlabs import ElevenLabs, VoiceSettings
from backend.features.yt_shorts.models.voiceover import Voiceover


def generate_voiceover(
    text: str,
    api_key: str,
    voice_id: str,
    output_path: str,
) -> Voiceover:
    client = ElevenLabs(api_key=api_key)
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id="eleven_multilingual_v2",
        voice_settings=VoiceSettings(
            stability=0.70,
            similarity_boost=0.82,
            style=0.37,
            use_speaker_boost=True,
        ),
        output_format="mp3_44100_192",
    )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in audio:
            if chunk:
                f.write(chunk)
    return Voiceover(audio_path=output_path)
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_voiceover_service.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/features/yt_shorts/services/voiceover.py backend/tests/features/yt_shorts/test_voiceover_service.py
git commit -m "feat: add voiceover generation service (ElevenLabs)"
```

---

## Task 11: Voiceover Router

**Files:**
- Create: `backend/features/yt_shorts/routers/voiceover.py`
- Create: `backend/tests/features/yt_shorts/test_voiceover_router.py`
- Modify: `backend/features/yt_shorts/router.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/features/yt_shorts/test_voiceover_router.py`:

```python
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch
from backend.core.store import ProjectStore, get_store
from backend.config import get_settings, Settings
from backend.features.yt_shorts.routers.voiceover import router
from backend.features.yt_shorts.models.voiceover import Voiceover
from backend.features.yt_shorts.models.script import Script, ScriptSentence

_SENTENCE = ScriptSentence(
    id="s1", text="Hook sentence.", pexels_query="q", pixabay_query="q",
    ai_needed=False, keyword_overlay="TEST",
)
_SCRIPT_DICT = Script(
    sentences=[_SENTENCE],
    full_text="Hook sentence.",
    originality_score=8,
    advertiser_friendliness_score=9,
    us_resonance_score=8,
    music_mood="tense",
    status="approved",
).model_dump()


@pytest.fixture
def setup(tmp_path):
    store = ProjectStore(base_dir=str(tmp_path))
    project = store.create({
        "title": "Test Video",
        "current_step": "voiceover",
        "topics": [],
        "approved_topic": {"id": "t1", "title": "Why snipers", "misconception": "X", "real_answer": "Y", "us_curiosity_score": 9, "status": "approved"},
        "script_draft": _SCRIPT_DICT,
        "compliance_report": None,
        "voiceover": None,
        "footage_clips": [],
        "ai_clips": [],
        "selected_track": None,
        "assets_path": None,
        "gate_result": None,
        "metadata": None,
        "youtube_video_id": None,
    })
    project_id = project["id"]

    app = FastAPI()
    app.include_router(router, prefix="/projects/{project_id}/voiceover")
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_settings] = lambda: Settings(
        elevenlabs_api_key="test-key",
        elevenlabs_voice_id="test-voice",
        tmp_dir=str(tmp_path),
    )

    return TestClient(app), project_id, store


def test_generate_voiceover_returns_voiceover(setup):
    client, project_id, _ = setup
    mock_vo = Voiceover(audio_path="/tmp/test/voiceover.mp3")

    with patch("backend.features.yt_shorts.routers.voiceover.generate_voiceover") as mock_gen:
        mock_gen.return_value = mock_vo
        response = client.post(f"/projects/{project_id}/voiceover/generate")

    assert response.status_code == 200
    assert response.json()["status"] == "generated"


def test_generate_voiceover_stores_in_project(setup):
    client, project_id, store = setup
    mock_vo = Voiceover(audio_path="/tmp/test/voiceover.mp3")

    with patch("backend.features.yt_shorts.routers.voiceover.generate_voiceover") as mock_gen:
        mock_gen.return_value = mock_vo
        client.post(f"/projects/{project_id}/voiceover/generate")

    project = store.get(project_id)
    assert project["voiceover"] is not None
    assert project["voiceover"]["audio_path"] == "/tmp/test/voiceover.mp3"


def test_generate_voiceover_no_script_returns_400(setup):
    client, project_id, store = setup
    store.update(project_id, {"script_draft": None})

    with patch("backend.features.yt_shorts.routers.voiceover.generate_voiceover"):
        response = client.post(f"/projects/{project_id}/voiceover/generate")

    assert response.status_code == 400


def test_get_voiceover_returns_none_when_not_generated(setup):
    client, project_id, _ = setup
    response = client.get(f"/projects/{project_id}/voiceover")
    assert response.status_code == 200
    assert response.json() is None


def test_get_voiceover_after_generate(setup):
    client, project_id, _ = setup
    mock_vo = Voiceover(audio_path="/tmp/test/voiceover.mp3")

    with patch("backend.features.yt_shorts.routers.voiceover.generate_voiceover") as mock_gen:
        mock_gen.return_value = mock_vo
        client.post(f"/projects/{project_id}/voiceover/generate")

    response = client.get(f"/projects/{project_id}/voiceover")
    assert response.status_code == 200
    assert response.json()["audio_path"] == "/tmp/test/voiceover.mp3"


def test_approve_voiceover_advances_to_footage_search(setup):
    client, project_id, store = setup
    mock_vo = Voiceover(audio_path="/tmp/test/voiceover.mp3")

    with patch("backend.features.yt_shorts.routers.voiceover.generate_voiceover") as mock_gen:
        mock_gen.return_value = mock_vo
        client.post(f"/projects/{project_id}/voiceover/generate")

    response = client.post(f"/projects/{project_id}/voiceover/approve")

    assert response.status_code == 200
    project = store.get(project_id)
    assert project["current_step"] == "footage_search"
    assert project["voiceover"]["status"] == "approved"


def test_approve_voiceover_no_voiceover_returns_400(setup):
    client, project_id, _ = setup
    response = client.post(f"/projects/{project_id}/voiceover/approve")
    assert response.status_code == 400
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_voiceover_router.py -v
```

Expected: `ImportError` — router not found.

- [ ] **Step 3: Create `backend/features/yt_shorts/routers/voiceover.py`**

```python
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from backend.core.store import ProjectStore, get_store
from backend.config import get_settings, Settings
from backend.features.yt_shorts.models.voiceover import Voiceover
from backend.features.yt_shorts.models.script import Script
from backend.features.yt_shorts.services.voiceover import generate_voiceover

router = APIRouter(tags=["yt-shorts-voiceover"])


@router.post("/generate", response_model=Voiceover)
def generate_voiceover_endpoint(
    project_id: str,
    store: ProjectStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    script_dict = project.get("script_draft")
    if not script_dict:
        raise HTTPException(status_code=400, detail="No script draft. Generate and approve script first.")

    script = Script(**script_dict)
    audio_path = str(
        Path(settings.tmp_dir) / "projects" / project_id / "voiceover.mp3"
    )
    voiceover = generate_voiceover(
        text=script.full_text,
        api_key=settings.elevenlabs_api_key,
        voice_id=settings.elevenlabs_voice_id,
        output_path=audio_path,
    )
    store.update(project_id, {"voiceover": voiceover.model_dump()})
    return voiceover


@router.get("", response_model=Voiceover | None)
def get_voiceover(
    project_id: str,
    store: ProjectStore = Depends(get_store),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    vo_dict = project.get("voiceover")
    return Voiceover(**vo_dict) if vo_dict else None


@router.post("/approve", response_model=Voiceover)
def approve_voiceover(
    project_id: str,
    store: ProjectStore = Depends(get_store),
):
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    vo_dict = project.get("voiceover")
    if not vo_dict:
        raise HTTPException(status_code=400, detail="No voiceover. Generate voiceover first.")

    vo_dict["status"] = "approved"
    store.update(project_id, {
        "voiceover": vo_dict,
        "current_step": "footage_search",
    })
    return Voiceover(**vo_dict)
```

- [ ] **Step 4: Update `backend/features/yt_shorts/router.py`**

```python
from fastapi import APIRouter
from backend.features.yt_shorts.routers import projects, topics, script, voiceover

router = APIRouter(prefix="/yt-shorts")
router.include_router(projects.router, prefix="/projects")
router.include_router(topics.router, prefix="/projects/{project_id}/topics")
router.include_router(script.router, prefix="/projects/{project_id}/script")
router.include_router(voiceover.router, prefix="/projects/{project_id}/voiceover")
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
.venv/Scripts/python -m pytest backend/tests/features/yt_shorts/test_voiceover_router.py -v
```

Expected: `7 passed`

- [ ] **Step 6: Run the full test suite**

```bash
.venv/Scripts/python -m pytest backend/tests/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/features/yt_shorts/routers/voiceover.py backend/tests/features/yt_shorts/test_voiceover_router.py backend/features/yt_shorts/router.py
git commit -m "feat: add voiceover router (generate, get, approve)"
```

---

## Final Verification

- [ ] **Run the full backend test suite**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts
.venv/Scripts/python -m pytest backend/tests/ -v --tb=short
```

Expected: all tests pass. Confirm topics, script, compliance, and voiceover tests all present.

- [ ] **Confirm Swagger shows new endpoints**

```bash
.venv/Scripts/python -m uvicorn backend.main:app --port 8000
```

Open `http://localhost:8000/docs`. Confirm these route groups exist:
- `yt-shorts-topics`: generate, list, approve
- `yt-shorts-script`: generate, get, compliance, approve
- `yt-shorts-voiceover`: generate, get, approve

- [ ] **Final commit**

```bash
git add -A
git commit -m "chore: Plan 2 complete — Topics, Script, Compliance, Voiceover endpoints"
```
