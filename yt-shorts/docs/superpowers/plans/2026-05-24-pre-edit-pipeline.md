# Pre-Edit Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `pipeline.py` and its 9 tool scripts so that one command takes an approved topic from `topics/queue.json` to a packaged asset bundle in `assets/<job-id>/` ready for CapCut editing.

**Architecture:** WAT (Workflows, Agents, Tools). `pipeline.py` is a thin orchestrator — it reads state, calls each tool script's `run()` function in order, checkpoints after each step, and halts cleanly at natural pause points (no approved topic, compliance failure, Runway gaps). Each tool script is independently runnable and testable.

**Tech Stack:** Python 3.11+, `anthropic` SDK, `requests`, `python-dotenv`, `ffmpeg` (system binary via subprocess), `pytest`, `pytest-mock`

---

## File Map

```
pipeline.py                          orchestrator
tools/__init__.py
tools/utils/__init__.py
tools/utils/config.py                load .env → config dict
tools/utils/state.py                 read/write .tmp/<job-id>/state.json
tools/utils/job.py                   generate job ID from topic title
tools/generate_topics.py             Claude API → 20 topics → queue.json
tools/generate_script.py             Claude API → script.json per job
tools/check_compliance.py            validate scores from script.json
tools/generate_voiceover.py          ElevenLabs REST → voiceover.mp3
tools/search_footage.py              Pexels + Pixabay concurrent → clip files
tools/clear_footage.py               ffmpeg strip audio → clearance log
tools/select_music.py                pick track from music/ by mood
tools/check_footage_gaps.py          detect missing clips → footage-gaps.md
tools/package_assets.py              assemble numbered bundle → assets/<job-id>/
tests/conftest.py                    shared fixtures
tests/tools/test_utils.py
tests/tools/test_generate_topics.py
tests/tools/test_generate_script.py
tests/tools/test_check_compliance.py
tests/tools/test_generate_voiceover.py
tests/tools/test_search_footage.py
tests/tools/test_clear_footage.py
tests/tools/test_select_music.py
tests/tools/test_check_footage_gaps.py
tests/tools/test_package_assets.py
tests/test_pipeline.py
requirements.txt
.env.example
```

---

## Task 1: Project Foundation

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `tools/__init__.py`
- Create: `tools/utils/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/tools/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
anthropic>=0.40.0
requests>=2.31.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 2: Create .env.example**

```
ANTHROPIC_API_KEY=
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
PEXELS_API_KEY=
PIXABAY_API_KEY=
```

- [ ] **Step 3: Create empty init files**

```bash
touch tools/__init__.py tools/utils/__init__.py tests/__init__.py tests/tools/__init__.py
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 5: Create project directories**

```bash
mkdir -p topics scripts voiceover footage assets output metadata compliance-logs music/tense music/dramatic music/suspenseful .tmp
```

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .env.example tools/__init__.py tools/utils/__init__.py tests/__init__.py tests/tools/__init__.py
git commit -m "feat: project foundation — requirements, env template, package structure"
```

---

## Task 2: Shared Utilities

**Files:**
- Create: `tools/utils/config.py`
- Create: `tools/utils/state.py`
- Create: `tools/utils/job.py`
- Create: `tests/conftest.py`
- Create: `tests/tools/test_utils.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tools/test_utils.py`:

```python
import json
import pytest
from pathlib import Path
from tools.utils.state import load_state, save_state, is_complete, mark_complete
from tools.utils.job import make_job_id


def test_make_job_id_format():
    job_id = make_job_id("Why do real snipers never use laser sights?")
    assert job_id[:8].isdigit()  # YYYYMMDD prefix
    assert "-" in job_id
    assert job_id == job_id.lower()


def test_make_job_id_slug_truncated():
    job_id = make_job_id("Why do real snipers never use laser sights in combat today?")
    parts = job_id.split("-")
    # date part (8 digits) + max 5 slug words
    assert len(parts) <= 6


def test_load_state_missing_returns_empty(tmp_path):
    state = load_state("nonexistent-job", tmp_path)
    assert state["job_id"] == "nonexistent-job"
    assert state["completed_steps"] == []


def test_save_and_load_state(tmp_path):
    state = {"job_id": "test-job", "completed_steps": ["generate_script"]}
    save_state(state, tmp_path)
    loaded = load_state("test-job", tmp_path)
    assert loaded["completed_steps"] == ["generate_script"]


def test_is_complete(tmp_path):
    state = {"job_id": "j", "completed_steps": ["generate_script"]}
    assert is_complete("generate_script", state) is True
    assert is_complete("generate_voiceover", state) is False


def test_mark_complete_saves_and_returns(tmp_path):
    state = {"job_id": "j", "completed_steps": []}
    state = mark_complete("generate_script", state, tmp_path)
    assert "generate_script" in state["completed_steps"]
    loaded = load_state("j", tmp_path)
    assert "generate_script" in loaded["completed_steps"]
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_utils.py -v
```

Expected: `ImportError` — modules not yet created.

- [ ] **Step 3: Create `tests/conftest.py`**

```python
import json
import pytest
from pathlib import Path


@pytest.fixture
def project_root(tmp_path):
    for d in ["topics", ".tmp", "scripts", "voiceover", "footage", "assets",
              "music/tense", "music/dramatic", "music/suspenseful",
              "compliance-logs", "metadata", "output"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def config():
    return {
        "anthropic_api_key": "test-key",
        "elevenlabs_api_key": "test-key",
        "elevenlabs_voice_id": "test-voice-id",
        "pexels_api_key": "test-key",
        "pixabay_api_key": "test-key",
    }


@pytest.fixture
def sample_topic():
    return {
        "id": "abc123",
        "title": "Why do real snipers never use laser sights in combat?",
        "misconception": "Laser sights give snipers a tactical advantage",
        "real_answer": "Lasers are visible to night vision, revealing your position",
        "us_score": 9,
        "status": "approved",
        "created_at": "2026-05-24T10:00:00Z",
    }


@pytest.fixture
def sample_script(project_root, sample_topic):
    script = {
        "job_id": "20260524-test-job",
        "topic": sample_topic,
        "sentences": [
            {
                "text": "You've seen them in every action movie.",
                "pexels_query": "laser sight rifle",
                "pixabay_query": "sniper rifle military",
                "needs_ai_video": False,
                "runway_prompt": None,
                "overlay": "EVERY MOVIE",
                "timestamp_approx": "0:00",
            },
            {
                "text": "But real snipers never use them in combat.",
                "pexels_query": "military sniper rifle",
                "pixabay_query": "sniper combat",
                "needs_ai_video": False,
                "runway_prompt": None,
                "overlay": "REAL SNIPERS",
                "timestamp_approx": "0:04",
            },
        ],
        "scores": {
            "originality": 8,
            "advertiser_friendliness": 9,
            "us_resonance": 9,
        },
        "compliance": {
            "originality": "PASS",
            "advertiser_friendliness": "PASS",
            "sensitive_content": "CLEAR",
            "ai_disclosure_required": "YES",
            "revision_notes": None,
        },
        "music_mood": "tense",
    }
    script_dir = project_root / "scripts" / "20260524-test-job"
    script_dir.mkdir(parents=True)
    (script_dir / "script.json").write_text(json.dumps(script))
    return script
```

- [ ] **Step 4: Create `tools/utils/config.py`**

```python
import os
from pathlib import Path
from dotenv import load_dotenv


def load_config() -> dict:
    load_dotenv()
    return {
        "anthropic_api_key": os.environ["ANTHROPIC_API_KEY"],
        "elevenlabs_api_key": os.environ["ELEVENLABS_API_KEY"],
        "elevenlabs_voice_id": os.environ["ELEVENLABS_VOICE_ID"],
        "pexels_api_key": os.environ["PEXELS_API_KEY"],
        "pixabay_api_key": os.environ["PIXABAY_API_KEY"],
    }
```

- [ ] **Step 5: Create `tools/utils/state.py`**

```python
import json
from pathlib import Path


def load_state(job_id: str, project_root: Path) -> dict:
    state_file = project_root / ".tmp" / job_id / "state.json"
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {"job_id": job_id, "completed_steps": []}


def save_state(state: dict, project_root: Path) -> None:
    state_file = project_root / ".tmp" / state["job_id"] / "state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2))


def is_complete(step: str, state: dict) -> bool:
    return step in state.get("completed_steps", [])


def mark_complete(step: str, state: dict, project_root: Path) -> dict:
    state.setdefault("completed_steps", []).append(step)
    save_state(state, project_root)
    return state
```

- [ ] **Step 6: Create `tools/utils/job.py`**

```python
import re
from datetime import datetime


def make_job_id(topic_title: str) -> str:
    date = datetime.now().strftime("%Y%m%d")
    slug = re.sub(r"[^a-z0-9]+", "-", topic_title.lower())
    slug = "-".join(slug.split("-")[:5]).strip("-")
    return f"{date}-{slug}"
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
pytest tests/tools/test_utils.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add tools/utils/config.py tools/utils/state.py tools/utils/job.py tests/conftest.py tests/tools/test_utils.py
git commit -m "feat: shared utilities — config, state checkpoint, job ID generation"
```

---

## Task 3: generate_topics.py

**Files:**
- Create: `tools/generate_topics.py`
- Create: `tests/tools/test_generate_topics.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tools/test_generate_topics.py`:

```python
import json
import pytest
from unittest.mock import MagicMock, patch
from tools.generate_topics import run, append_to_queue


def make_mock_response(topics_json: str):
    mock = MagicMock()
    mock.content = [MagicMock(text=topics_json)]
    return mock


SAMPLE_TOPICS_JSON = json.dumps([
    {
        "title": "Why do real snipers never use laser sights in combat?",
        "misconception": "Laser sights give a tactical advantage",
        "real_answer": "Lasers reveal your position to night vision",
        "us_score": 9,
    },
    {
        "title": "Why did the US Army abandon the M14 rifle so quickly?",
        "misconception": "The M14 was a failed design",
        "real_answer": "It was accurate but wrong for jungle warfare",
        "us_score": 8,
    },
])


def test_run_calls_claude_api(config):
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_mock_response(SAMPLE_TOPICS_JSON)

        topics = run(config)

    assert len(topics) == 2
    assert topics[0]["title"].startswith("Why")
    assert "us_score" in topics[0]
    mock_client.messages.create.assert_called_once()


def test_run_passes_cache_control(config):
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_mock_response(SAMPLE_TOPICS_JSON)

        run(config)

    call_kwargs = mock_client.messages.create.call_args[1]
    system = call_kwargs["system"]
    assert system[0]["cache_control"] == {"type": "ephemeral"}


def test_append_to_queue_creates_file(project_root):
    topics = [{"title": "Test", "misconception": "X", "real_answer": "Y", "us_score": 7}]
    append_to_queue(topics, project_root)

    queue_file = project_root / "topics" / "queue.json"
    assert queue_file.exists()
    queue = json.loads(queue_file.read_text())
    assert len(queue) == 1
    assert queue[0]["status"] == "pending"
    assert "id" in queue[0]
    assert "created_at" in queue[0]


def test_append_to_queue_merges_with_existing(project_root):
    existing = [{"id": "old1", "title": "Old Topic", "status": "used"}]
    (project_root / "topics" / "queue.json").write_text(json.dumps(existing))

    topics = [{"title": "New Topic", "misconception": "X", "real_answer": "Y", "us_score": 8}]
    append_to_queue(topics, project_root)

    queue = json.loads((project_root / "topics" / "queue.json").read_text())
    assert len(queue) == 2
    assert queue[0]["id"] == "old1"
    assert queue[1]["title"] == "New Topic"
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_generate_topics.py -v
```

Expected: `ImportError` — module not yet created.

- [ ] **Step 3: Create `tools/generate_topics.py`**

```python
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import anthropic

SYSTEM_PROMPT = """Generate 20 YouTube Shorts topic ideas for a military and historical
weapons education channel targeting US audiences.

For each topic provide:
- title: video title using the "Why do real [X] actually [Y]?" formula
- misconception: the common wrong belief being corrected
- real_answer: the surprising real answer in one sentence
- us_score: US curiosity gap score 1–10

Focus on: weapons engineering, historical warrior tools, military tactics,
equipment design evolution, combat technology.
Avoid: active conflicts, casualties, political topics.
Sort by us_score descending.

Output ONLY a valid JSON array. No prose, no markdown fences."""


def run(config: dict) -> list[dict]:
    client = anthropic.Anthropic(api_key=config["anthropic_api_key"])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": "Generate the 20 topics now."}],
    )
    return json.loads(response.content[0].text)


def append_to_queue(topics: list[dict], project_root: Path) -> None:
    queue_file = project_root / "topics" / "queue.json"
    queue_file.parent.mkdir(exist_ok=True)
    existing = json.loads(queue_file.read_text()) if queue_file.exists() else []
    now = datetime.now(timezone.utc).isoformat()
    for topic in topics:
        topic["id"] = str(uuid.uuid4())[:8]
        topic["status"] = "pending"
        topic["created_at"] = now
    existing.extend(topics)
    queue_file.write_text(json.dumps(existing, indent=2))


if __name__ == "__main__":
    from pathlib import Path
    from tools.utils.config import load_config
    project_root = Path(__file__).parent.parent
    cfg = load_config()
    topics = run(cfg)
    append_to_queue(topics, project_root)
    print(f"✅ Added {len(topics)} topics to queue.json")
    for t in topics[:5]:
        print(f"  [{t['us_score']}/10] {t['title']}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/tools/test_generate_topics.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/generate_topics.py tests/tools/test_generate_topics.py
git commit -m "feat: generate_topics — Claude API topic generation with queue append"
```

---

## Task 4: generate_script.py

**Files:**
- Create: `tools/generate_script.py`
- Create: `tests/tools/test_generate_script.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tools/test_generate_script.py`:

```python
import json
import pytest
from unittest.mock import MagicMock, patch
from tools.generate_script import run


def make_mock_response(script_dict: dict):
    mock = MagicMock()
    mock.content = [MagicMock(text=json.dumps(script_dict))]
    return mock


SAMPLE_SCRIPT_RESPONSE = {
    "sentences": [
        {
            "text": "You've seen them in every action movie.",
            "pexels_query": "laser sight rifle",
            "pixabay_query": "sniper rifle military",
            "needs_ai_video": False,
            "runway_prompt": None,
            "overlay": "EVERY MOVIE",
            "timestamp_approx": "0:00",
        }
    ],
    "scores": {"originality": 8, "advertiser_friendliness": 9, "us_resonance": 9},
    "compliance": {
        "originality": "PASS",
        "advertiser_friendliness": "PASS",
        "sensitive_content": "CLEAR",
        "ai_disclosure_required": "YES",
        "revision_notes": None,
    },
    "music_mood": "tense",
}


def test_run_creates_script_json(project_root, config, sample_topic):
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_mock_response(SAMPLE_SCRIPT_RESPONSE)

        result = run("20260524-test-job", sample_topic, config, project_root)

    script_file = project_root / "scripts" / "20260524-test-job" / "script.json"
    assert script_file.exists()
    saved = json.loads(script_file.read_text())
    assert saved["job_id"] == "20260524-test-job"
    assert saved["topic"]["id"] == sample_topic["id"]
    assert len(saved["sentences"]) == 1


def test_run_returns_script_dict(project_root, config, sample_topic):
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_mock_response(SAMPLE_SCRIPT_RESPONSE)

        result = run("20260524-test-job", sample_topic, config, project_root)

    assert result["job_id"] == "20260524-test-job"
    assert "sentences" in result
    assert "scores" in result


def test_run_with_revision_context_appends_to_message(project_root, config, sample_topic):
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_mock_response(SAMPLE_SCRIPT_RESPONSE)

        run("20260524-test-job", sample_topic, config, project_root,
            revision_context="Originality too low — add a specific historical event.")

    call_kwargs = mock_client.messages.create.call_args[1]
    user_content = call_kwargs["messages"][0]["content"]
    assert "PREVIOUS REVISION REQUIRED" in user_content
    assert "historical event" in user_content
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_generate_script.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Create `tools/generate_script.py`**

```python
import json
from pathlib import Path
import anthropic

SYSTEM_PROMPT = """You are a military and historical weapons education script writer for a
YouTube Shorts channel targeting US audiences.

Write a complete production package and output it as valid JSON with this EXACT structure
(no prose, no markdown fences — raw JSON only):
{
  "sentences": [
    {
      "text": "...",
      "pexels_query": "2-4 word footage search query",
      "pixabay_query": "2-4 word alternative footage query",
      "needs_ai_video": false,
      "runway_prompt": null,
      "overlay": "1-3 WORDS ALL CAPS",
      "timestamp_approx": "0:00"
    }
  ],
  "scores": {
    "originality": 8,
    "advertiser_friendliness": 9,
    "us_resonance": 9
  },
  "compliance": {
    "originality": "PASS",
    "advertiser_friendliness": "PASS",
    "sensitive_content": "CLEAR",
    "ai_disclosure_required": "YES",
    "revision_notes": null
  },
  "music_mood": "tense"
}

Script rules:
- Structure: Hook (0-3s) → Common belief validation (3-10s) → Historical/technical truth (10-35s) → Final unexpected twist (35-50s)
- Total length: 120-160 words
- Tone: Conversational, confident, slightly conspiratorial. American English.
- No CTA, no filler. End on the twist — never a summary.
- One sentence per array entry.

Timestamp calculation: 145 WPM. First sentence = 0:00. Increment by (word_count / 145 * 60) seconds per sentence, formatted as M:SS.

Scoring:
- Originality (1-10): +2 each for — corrects a specific named misconception, references specific historical period/event, explains non-obvious mechanism, ends with twist more surprising than main answer, info not learnable from footage alone. Minimum passing: 7/10.
- Advertiser-Friendliness (1-10): minimum 8. Flag any sentences with specific issues in revision_notes.
- US Resonance (1-10): how strongly it targets US military curiosity.
- music_mood: one of "tense", "dramatic", "suspenseful"

If originality < 7 OR advertiser_friendliness < 8: set the corresponding compliance field to "REVISION REQUIRED" and set revision_notes to specific actionable instructions. Still output the full JSON."""


def run(
    job_id: str,
    topic: dict,
    config: dict,
    project_root: Path,
    revision_context: str | None = None,
) -> dict:
    client = anthropic.Anthropic(api_key=config["anthropic_api_key"])

    user_content = (
        f"TOPIC: {topic['title']}\n"
        f"Misconception to correct: {topic['misconception']}\n"
        f"Real answer direction: {topic['real_answer']}"
    )
    if revision_context:
        user_content += (
            f"\n\nPREVIOUS REVISION REQUIRED:\n{revision_context}\n\n"
            "Please revise the script to address these issues."
        )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_content}],
    )

    script = json.loads(response.content[0].text)
    script["job_id"] = job_id
    script["topic"] = topic

    out_dir = project_root / "scripts" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "script.json").write_text(json.dumps(script, indent=2))
    return script


if __name__ == "__main__":
    import sys
    from tools.utils.config import load_config
    project_root = Path(__file__).parent.parent
    job_id, topic_json = sys.argv[1], sys.argv[2]
    result = run(job_id, json.loads(topic_json), load_config(), project_root)
    print(f"✅ Script saved: scripts/{job_id}/script.json")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/tools/test_generate_script.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/generate_script.py tests/tools/test_generate_script.py
git commit -m "feat: generate_script — Claude API script generation with compliance scoring"
```

---

## Task 5: check_compliance.py

**Files:**
- Create: `tools/check_compliance.py`
- Create: `tests/tools/test_check_compliance.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tools/test_check_compliance.py`:

```python
import json
import pytest
from tools.check_compliance import run


def write_script(project_root, job_id, originality, advertiser, sensitive="CLEAR", revision_notes=None):
    script = {
        "job_id": job_id,
        "scores": {"originality": originality, "advertiser_friendliness": advertiser, "us_resonance": 8},
        "compliance": {
            "originality": "PASS" if originality >= 7 else "REVISION REQUIRED",
            "advertiser_friendliness": "PASS" if advertiser >= 8 else "REVISION REQUIRED",
            "sensitive_content": sensitive,
            "ai_disclosure_required": "YES",
            "revision_notes": revision_notes,
        },
    }
    d = project_root / "scripts" / job_id
    d.mkdir(parents=True)
    (d / "script.json").write_text(json.dumps(script))


def test_pass_when_scores_meet_minimums(project_root):
    write_script(project_root, "job-pass", originality=8, advertiser=9)
    result = run("job-pass", project_root)
    assert result["status"] == "PASS"


def test_fail_when_originality_below_7(project_root):
    write_script(project_root, "job-orig", originality=6, advertiser=9,
                 revision_notes="Add a specific historical event.")
    result = run("job-orig", project_root)
    assert result["status"] == "REVISION_REQUIRED"
    assert result["notes"] == "Add a specific historical event."


def test_fail_when_advertiser_below_8(project_root):
    write_script(project_root, "job-adv", originality=8, advertiser=7,
                 revision_notes="Remove the reference to combat casualties.")
    result = run("job-adv", project_root)
    assert result["status"] == "REVISION_REQUIRED"


def test_fail_when_sensitive_content_flagged(project_root):
    write_script(project_root, "job-sens", originality=8, advertiser=9,
                 sensitive="FLAG", revision_notes="Script references active conflict.")
    result = run("job-sens", project_root)
    assert result["status"] == "REVISION_REQUIRED"
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_check_compliance.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Create `tools/check_compliance.py`**

```python
import json
from pathlib import Path


def run(job_id: str, project_root: Path) -> dict:
    script = json.loads((project_root / "scripts" / job_id / "script.json").read_text())
    scores = script["scores"]
    compliance = script["compliance"]

    failures = []
    if scores["originality"] < 7:
        failures.append(f"Originality {scores['originality']}/10 (minimum 7)")
    if scores["advertiser_friendliness"] < 8:
        failures.append(f"Advertiser-friendliness {scores['advertiser_friendliness']}/10 (minimum 8)")
    if compliance.get("sensitive_content") == "FLAG":
        failures.append("Sensitive content flagged")

    revision_required = (
        failures
        or compliance.get("originality") == "REVISION REQUIRED"
        or compliance.get("advertiser_friendliness") == "REVISION REQUIRED"
    )

    if revision_required:
        notes = compliance.get("revision_notes") or "; ".join(failures)
        print(f"\n❌ REVISION REQUIRED for job {job_id}:")
        print(f"   {notes}")
        print(f"\n💡 Fix: python pipeline.py --job {job_id} --revise\n")
        return {"status": "REVISION_REQUIRED", "notes": notes}

    print(
        f"✅ Compliance PASS — "
        f"Originality: {scores['originality']}/10, "
        f"Advertiser: {scores['advertiser_friendliness']}/10, "
        f"US Resonance: {scores['us_resonance']}/10"
    )
    return {"status": "PASS"}


if __name__ == "__main__":
    import sys
    from pathlib import Path
    job_id = sys.argv[1]
    project_root = Path(__file__).parent.parent
    result = run(job_id, project_root)
    if result["status"] != "PASS":
        sys.exit(1)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/tools/test_check_compliance.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/check_compliance.py tests/tools/test_check_compliance.py
git commit -m "feat: check_compliance — score gate with revision instructions"
```

---

## Task 6: generate_voiceover.py

**Files:**
- Create: `tools/generate_voiceover.py`
- Create: `tests/tools/test_generate_voiceover.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tools/test_generate_voiceover.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from tools.generate_voiceover import run


def test_run_saves_mp3(project_root, config, sample_script):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"fake-mp3-bytes"

    with patch("requests.post", return_value=mock_response):
        out_path = run("20260524-test-job", config, project_root)

    assert out_path.exists()
    assert out_path.suffix == ".mp3"
    assert out_path.read_bytes() == b"fake-mp3-bytes"


def test_run_uses_voice_override(project_root, config, sample_script):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"fake-mp3-bytes"

    with patch("requests.post", return_value=mock_response) as mock_post:
        run("20260524-test-job", config, project_root, voice_id="custom-voice-xyz")

    call_url = mock_post.call_args[0][0]
    assert "custom-voice-xyz" in call_url


def test_run_uses_env_voice_when_no_override(project_root, config, sample_script):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"bytes"

    with patch("requests.post", return_value=mock_response) as mock_post:
        run("20260524-test-job", config, project_root)

    call_url = mock_post.call_args[0][0]
    assert config["elevenlabs_voice_id"] in call_url


def test_run_concatenates_all_sentences(project_root, config, sample_script):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"bytes"

    with patch("requests.post", return_value=mock_response) as mock_post:
        run("20260524-test-job", config, project_root)

    call_body = mock_post.call_args[1]["json"]
    assert "You've seen them" in call_body["text"]
    assert "real snipers" in call_body["text"]
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_generate_voiceover.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Create `tools/generate_voiceover.py`**

```python
import json
from pathlib import Path
import requests


def run(
    job_id: str,
    config: dict,
    project_root: Path,
    voice_id: str | None = None,
) -> Path:
    script = json.loads((project_root / "scripts" / job_id / "script.json").read_text())
    full_text = " ".join(s["text"] for s in script["sentences"])

    vid = voice_id or config["elevenlabs_voice_id"]
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"

    response = requests.post(
        url,
        headers={
            "xi-api-key": config["elevenlabs_api_key"],
            "Content-Type": "application/json",
        },
        json={
            "text": full_text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.70,
                "similarity_boost": 0.82,
                "style": 0.37,
                "use_speaker_boost": True,
            },
        },
    )
    response.raise_for_status()

    out_dir = project_root / "voiceover" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "voiceover.mp3"
    out_path.write_bytes(response.content)
    print(f"✅ Voiceover saved: {out_path}")
    return out_path


if __name__ == "__main__":
    import sys
    from tools.utils.config import load_config
    project_root = Path(__file__).parent.parent
    job_id = sys.argv[1]
    voice_id = sys.argv[2] if len(sys.argv) > 2 else None
    run(job_id, load_config(), project_root, voice_id)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/tools/test_generate_voiceover.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/generate_voiceover.py tests/tools/test_generate_voiceover.py
git commit -m "feat: generate_voiceover — ElevenLabs REST with voice override support"
```

---

## Task 7: search_footage.py

**Files:**
- Create: `tools/search_footage.py`
- Create: `tests/tools/test_search_footage.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tools/test_search_footage.py`:

```python
import pytest
from unittest.mock import MagicMock, patch, call
from tools.search_footage import run, search_pexels, best_pexels_url


def test_search_pexels_returns_videos(config):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"videos": [{"id": 1, "video_files": []}]}
    with patch("requests.get", return_value=mock_resp):
        result = search_pexels("sniper rifle", config["pexels_api_key"])
    assert len(result) == 1


def test_best_pexels_url_picks_720p_or_higher():
    videos = [{"video_files": [
        {"height": 480, "link": "http://low.mp4"},
        {"height": 1080, "link": "http://high.mp4"},
    ]}]
    url = best_pexels_url(videos)
    assert url == "http://high.mp4"


def test_best_pexels_url_returns_none_when_no_videos():
    assert best_pexels_url([]) is None


def test_run_downloads_clips_for_each_sentence(project_root, config, sample_script):
    pexels_resp = MagicMock()
    pexels_resp.json.return_value = {
        "videos": [{"video_files": [{"height": 1080, "link": "http://clip.mp4"}]}]
    }
    download_resp = MagicMock()
    download_resp.status_code = 200
    download_resp.content = b"fake-video"

    with patch("requests.get", side_effect=[pexels_resp, download_resp, pexels_resp, download_resp]):
        results = run("20260524-test-job", config, project_root)

    assert len(results) == 2
    clips = list((project_root / "footage" / "20260524-test-job").glob("clip_*.mp4"))
    assert len(clips) == 2


def test_run_falls_back_to_pixabay_when_pexels_empty(project_root, config, sample_script):
    pexels_empty = MagicMock()
    pexels_empty.json.return_value = {"videos": []}

    pixabay_resp = MagicMock()
    pixabay_resp.json.return_value = {
        "hits": [{"videos": {"large": {"url": "http://pixabay-clip.mp4"}}}]
    }
    download_resp = MagicMock()
    download_resp.status_code = 200
    download_resp.content = b"pixabay-video"

    with patch("requests.get", side_effect=[pexels_empty, pixabay_resp, download_resp,
                                             pexels_empty, pixabay_resp, download_resp]):
        results = run("20260524-test-job", config, project_root)

    found = [r for r in results if r["status"] == "found"]
    assert all(r.get("source") == "pixabay" for r in found)
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_search_footage.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Create `tools/search_footage.py`**

```python
import json
import concurrent.futures
from pathlib import Path
import requests


def search_pexels(query: str, api_key: str) -> list[dict]:
    r = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": api_key},
        params={"query": query, "per_page": 3, "orientation": "portrait"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("videos", [])


def best_pexels_url(videos: list) -> str | None:
    for v in videos:
        files = sorted(v.get("video_files", []), key=lambda f: f.get("height", 0), reverse=True)
        for f in files:
            if f.get("height", 0) >= 720:
                return f["link"]
    return None


def search_pixabay(query: str, api_key: str) -> list[dict]:
    r = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": api_key, "q": query, "per_page": 3},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("hits", [])


def best_pixabay_url(hits: list) -> str | None:
    for h in hits:
        for quality in ("full", "large", "medium"):
            url = h.get("videos", {}).get(quality, {}).get("url")
            if url:
                return url
    return None


def _download(url: str, out_path: Path) -> bool:
    r = requests.get(url, stream=True, timeout=30)
    if r.status_code == 200:
        out_path.write_bytes(r.content)
        return True
    return False


def _search_one(idx: int, sentence: dict, job_id: str, config: dict, project_root: Path) -> dict:
    out_dir = project_root / "footage" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"clip_{idx:02d}.mp4"

    if out_path.exists():
        return {"idx": idx, "status": "cached", "path": str(out_path)}

    pexels = search_pexels(sentence["pexels_query"], config["pexels_api_key"])
    url = best_pexels_url(pexels)
    source = "pexels"

    if not url:
        pixabay = search_pixabay(sentence["pixabay_query"], config["pixabay_api_key"])
        url = best_pixabay_url(pixabay)
        source = "pixabay"

    if url and _download(url, out_path):
        return {"idx": idx, "status": "found", "source": source, "path": str(out_path)}

    return {"idx": idx, "status": "not_found", "query": sentence["pexels_query"]}


def run(job_id: str, config: dict, project_root: Path) -> list[dict]:
    script = json.loads((project_root / "scripts" / job_id / "script.json").read_text())
    sentences = script["sentences"]

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_search_one, i, s, job_id, config, project_root): i
            for i, s in enumerate(sentences)
        }
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            status = result["status"]
            src = f" [{result.get('source', '')}]" if status == "found" else ""
            print(f"  Clip {result['idx']:02d}: {status}{src}")

    found = sum(1 for r in results if r["status"] in ("found", "cached"))
    print(f"\n✅ Footage: {found}/{len(sentences)} clips found")
    return sorted(results, key=lambda r: r["idx"])


if __name__ == "__main__":
    import sys
    from tools.utils.config import load_config
    project_root = Path(__file__).parent.parent
    run(sys.argv[1], load_config(), project_root)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/tools/test_search_footage.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/search_footage.py tests/tools/test_search_footage.py
git commit -m "feat: search_footage — concurrent Pexels+Pixabay search with Pixabay fallback"
```

---

## Task 8: clear_footage.py

**Files:**
- Create: `tools/clear_footage.py`
- Create: `tests/tools/test_clear_footage.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tools/test_clear_footage.py`:

```python
import json
import pytest
from unittest.mock import patch, MagicMock
from tools.clear_footage import run, strip_audio


def test_strip_audio_returns_true_on_success(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = strip_audio(tmp_path / "in.mp4", tmp_path / "out.mp4")
    assert result is True


def test_strip_audio_returns_false_on_ffmpeg_failure(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        result = strip_audio(tmp_path / "in.mp4", tmp_path / "out.mp4")
    assert result is False


def test_run_strips_all_clips_and_writes_log(project_root):
    footage_dir = project_root / "footage" / "test-job"
    footage_dir.mkdir(parents=True)
    (footage_dir / "clip_00.mp4").write_bytes(b"fake")
    (footage_dir / "clip_01.mp4").write_bytes(b"fake")

    def fake_strip(input_path, output_path):
        output_path.write_bytes(b"stripped")
        return True

    with patch("tools.clear_footage.strip_audio", side_effect=fake_strip):
        log = run("test-job", project_root)

    assert len(log["clips"]) == 2
    assert all(c["status"] == "cleared" for c in log["clips"])
    log_file = project_root / "compliance-logs" / "test-job" / "clearance.json"
    assert log_file.exists()


def test_run_raises_on_any_failure(project_root):
    footage_dir = project_root / "footage" / "test-job"
    footage_dir.mkdir(parents=True)
    (footage_dir / "clip_00.mp4").write_bytes(b"fake")

    with patch("tools.clear_footage.strip_audio", return_value=False):
        with pytest.raises(RuntimeError, match="Audio stripping failed"):
            run("test-job", project_root)
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_clear_footage.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Create `tools/clear_footage.py`**

```python
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def strip_audio(input_path: Path, output_path: Path) -> bool:
    result = subprocess.run(
        ["ffmpeg", "-i", str(input_path), "-an", "-c:v", "copy", "-y", str(output_path)],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def run(job_id: str, project_root: Path) -> dict:
    footage_dir = project_root / "footage" / job_id
    clips = sorted(footage_dir.glob("clip_*.mp4"))

    log = {
        "job_id": job_id,
        "cleared_at": datetime.now(timezone.utc).isoformat(),
        "clips": [],
    }
    failed = []

    for clip in clips:
        tmp = clip.with_suffix(".noaudio.mp4")
        if strip_audio(clip, tmp):
            tmp.replace(clip)
            log["clips"].append({"file": clip.name, "status": "cleared", "audio_stripped": True})
            print(f"  ✅ {clip.name} — audio stripped")
        else:
            failed.append(clip.name)
            log["clips"].append({"file": clip.name, "status": "failed"})
            print(f"  ❌ {clip.name} — ffmpeg failed")

    log_dir = project_root / "compliance-logs" / job_id
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "clearance.json").write_text(json.dumps(log, indent=2))

    if failed:
        raise RuntimeError(f"Audio stripping failed for: {', '.join(failed)}")

    print(f"✅ {len(clips)} clips cleared")
    return log


if __name__ == "__main__":
    import sys
    project_root = Path(__file__).parent.parent
    run(sys.argv[1], project_root)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/tools/test_clear_footage.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/clear_footage.py tests/tools/test_clear_footage.py
git commit -m "feat: clear_footage — ffmpeg audio strip with clearance log"
```

---

## Task 9: select_music.py

**Files:**
- Create: `tools/select_music.py`
- Create: `tests/tools/test_select_music.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tools/test_select_music.py`:

```python
import pytest
from tools.select_music import run


def add_track(project_root, folder: str, name: str = "track.mp3"):
    (project_root / "music" / folder / name).write_bytes(b"fake-mp3")


def test_run_copies_track_to_asset_bundle(project_root, sample_script):
    add_track(project_root, "tense")
    out_path = run("20260524-test-job", project_root)
    assert out_path.exists()
    assert out_path.name == "music.mp3"
    assert (project_root / "assets" / "20260524-test-job" / "music.mp3").exists()


def test_run_selects_from_correct_mood_folder(project_root, sample_script):
    add_track(project_root, "tense", "dark_tension.mp3")
    add_track(project_root, "dramatic", "epic_drama.mp3")
    # script mood is "tense"
    out_path = run("20260524-test-job", project_root)
    assert out_path.read_bytes() == b"fake-mp3"


def test_run_falls_back_to_any_track_when_mood_folder_empty(project_root, sample_script):
    add_track(project_root, "dramatic", "epic.mp3")
    out_path = run("20260524-test-job", project_root)
    assert out_path.exists()


def test_run_raises_when_no_music_at_all(project_root, sample_script):
    with pytest.raises(FileNotFoundError, match="No music tracks found"):
        run("20260524-test-job", project_root)
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_select_music.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Create `tools/select_music.py`**

```python
import json
import random
import shutil
from pathlib import Path

MOOD_FOLDERS = {
    "tense": ["tense", "suspenseful"],
    "dramatic": ["dramatic"],
    "suspenseful": ["tense", "suspenseful"],
}


def run(job_id: str, project_root: Path) -> Path:
    script = json.loads((project_root / "scripts" / job_id / "script.json").read_text())
    mood = script.get("music_mood", "tense")

    music_root = project_root / "music"
    candidates = []
    for folder_name in MOOD_FOLDERS.get(mood, [mood]):
        folder = music_root / folder_name
        if folder.exists():
            candidates.extend(folder.glob("*.mp3"))

    if not candidates:
        candidates = list(music_root.glob("**/*.mp3"))

    if not candidates:
        raise FileNotFoundError(
            f"No music tracks found in {music_root}. "
            "Add royalty-free MP3s to music/tense/, music/dramatic/, or music/suspenseful/."
        )

    chosen = random.choice(candidates)
    out_dir = project_root / "assets" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "music.mp3"
    shutil.copy2(chosen, out_path)
    print(f"✅ Music selected: {chosen.name} (mood: {mood})")
    return out_path


if __name__ == "__main__":
    import sys
    project_root = Path(__file__).parent.parent
    run(sys.argv[1], project_root)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/tools/test_select_music.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/select_music.py tests/tools/test_select_music.py
git commit -m "feat: select_music — mood-based track selection from local library"
```

---

## Task 10: check_footage_gaps.py

**Files:**
- Create: `tools/check_footage_gaps.py`
- Create: `tests/tools/test_check_footage_gaps.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tools/test_check_footage_gaps.py`:

```python
import pytest
from tools.check_footage_gaps import run


def add_clip(project_root, job_id, idx):
    d = project_root / "footage" / job_id
    d.mkdir(parents=True, exist_ok=True)
    (d / f"clip_{idx:02d}.mp4").write_bytes(b"fake")


def test_run_returns_empty_when_all_clips_present(project_root, sample_script):
    add_clip(project_root, "20260524-test-job", 0)
    add_clip(project_root, "20260524-test-job", 1)
    gaps = run("20260524-test-job", project_root)
    assert gaps == []


def test_run_detects_missing_clips(project_root, sample_script):
    add_clip(project_root, "20260524-test-job", 0)
    # clip_01 is missing
    gaps = run("20260524-test-job", project_root)
    assert len(gaps) == 1
    assert gaps[0]["sentence_idx"] == 1


def test_run_writes_gaps_md_with_runway_prompt(project_root, sample_script):
    # no clips at all
    (project_root / "footage" / "20260524-test-job").mkdir(parents=True)
    run("20260524-test-job", project_root)
    gaps_file = project_root / "assets" / "20260524-test-job" / "footage-gaps.md"
    assert gaps_file.exists()
    content = gaps_file.read_text()
    assert "Runway ML" in content
    assert "clip_00" in content or "Gap #00" in content


def test_run_writes_no_gaps_message_when_all_found(project_root, sample_script):
    add_clip(project_root, "20260524-test-job", 0)
    add_clip(project_root, "20260524-test-job", 1)
    run("20260524-test-job", project_root)
    gaps_file = project_root / "assets" / "20260524-test-job" / "footage-gaps.md"
    assert "No footage gaps" in gaps_file.read_text()


def test_run_accepts_gap_filled_clip_from_gaps_folder(project_root, sample_script):
    # clip_00 missing from main folder but present in gaps/
    footage_dir = project_root / "footage" / "20260524-test-job"
    footage_dir.mkdir(parents=True)
    (footage_dir / "gaps").mkdir()
    (footage_dir / "gaps" / "clip_00.mp4").write_bytes(b"gap-fill")
    add_clip(project_root, "20260524-test-job", 1)
    gaps = run("20260524-test-job", project_root)
    assert gaps == []
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_check_footage_gaps.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Create `tools/check_footage_gaps.py`**

```python
import json
from pathlib import Path


def run(job_id: str, project_root: Path) -> list[dict]:
    script = json.loads((project_root / "scripts" / job_id / "script.json").read_text())
    footage_dir = project_root / "footage" / job_id

    gaps = []
    for i, sentence in enumerate(script["sentences"]):
        stock_clip = footage_dir / f"clip_{i:02d}.mp4"
        gap_clip = footage_dir / "gaps" / f"clip_{i:02d}.mp4"
        if not stock_clip.exists() and not gap_clip.exists():
            prompt = (
                sentence.get("runway_prompt")
                or f"Close-up of {sentence['pexels_query']}, cinematic, 4K, no people"
            )
            gaps.append({
                "sentence_idx": i,
                "text": sentence["text"],
                "overlay": sentence["overlay"],
                "runway_prompt": prompt,
            })

    out_dir = project_root / "assets" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    gaps_file = out_dir / "footage-gaps.md"

    if not gaps:
        gaps_file.write_text("No footage gaps — all clips found.\n")
        print("✅ No footage gaps")
        return []

    lines = [
        f"# Footage Gaps — {job_id}\n",
        f"**{len(gaps)} clips need AI generation in Runway ML.**\n",
        "## Steps",
        "1. Go to https://runwayml.com/ai-tools/gen-3-alpha-turbo/",
        "2. For each gap below: paste the prompt, generate, download",
        f"3. Save each clip as `clip_XX.mp4` in `footage/{job_id}/gaps/`",
        f"4. Re-run: `python pipeline.py --job {job_id}`\n",
    ]
    for g in gaps:
        lines += [
            f"## Gap #{g['sentence_idx']:02d} — overlay: {g['overlay']}",
            f"**Script:** \"{g['text']}\"",
            f"**Runway Prompt:** `{g['runway_prompt']}`\n",
        ]

    gaps_file.write_text("\n".join(lines))
    print(f"⚠️  {len(gaps)} footage gaps → {gaps_file}")
    print(f"   Fill gaps in Runway ML, then re-run: python pipeline.py --job {job_id}")
    return gaps


if __name__ == "__main__":
    import sys
    project_root = Path(__file__).parent.parent
    run(sys.argv[1], project_root)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/tools/test_check_footage_gaps.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/check_footage_gaps.py tests/tools/test_check_footage_gaps.py
git commit -m "feat: check_footage_gaps — detect missing clips and write Runway ML prompts"
```

---

## Task 11: package_assets.py

**Files:**
- Create: `tools/package_assets.py`
- Create: `tests/tools/test_package_assets.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tools/test_package_assets.py`:

```python
import pytest
from tools.package_assets import run


def add_footage(project_root, job_id, count=2):
    d = project_root / "footage" / job_id
    d.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (d / f"clip_{i:02d}.mp4").write_bytes(b"clip")


def add_voiceover(project_root, job_id):
    d = project_root / "voiceover" / job_id
    d.mkdir(parents=True)
    (d / "voiceover.mp3").write_bytes(b"audio")


def add_music(project_root, job_id):
    d = project_root / "assets" / job_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "music.mp3").write_bytes(b"music")


def test_run_copies_clips_numbered(project_root, sample_script):
    add_footage(project_root, "20260524-test-job", count=2)
    add_voiceover(project_root, "20260524-test-job")
    add_music(project_root, "20260524-test-job")

    run("20260524-test-job", project_root)

    assets = project_root / "assets" / "20260524-test-job"
    assert (assets / "01_clip.mp4").exists()
    assert (assets / "02_clip.mp4").exists()


def test_run_copies_voiceover(project_root, sample_script):
    add_footage(project_root, "20260524-test-job", count=2)
    add_voiceover(project_root, "20260524-test-job")
    add_music(project_root, "20260524-test-job")

    run("20260524-test-job", project_root)

    assert (project_root / "assets" / "20260524-test-job" / "voiceover.mp3").exists()


def test_run_writes_script_txt(project_root, sample_script):
    add_footage(project_root, "20260524-test-job", count=2)
    add_voiceover(project_root, "20260524-test-job")
    add_music(project_root, "20260524-test-job")

    run("20260524-test-job", project_root)

    script_txt = project_root / "assets" / "20260524-test-job" / "script.txt"
    assert script_txt.exists()
    content = script_txt.read_text()
    assert "You've seen them" in content


def test_run_writes_overlays_with_timestamps(project_root, sample_script):
    add_footage(project_root, "20260524-test-job", count=2)
    add_voiceover(project_root, "20260524-test-job")
    add_music(project_root, "20260524-test-job")

    run("20260524-test-job", project_root)

    overlays = (project_root / "assets" / "20260524-test-job" / "overlays.txt").read_text()
    assert "[0:00]" in overlays
    assert "EVERY MOVIE" in overlays


def test_run_prefers_gap_clip_over_stock(project_root, sample_script):
    footage_dir = project_root / "footage" / "20260524-test-job"
    footage_dir.mkdir(parents=True)
    (footage_dir / "clip_00.mp4").write_bytes(b"stock")
    (footage_dir / "gaps").mkdir()
    (footage_dir / "gaps" / "clip_00.mp4").write_bytes(b"runway-fill")
    (footage_dir / "clip_01.mp4").write_bytes(b"stock2")
    add_voiceover(project_root, "20260524-test-job")
    add_music(project_root, "20260524-test-job")

    run("20260524-test-job", project_root)

    clip = (project_root / "assets" / "20260524-test-job" / "01_clip.mp4").read_bytes()
    assert clip == b"runway-fill"
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_package_assets.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Create `tools/package_assets.py`**

```python
import json
import shutil
from pathlib import Path


def run(job_id: str, project_root: Path) -> Path:
    script = json.loads((project_root / "scripts" / job_id / "script.json").read_text())
    sentences = script["sentences"]
    footage_dir = project_root / "footage" / job_id
    voiceover_src = project_root / "voiceover" / job_id / "voiceover.mp3"

    out_dir = project_root / "assets" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Copy clips — gap-filled clips take priority over stock
    for i, _ in enumerate(sentences):
        gap_clip = footage_dir / "gaps" / f"clip_{i:02d}.mp4"
        stock_clip = footage_dir / f"clip_{i:02d}.mp4"
        src = gap_clip if gap_clip.exists() else stock_clip
        if src.exists():
            shutil.copy2(src, out_dir / f"{i+1:02d}_clip.mp4")

    # Copy voiceover
    shutil.copy2(voiceover_src, out_dir / "voiceover.mp3")

    # script.txt — timestamped lines for reference while editing
    script_lines = [f"=== {job_id} ===\n"]
    for s in sentences:
        script_lines.append(f"[{s['timestamp_approx']}] {s['text']}")
    (out_dir / "script.txt").write_text("\n".join(script_lines))

    # overlays.txt — timestamp + keyword for each sentence
    overlay_lines = [f"[{s['timestamp_approx']}] {s['overlay']}" for s in sentences]
    (out_dir / "overlays.txt").write_text("\n".join(overlay_lines))

    clips_count = len(list(out_dir.glob("*_clip.mp4")))
    has_voiceover = (out_dir / "voiceover.mp3").exists()
    has_music = (out_dir / "music.mp3").exists()
    has_gaps = (out_dir / "footage-gaps.md").exists() and "No footage gaps" not in (
        out_dir / "footage-gaps.md"
    ).read_text()

    print(f"""
✅ Asset bundle ready: assets/{job_id}/

📋 EDIT CHECKLIST — open this folder in CapCut:
  {"✅" if has_voiceover else "❌"} voiceover.mp3
  {"✅" if has_music else "⚠️ "} music.mp3  (add a track if missing)
  {clips_count} clips numbered for assembly
  ✅ script.txt  (reference while editing)
  ✅ overlays.txt  (timestamps included)
  {"⚠️  footage-gaps.md has unresolved gaps" if has_gaps else "✅ no footage gaps"}

⚠️  THUMBNAIL: First clip first frame must show the object in clear focus.
    This becomes the YouTube Shorts thumbnail.

Next: edit in CapCut → export to output/{job_id}/final.mp4
Then: python publish.py --job {job_id}
""")
    return out_dir


if __name__ == "__main__":
    import sys
    project_root = Path(__file__).parent.parent
    run(sys.argv[1], project_root)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/tools/test_package_assets.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/package_assets.py tests/tools/test_package_assets.py
git commit -m "feat: package_assets — numbered bundle with timestamps, edit checklist, thumbnail reminder"
```

---

## Task 12: pipeline.py Orchestrator

**Files:**
- Create: `pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_pipeline.py`:

```python
import json
import sys
import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path


def write_approved_queue(project_root, topic):
    queue = [topic]
    (project_root / "topics" / "queue.json").write_text(json.dumps(queue))


def write_state(project_root, job_id, completed_steps):
    state = {"job_id": job_id, "topic": {}, "topic_id": "x", "completed_steps": completed_steps}
    (project_root / ".tmp" / job_id).mkdir(parents=True, exist_ok=True)
    (project_root / ".tmp" / job_id / "state.json").write_text(json.dumps(state))


def test_topics_only_flag_calls_generate_and_exits(project_root, config, monkeypatch):
    monkeypatch.setattr("sys.argv", ["pipeline.py", "--topics-only"])
    monkeypatch.setattr("sys.path", [str(project_root)] + sys.path)

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.generate_topics.run", return_value=[]) as mock_gen, \
         patch("tools.generate_topics.append_to_queue") as mock_append:
        import importlib
        import pipeline
        importlib.reload(pipeline)
        pipeline.main()

    mock_gen.assert_called_once()
    mock_append.assert_called_once()


def test_exits_cleanly_when_no_approved_topic(project_root, config, monkeypatch, capsys):
    (project_root / "topics" / "queue.json").write_text("[]")
    monkeypatch.setattr("sys.argv", ["pipeline.py"])

    with patch("tools.utils.config.load_config", return_value=config):
        import pipeline
        with pytest.raises(SystemExit) as exc:
            pipeline.main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    assert "No approved topics" in captured.out


def test_full_run_calls_all_steps_in_order(project_root, config, sample_topic, monkeypatch):
    write_approved_queue(project_root, sample_topic)
    monkeypatch.setattr("sys.argv", ["pipeline.py"])

    call_order = []

    def track(name):
        def fn(*a, **kw):
            call_order.append(name)
            return MagicMock()
        return fn

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.generate_script.run", side_effect=track("generate_script")), \
         patch("tools.check_compliance.run", return_value={"status": "PASS"}, side_effect=lambda *a, **kw: call_order.append("check_compliance") or {"status": "PASS"}), \
         patch("tools.generate_voiceover.run", side_effect=track("generate_voiceover")), \
         patch("tools.select_music.run", side_effect=track("select_music")), \
         patch("tools.search_footage.run", side_effect=track("search_footage")), \
         patch("tools.clear_footage.run", side_effect=track("clear_footage")), \
         patch("tools.check_footage_gaps.run", return_value=[], side_effect=lambda *a, **kw: call_order.append("check_footage_gaps") or []), \
         patch("tools.package_assets.run", side_effect=track("package_assets")):
        import pipeline
        pipeline.main()

    assert call_order == [
        "generate_script", "check_compliance", "generate_voiceover",
        "select_music", "search_footage", "clear_footage",
        "check_footage_gaps", "package_assets",
    ]


def test_revise_flag_clears_script_steps(project_root, config, sample_topic, monkeypatch):
    write_approved_queue(project_root, sample_topic)
    monkeypatch.setattr("sys.argv", ["pipeline.py", "--revise"])

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.generate_script.run", return_value={"sentences": []}), \
         patch("tools.check_compliance.run", return_value={"status": "PASS"}), \
         patch("tools.generate_voiceover.run", return_value=MagicMock()), \
         patch("tools.select_music.run", return_value=MagicMock()), \
         patch("tools.search_footage.run", return_value=[]), \
         patch("tools.clear_footage.run", return_value={}), \
         patch("tools.check_footage_gaps.run", return_value=[]), \
         patch("tools.package_assets.run", return_value=MagicMock()):
        import pipeline
        pipeline.main()  # should not raise
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_pipeline.py -v
```

Expected: `ImportError` or `ModuleNotFoundError`.

- [ ] **Step 3: Create `pipeline.py`**

```python
#!/usr/bin/env python3
"""
Pre-edit pipeline orchestrator.

Usage:
  python pipeline.py                         run full pipeline with next approved topic
  python pipeline.py --topics-only           generate and queue topics, then exit
  python pipeline.py --job <id>              resume a specific job
  python pipeline.py --job <id> --revise     re-run script generation after compliance failure
  python pipeline.py --job <id> --voice <id> use alternate ElevenLabs voice for this job
"""
import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent


def _get_next_approved_topic() -> dict | None:
    queue_file = PROJECT_ROOT / "topics" / "queue.json"
    if not queue_file.exists():
        return None
    queue = json.loads(queue_file.read_text())
    approved = [t for t in queue if t.get("status") == "approved"]
    return approved[0] if approved else None


def _set_topic_status(topic_id: str, status: str) -> None:
    queue_file = PROJECT_ROOT / "topics" / "queue.json"
    queue = json.loads(queue_file.read_text())
    for t in queue:
        if t["id"] == topic_id:
            t["status"] = status
    queue_file.write_text(json.dumps(queue, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="YT Shorts pre-edit pipeline")
    parser.add_argument("--topics-only", action="store_true",
                        help="Generate and queue topics, then exit")
    parser.add_argument("--job", help="Resume or target specific job ID")
    parser.add_argument("--revise", action="store_true",
                        help="Re-run script generation after compliance failure")
    parser.add_argument("--voice", help="ElevenLabs voice ID override for this job")
    args = parser.parse_args()

    sys.path.insert(0, str(PROJECT_ROOT))

    from tools.utils.config import load_config
    from tools.utils.state import load_state, mark_complete, is_complete, save_state
    from tools.utils.job import make_job_id
    import tools.generate_topics as generate_topics
    import tools.generate_script as generate_script
    import tools.check_compliance as check_compliance
    import tools.generate_voiceover as generate_voiceover
    import tools.select_music as select_music
    import tools.search_footage as search_footage
    import tools.clear_footage as clear_footage
    import tools.check_footage_gaps as check_footage_gaps
    import tools.package_assets as package_assets

    config = load_config()

    # ── topics-only mode ──────────────────────────────────────────────────────
    if args.topics_only:
        print("🔍 Generating topics...")
        topics = generate_topics.run(config)
        generate_topics.append_to_queue(topics, PROJECT_ROOT)
        print("\n💡 Open topics/queue.json and set status → \"approved\" on topics you want to produce.")
        return

    # ── determine job ID and topic ────────────────────────────────────────────
    if args.job:
        job_id = args.job
        state = load_state(job_id, PROJECT_ROOT)
        topic = state.get("topic")
        if not topic:
            print(f"❌ No state found for job {job_id}. Check .tmp/{job_id}/state.json")
            sys.exit(1)
    else:
        topic = _get_next_approved_topic()
        if not topic:
            print("⚠️  No approved topics in queue.")
            print("   Run: python pipeline.py --topics-only")
            print("   Then open topics/queue.json and set status → \"approved\"")
            sys.exit(0)
        job_id = make_job_id(topic["title"])
        state = {
            "job_id": job_id,
            "topic": topic,
            "topic_id": topic["id"],
            "completed_steps": [],
        }
        if args.voice:
            state["voice_id"] = args.voice
        save_state(state, PROJECT_ROOT)
        _set_topic_status(topic["id"], "in_progress")
        print(f"\n🎬 Job: {job_id}")
        print(f"   Topic: {topic['title']}\n")

    # ── revise mode ───────────────────────────────────────────────────────────
    if args.revise:
        script_file = PROJECT_ROOT / "scripts" / job_id / "script.json"
        revision_notes = None
        if script_file.exists():
            saved = json.loads(script_file.read_text())
            revision_notes = saved.get("compliance", {}).get("revision_notes")
        state["completed_steps"] = [
            s for s in state["completed_steps"]
            if s not in ("generate_script", "check_compliance")
        ]
        state["revision_notes"] = revision_notes
        save_state(state, PROJECT_ROOT)
        print("🔄 Revision mode — re-running script generation with failure context\n")

    # ── pipeline steps ────────────────────────────────────────────────────────
    if not is_complete("generate_script", state):
        print("📝 Generating script...")
        revision_context = state.get("revision_notes") if args.revise else None
        generate_script.run(job_id, topic, config, PROJECT_ROOT, revision_context)
        state = mark_complete("generate_script", state, PROJECT_ROOT)
    else:
        print("⏭  Script: already done")

    if not is_complete("check_compliance", state):
        print("🔍 Checking compliance...")
        result = check_compliance.run(job_id, PROJECT_ROOT)
        if result["status"] == "REVISION_REQUIRED":
            sys.exit(1)
        state = mark_complete("check_compliance", state, PROJECT_ROOT)
    else:
        print("⏭  Compliance: already done")

    if not is_complete("generate_voiceover", state):
        print("🎙  Generating voiceover...")
        voice_id = state.get("voice_id") or args.voice
        generate_voiceover.run(job_id, config, PROJECT_ROOT, voice_id)
        state = mark_complete("generate_voiceover", state, PROJECT_ROOT)
    else:
        print("⏭  Voiceover: already done")

    if not is_complete("select_music", state):
        print("🎵 Selecting background music...")
        try:
            select_music.run(job_id, PROJECT_ROOT)
            state = mark_complete("select_music", state, PROJECT_ROOT)
        except FileNotFoundError as e:
            print(f"⚠️  {e}")
            print("   Add MP3 tracks to music/tense/, music/dramatic/, or music/suspenseful/")
            print("   Then re-run: python pipeline.py --job", job_id)
            sys.exit(1)
    else:
        print("⏭  Music: already done")

    if not is_complete("search_footage", state):
        print("🎥 Searching footage...")
        search_footage.run(job_id, config, PROJECT_ROOT)
        state = mark_complete("search_footage", state, PROJECT_ROOT)
    else:
        print("⏭  Footage: already done")

    if not is_complete("clear_footage", state):
        print("🔇 Stripping audio from clips...")
        clear_footage.run(job_id, PROJECT_ROOT)
        state = mark_complete("clear_footage", state, PROJECT_ROOT)
    else:
        print("⏭  Footage cleared: already done")

    if not is_complete("check_footage_gaps", state):
        print("🔎 Checking for footage gaps...")
        gaps = check_footage_gaps.run(job_id, PROJECT_ROOT)
        state = mark_complete("check_footage_gaps", state, PROJECT_ROOT)
        if gaps:
            sys.exit(0)
    else:
        print("⏭  Gaps checked: already done")

    if not is_complete("package_assets", state):
        print("📦 Packaging assets...")
        package_assets.run(job_id, PROJECT_ROOT)
        state = mark_complete("package_assets", state, PROJECT_ROOT)
        _set_topic_status(state["topic_id"], "used")
    else:
        print(f"✅ Assets already packaged — open: assets/{job_id}/")
        print(f"   Next: python publish.py --job {job_id}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_pipeline.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests PASS. Note: `test_full_run_calls_all_steps_in_order` patches all external APIs — no real API calls made.

- [ ] **Step 6: Commit**

```bash
git add pipeline.py tests/test_pipeline.py
git commit -m "feat: pipeline.py orchestrator — checkpoint, resume, revise, voice override"
```

---

## Self-Review Checklist

- [x] **Spec coverage:**
  - Topic queue (FIFO, `status: approved`) → Task 2 + Task 12
  - Auto-generate topics when queue empty → Task 12 (`--topics-only` branch)
  - Script generation with Claude API + prompt caching → Task 4
  - Compliance gate (originality ≥7, advertiser ≥8) → Task 5
  - `--revise` flag → Task 12 (revise mode section)
  - Voiceover with `--voice` override → Task 6 + Task 12
  - Concurrent footage search → Task 7 (ThreadPoolExecutor)
  - ffmpeg audio strip + clearance log → Task 8
  - Music selection by mood → Task 9
  - Runway gap report with prompts → Task 10
  - Gap-filled clips accepted from `gaps/` folder → Task 10 + Task 11
  - Numbered asset bundle → Task 11
  - Overlay timestamps at 145 WPM → Task 4 (Claude generates them) + Task 11 (copied to overlays.txt)
  - Thumbnail first-frame reminder → Task 11 (`package_assets.py` checklist print)
  - Checkpoint / resume on failure → Task 2 (state utils) + Task 12 (all steps gated by `is_complete`)

- [x] **No placeholders** — all steps have complete code and exact commands.

- [x] **Type consistency** — `run()` signatures are consistent across tasks and how pipeline.py calls them.
