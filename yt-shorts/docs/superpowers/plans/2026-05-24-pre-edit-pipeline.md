# Pre-Edit Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `pipeline.py` and its 10 tool scripts so that one command takes an approved topic from `topics/queue.json` to a packaged asset bundle in `assets/<job-id>/` ready for CapCut editing — fully unattended, including AI footage gap-filling via the Runway API. Incorporates 7 automation improvements: interactive topic approval CLI, auto-retry compliance loop (3x), Claude footage query fallback, script word count validation, auto-thumbnail extraction, published topics deduplication, and prop-library Runway fallback.

**Architecture:** WAT (Workflows, Agents, Tools). `pipeline.py` is a thin orchestrator — it reads state, calls each tool script's `run()` function in order, checkpoints after each step, and halts cleanly at natural pause points (no approved topic, compliance failure, unfillable prop-library gaps). Each tool script is independently runnable and testable.

**Tech Stack:** Python 3.11+, `anthropic` SDK, `runwayml` SDK, `requests`, `python-dotenv`, `ffmpeg` (system binary via subprocess), `pytest`, `pytest-mock`

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
tools/check_footage_gaps.py          detect missing clips, split ai vs prop-library gaps
tools/generate_ai_footage.py         Runway API → auto-generate ai gaps → gaps/clip_XX.mp4
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
tests/tools/test_generate_ai_footage.py
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
runwayml>=0.1.0
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
RUNWAYML_API_SECRET=
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
        "word_count": 178,
        "estimated_duration_sec": 58,
        "tier_score": 9,
        "sentences": [
            {
                "index": 0,
                "text": "You've seen them in every action movie.",
                "section": "hook",
                "pexels_query": "laser sight rifle",
                "pixabay_query": "sniper rifle military",
                "needs_prop_library": True,
                "prop_description": "Rifle scope on dark surface, close-up glide shot",
                "needs_ai_video": False,
                "runway_prompt": None,
                "overlay": "EVERY MOVIE",
                "color_pop_words": ["EVERY"],
                "timestamp_approx": "0:00",
            },
            {
                "index": 1,
                "text": "But real snipers never use them in combat.",
                "section": "truth",
                "pexels_query": "military sniper rifle",
                "pixabay_query": "sniper combat",
                "needs_prop_library": False,
                "prop_description": None,
                "needs_ai_video": False,
                "runway_prompt": None,
                "overlay": "REAL SNIPERS",
                "color_pop_words": ["NEVER"],
                "timestamp_approx": "0:04",
            },
        ],
        "music_timing": {
            "dip_at_sentence_index": 1,
            "dip_timestamp_approx": "0:04",
            "dip_instruction": "Reduce music mid-range EQ or lower to -22dB",
            "swell_at_sentence_index": 1,
            "swell_timestamp_approx": "0:04",
            "swell_instruction": "Restore music to -16dB for final twist impact",
        },
        "loop": {
            "opening_shot_description": "Close-up glide across rifle scope on dark desk mat",
            "closing_shot_description": "Pull-back from scope to match exact opening frame",
            "loop_match_confirmed": True,
        },
        "background_music_mood": "Cinematic suspense, low-frequency atmospheric drone",
        "scores": {
            "originality": 8,
            "originality_breakdown": {
                "corrects_misconception": 2,
                "specific_historical_fact": 2,
                "non_obvious_mechanism": 2,
                "ironic_consequence_twist": 2,
                "beyond_footage_info": 0,
            },
            "advertiser_friendliness": 9,
            "advertiser_flags": [],
            "us_resonance": 9,
            "compliance_status": "PASS",
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


def test_run_injects_published_titles_into_prompt(project_root, config):
    (project_root / "topics").mkdir(parents=True, exist_ok=True)
    (project_root / "topics" / "published.json").write_text(json.dumps([
        {"title": "Why do snipers avoid laser sights?", "job_id": "old-job-1"},
    ]))
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_mock_response(SAMPLE_TOPICS_JSON)

        run(config, project_root)

    call_kwargs = mock_client.messages.create.call_args[1]
    user_msg = call_kwargs["messages"][0]["content"]
    assert "snipers avoid laser sights" in user_msg
    assert "AVOID" in user_msg
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

SYSTEM_PROMPT = """You are a topic researcher for a military and historical weapons
YouTube Shorts channel targeting US audiences.

Generate exactly 20 topic ideas. For each topic:

1. Write 3 title options using these formulas:
   - "Why did/do [group] [surprising behavior] with [familiar object]?"
   - "Why did [historical group] use [object] to [surprising action]?"
   - "Why [common military assumption] is completely wrong?"

2. Name the hook object and answer:
   "Would a non-military American recognize this object on sight?"
   YES / NO / MAYBE — with one sentence explanation

3. Describe the emotional paradox in one sentence:
   "The paradox is that [familiar/harmless thing] was actually [surprising truth]"

4. Score the topic using this rubric (0–10):
   - Object familiarity to non-military American: 0–3
   - Paradox is visual/emotional not just logical: 0–3
   - Stakes feel personally relatable: 0–2
   - Strong US military connection: 0–2

5. Assign tier:
   - Tier 1 (score 8–10): pursue immediately
   - Tier 2 (score 6–7): acceptable filler
   - Tier 3 (score <6): reject

DIVERSITY RULES — reject any topic that:
- Covers the same equipment type as a topic already in this list
- Involves geopolitical country comparisons
- Involves active conflicts from the last 5 years
- Requires knowledge of obscure military hardware to appreciate the hook

Sort output by tier score descending.
Output valid JSON array only. No preamble, no markdown."""


def load_published_titles(project_root: Path) -> list[str]:
    published_file = project_root / "topics" / "published.json"
    if not published_file.exists():
        return []
    entries = json.loads(published_file.read_text())
    return [e["title"] for e in entries[-30:]]


def run(config: dict, project_root: Path | None = None) -> list[dict]:
    client = anthropic.Anthropic(api_key=config["anthropic_api_key"])

    user_content = "Generate the 20 topics now."
    if project_root:
        published = load_published_titles(project_root)
        if published:
            avoid_list = "\n".join(f"- {t}" for t in published)
            user_content += f"\n\nAVOID topics similar to these already-published titles:\n{avoid_list}"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_content}],
    )
    topics = json.loads(response.content[0].text)
    # Only return Tier 1 and Tier 2 topics
    return [t for t in topics if t.get("tier") in ("1", "2", 1, 2)]


def append_to_queue(topics: list[dict], project_root: Path) -> None:
    queue_file = project_root / "topics" / "queue.json"
    queue_file.parent.mkdir(exist_ok=True)
    existing = json.loads(queue_file.read_text()) if queue_file.exists() else []
    now = datetime.now(timezone.utc).isoformat()
    for topic in topics:
        topic["id"] = str(uuid.uuid4())[:8]
        topic["status"] = "pending"
        topic["created_at"] = now
        # Flatten: use best title option as the canonical title
        if "title_options" in topic and not topic.get("title"):
            topic["title"] = topic["title_options"][0]
    existing.extend(topics)
    queue_file.write_text(json.dumps(existing, indent=2))


if __name__ == "__main__":
    from pathlib import Path
    from tools.utils.config import load_config
    project_root = Path(__file__).parent.parent
    cfg = load_config()
    topics = run(cfg, project_root)
    append_to_queue(topics, project_root)
    print(f"✅ Added {len(topics)} topics to queue.json")
    for t in topics[:5]:
        tier = t.get("tier", "?")
        score = t.get("tier_score", "?")
        print(f"  [Tier {tier} | {score}/10] {t.get('title', t.get('title_options', ['?'])[0])}")
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
    "status": "PASS",
    "word_count": 178,
    "estimated_duration_sec": 58,
    "tier_score": 9,
    "sentences": [
        {
            "index": 0,
            "text": "You've seen them in every action movie.",
            "section": "hook",
            "timestamp_approx": "0:00",
            "pexels_query": "laser sight rifle",
            "pixabay_query": "sniper rifle military",
            "needs_prop_library": True,
            "prop_description": "Rifle scope on dark surface, close-up glide",
            "needs_ai_video": False,
            "runway_prompt": None,
            "overlay": "EVERY MOVIE",
            "color_pop_words": ["EVERY"],
        }
    ],
    "music_timing": {
        "dip_at_sentence_index": 1,
        "dip_timestamp_approx": "0:04",
        "dip_instruction": "Reduce music mid-range EQ or lower to -22dB",
        "swell_at_sentence_index": 1,
        "swell_timestamp_approx": "0:04",
        "swell_instruction": "Restore music to -16dB for final twist impact",
    },
    "loop": {
        "opening_shot_description": "Close-up glide across rifle scope on dark desk mat",
        "closing_shot_description": "Pull-back from scope to match exact opening frame",
        "loop_match_confirmed": True,
    },
    "background_music_mood": "Cinematic suspense, low-frequency atmospheric drone",
    "scores": {
        "originality": 8,
        "originality_breakdown": {
            "corrects_misconception": 2,
            "specific_historical_fact": 2,
            "non_obvious_mechanism": 2,
            "ironic_consequence_twist": 2,
            "beyond_footage_info": 0,
        },
        "advertiser_friendliness": 9,
        "advertiser_flags": [],
        "us_resonance": 9,
        "compliance_status": "PASS",
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


def test_run_auto_regenerates_when_word_count_out_of_range(project_root, config, sample_topic):
    # First response has 1-word sentence (way under 168) → triggers re-generation
    short_script = {
        **SAMPLE_SCRIPT_RESPONSE,
        "status": "PASS",
        "sentences": [
            {
                "index": 0, "text": "Short.", "section": "hook",
                "timestamp_approx": "0:00", "pexels_query": "x", "pixabay_query": "x",
                "needs_prop_library": False, "prop_description": None,
                "needs_ai_video": False, "runway_prompt": None,
                "overlay": "SHORT", "color_pop_words": [],
            }
        ],
    }
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [
            make_mock_response(short_script),
            make_mock_response(SAMPLE_SCRIPT_RESPONSE),
        ]
        run("20260524-test-job", sample_topic, config, project_root)

    assert mock_client.messages.create.call_count == 2
    # Second call includes the word count correction in the message history
    second_call = mock_client.messages.create.call_args_list[1][1]
    messages = second_call["messages"]
    assert any("WORD COUNT CORRECTION" in str(m) for m in messages)
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

SYSTEM_PROMPT = """You are a professional YouTube Shorts script writer for a military and
historical weapons education channel. Write viral, myth-busting scripts that reveal
the surprising truth behind common assumptions about military equipment and history.

Output valid JSON only. No preamble, no markdown, no explanation.

═══════════════════════════════════════════
CRITICAL RULES — NEVER VIOLATE THESE
═══════════════════════════════════════════

RULE 1 — WORD COUNT
Every script must be exactly 168–183 words. Count precisely. Target: 178 words.
Below 168 or above 183: REVISION REQUIRED.

RULE 2 — ZERO SILENCE RULE
Write sentences of varying length to force natural pacing at 183 WPM with zero
pause gaps. Sentence tails should flow directly into the next sentence.

RULE 3 — FAMILIAR OBJECT HOOK
The hook object must be recognizable to any average American who has never served
in the military. Test: would someone who has never studied military history instantly
recognize this object from the hook sentence alone?
If NO → output {"status":"TOPIC_REJECTED","reason":"...","alternative_topics":["x3"]}

RULE 4 — IRONIC CONSEQUENCE TWIST
The final twist must start with: "But the final twist is that..."
It must describe a CONSEQUENCE or IRONIC FAILURE of the main answer — never just
an additional surprising fact. If the twist is just a fact → REVISION REQUIRED.

RULE 5 — NO BANNED CONTENT
Instantly reject topics containing: blood/gore/injury visualization, country vs
country geopolitical comparisons, active conflicts (within last 5 years), named
living political figures in military context, torture or war crimes descriptions.
If any present → {"status":"TOPIC_REJECTED","reason":"..."}

═══════════════════════════════════════════
THE 4-PART SCRIPT STRUCTURE
═══════════════════════════════════════════

SECTION 1 — HOOK (5–6 sec | 15–20 words)
Format: "Why did/do [group] [surprising behavior] with/involving [familiar object]?"
The object must look harmless, ordinary, or unexpected given the military context.

SECTION 2 — MISCONCEPTION (9–11 sec | 25–35 words)
Validate why the wrong assumption makes complete sense. Never mock the assumption.
Start with: "Most people assume..." or "At first glance..." or "Everyone assumed..."

SECTION 3 — TRUTH (22–34 sec | 70–95 words)
Must include at least one specific fact (date, number, name, or measurement).
Clear cause-and-effect explanation. Never use passive voice.
Do NOT start with "However" alone — add texture: "However, the real engineering truth..."

SECTION 4 — FINAL TWIST (10–17 sec | 35–55 words)
Must start with: "But the final twist is that..."
Must describe how the solution created a new problem, or how the strength became
a weakness. This drives comments, replays, and shares.

═══════════════════════════════════════════
PER-SENTENCE REQUIREMENTS
═══════════════════════════════════════════

For every sentence output:
- pexels_query: 3–5 word footage search query
- pixabay_query: 3–5 word alternative query
- needs_prop_library: true if this sentence needs a self-filmed desk prop close-up
- prop_description: describe exactly which prop and shot angle (null if not needed)
- needs_ai_video: true if no stock footage exists for this concept
- runway_prompt: complete Runway ML prompt (null if not needed)
- overlay: 1–3 words ALL CAPS (most visceral word in the sentence)
- color_pop_words: 1–2 words to flash neon yellow or red (most emotionally charged)

Timestamp calculation: 183 WPM. First sentence = 0:00.
Increment by (word_count / 183 * 60) seconds per sentence, formatted as M:SS.

═══════════════════════════════════════════
SCORING REQUIREMENTS
═══════════════════════════════════════════

ORIGINALITY SCORE (0–10):
+2 — Corrects a specific named common misconception
+2 — References a specific historical period, event, name, or measurement
+2 — Explains a non-obvious mechanism or technical detail
+2 — Final twist is an ironic consequence not just a surprising fact
+2 — Information cannot be learned just by watching the footage
Minimum passing score: 7/10

ADVERTISER-FRIENDLINESS SCORE (0–10):
Start at 10. Deduct:
-3 — Any graphic violence description or injury visualization
-3 — Any geopolitical country comparison
-2 — Coverage of active conflicts within last 5 years
-2 — Any named living political figure in military context
-1 — Any reference to casualties by name or number
Minimum passing score: 8/10

US RESONANCE SCORE (0–10):
+3 — US military branch, weapon, or historical event featured
+2 — Topic covered in a standard US history class
+2 — Paradox relatable to general American civilian life
+2 — No cultural references excluding American audience
+1 — Final twist has personal stakes
Target: 8+/10

Output PASS only if ALL three scores meet minimums.
Output REVISION REQUIRED if any score fails, with specific sentence-by-sentence notes."""


def _count_words(script: dict) -> int:
    return sum(len(s["text"].split()) for s in script.get("sentences", []))


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

    # Word count validation — auto-regenerate once if outside 168–183
    if script.get("status") != "TOPIC_REJECTED":
        wc = _count_words(script)
        if not (168 <= wc <= 183):
            delta = abs(wc - 183) if wc > 183 else abs(168 - wc)
            direction = "trimming" if wc > 183 else "adding"
            correction = (
                f"WORD COUNT CORRECTION: Your previous script had {wc} words. "
                f"Target is exactly 168–183 words (target: 178). "
                f"Please rewrite by {direction} approximately {delta} words."
            )
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=3000,
                system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
                messages=[
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": response.content[0].text},
                    {"role": "user", "content": correction},
                ],
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


def test_run_generates_fallback_queries_via_claude_when_both_apis_empty(project_root, config, sample_script):
    pexels_empty = MagicMock()
    pexels_empty.json.return_value = {"videos": []}
    pixabay_empty = MagicMock()
    pixabay_empty.json.return_value = {"hits": []}

    pexels_fallback = MagicMock()
    pexels_fallback.json.return_value = {
        "videos": [{"video_files": [{"height": 1080, "link": "http://fallback.mp4"}]}]
    }
    download_resp = MagicMock()
    download_resp.status_code = 200
    download_resp.content = b"fallback-video"

    mock_claude_resp = MagicMock()
    mock_claude_resp.content = [MagicMock(text='["military scope closeup", "tactical equipment macro"]')]

    with patch("requests.get", side_effect=[
        pexels_empty, pixabay_empty, pexels_fallback, download_resp,
        pexels_empty, pixabay_empty, pexels_fallback, download_resp,
    ]), patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = mock_claude_resp

        results = run("20260524-test-job", config, project_root)

    found = [r for r in results if r["status"] == "found"]
    assert len(found) == 2
    assert all(r.get("source") == "pexels_fallback" for r in found)
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


def _generate_fallback_queries(sentence: dict, config: dict) -> list[str]:
    import anthropic
    client = anthropic.Anthropic(api_key=config["anthropic_api_key"])
    prompt = (
        f"Generate 2 alternative stock footage search queries for:\n"
        f'"{sentence["text"]}"\n'
        f"Original queries returned no results: '{sentence['pexels_query']}', '{sentence['pixabay_query']}'\n"
        f"Rules: 3-5 words, no people, objects or environments only, visually dramatic.\n"
        f"Output JSON array of 2 strings only. No preamble."
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(response.content[0].text)


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

    # Both APIs empty — generate fallback queries via Claude and retry
    try:
        fallback_queries = _generate_fallback_queries(sentence, config)
        for fq in fallback_queries:
            pexels = search_pexels(fq, config["pexels_api_key"])
            url = best_pexels_url(pexels)
            if url and _download(url, out_path):
                return {"idx": idx, "status": "found", "source": "pexels_fallback", "path": str(out_path)}
    except Exception:
        pass  # Fallback failure is non-fatal — gap detection handles it

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
    result = run("20260524-test-job", project_root)
    assert result == {"ai_gaps": [], "prop_library_gaps": []}


def test_run_routes_ai_gap_correctly(project_root, sample_script):
    # sentence 1 has needs_prop_library=False → should be an ai_gap
    add_clip(project_root, "20260524-test-job", 0)
    result = run("20260524-test-job", project_root)
    assert len(result["ai_gaps"]) == 1
    assert result["ai_gaps"][0]["sentence_idx"] == 1
    assert result["prop_library_gaps"] == []


def test_run_routes_prop_library_gap_correctly(project_root, sample_script):
    # sentence 0 has needs_prop_library=True → should be a prop_library_gap
    add_clip(project_root, "20260524-test-job", 1)
    result = run("20260524-test-job", project_root)
    assert len(result["prop_library_gaps"]) == 1
    assert result["prop_library_gaps"][0]["sentence_idx"] == 0
    assert result["ai_gaps"] == []


def test_run_writes_gaps_md_with_runway_prompt(project_root, sample_script):
    (project_root / "footage" / "20260524-test-job").mkdir(parents=True)
    run("20260524-test-job", project_root)
    content = (project_root / "assets" / "20260524-test-job" / "footage-gaps.md").read_text()
    assert "Runway" in content
    assert "Gap #" in content


def test_run_writes_no_gaps_message_when_all_found(project_root, sample_script):
    add_clip(project_root, "20260524-test-job", 0)
    add_clip(project_root, "20260524-test-job", 1)
    run("20260524-test-job", project_root)
    assert "No footage gaps" in (
        project_root / "assets" / "20260524-test-job" / "footage-gaps.md"
    ).read_text()


def test_run_accepts_gap_filled_clip_from_gaps_folder(project_root, sample_script):
    footage_dir = project_root / "footage" / "20260524-test-job"
    footage_dir.mkdir(parents=True)
    (footage_dir / "gaps").mkdir()
    (footage_dir / "gaps" / "clip_00.mp4").write_bytes(b"gap-fill")
    add_clip(project_root, "20260524-test-job", 1)
    result = run("20260524-test-job", project_root)
    assert result == {"ai_gaps": [], "prop_library_gaps": []}
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


def run(job_id: str, project_root: Path) -> dict:
    """
    Returns {"ai_gaps": [...], "prop_library_gaps": [...]}

    ai_gaps         — missing clips where needs_prop_library is False.
                      These are auto-filled by generate_ai_footage.py.
    prop_library_gaps — missing clips requiring a self-filmed desk prop.
                      These halt the pipeline — user must film and drop in footage/<job-id>/gaps/.
    """
    script = json.loads((project_root / "scripts" / job_id / "script.json").read_text())
    footage_dir = project_root / "footage" / job_id

    ai_gaps = []
    prop_library_gaps = []

    for i, sentence in enumerate(script["sentences"]):
        stock_clip = footage_dir / f"clip_{i:02d}.mp4"
        gap_clip = footage_dir / "gaps" / f"clip_{i:02d}.mp4"
        if stock_clip.exists() or gap_clip.exists():
            continue

        runway_prompt = (
            sentence.get("runway_prompt")
            or f"Close-up of {sentence['pexels_query']}, cinematic, 4K, no people"
        )
        gap = {
            "sentence_idx": i,
            "text": sentence["text"],
            "overlay": sentence["overlay"],
            "runway_prompt": runway_prompt,
            "needs_prop_library": sentence.get("needs_prop_library", False),
            "prop_description": sentence.get("prop_description"),
        }
        if sentence.get("needs_prop_library"):
            prop_library_gaps.append(gap)
        else:
            ai_gaps.append(gap)

    out_dir = project_root / "assets" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    gaps_file = out_dir / "footage-gaps.md"

    total = len(ai_gaps) + len(prop_library_gaps)
    if total == 0:
        gaps_file.write_text("No footage gaps — all clips found.\n")
        print("✅ No footage gaps")
        return {"ai_gaps": [], "prop_library_gaps": []}

    lines = [f"# Footage Gaps — {job_id}\n"]

    if ai_gaps:
        lines += [
            f"## AI Gaps ({len(ai_gaps)}) — auto-generated by pipeline\n",
            "These will be filled automatically via the Runway API.\n",
        ]
        for g in ai_gaps:
            lines += [
                f"### Gap #{g['sentence_idx']:02d} — overlay: {g['overlay']}",
                f"**Script:** \"{g['text']}\"",
                f"**Runway Prompt:** `{g['runway_prompt']}`\n",
            ]

    if prop_library_gaps:
        lines += [
            f"## Prop Library Gaps ({len(prop_library_gaps)}) — MANUAL FILMING REQUIRED\n",
            "These clips require a self-filmed desk prop close-up.",
            f"Film the prop and save each as `clip_XX.mp4` in `footage/{job_id}/gaps/`",
            f"Then re-run: `python pipeline.py --job {job_id}`\n",
        ]
        for g in prop_library_gaps:
            lines += [
                f"### Gap #{g['sentence_idx']:02d} — overlay: {g['overlay']}",
                f"**Script:** \"{g['text']}\"",
                f"**Prop needed:** {g['prop_description'] or 'desk prop close-up'}\n",
            ]

    gaps_file.write_text("\n".join(lines))
    if ai_gaps:
        print(f"🤖 {len(ai_gaps)} AI gaps — will auto-generate via Runway API")
    if prop_library_gaps:
        print(f"⚠️  {len(prop_library_gaps)} prop library gaps → manual filming required")
        print(f"   See: {gaps_file}")
    return {"ai_gaps": ai_gaps, "prop_library_gaps": prop_library_gaps}


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

## Task 10b: generate_ai_footage.py

**Files:**
- Create: `tools/generate_ai_footage.py`
- Create: `tests/tools/test_generate_ai_footage.py`

- [ ] **Step 1: Write failing tests**

Create `tests/tools/test_generate_ai_footage.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from tools.generate_ai_footage import run


SAMPLE_GAPS = [
    {
        "sentence_idx": 1,
        "text": "But real snipers never use them in combat.",
        "overlay": "REAL SNIPERS",
        "runway_prompt": "Close-up of sniper rifle scope, cinematic, 4K, no people",
        "needs_prop_library": False,
        "prop_description": None,
    }
]


def make_mock_task(video_url="https://cdn.runwayml.com/fake-video.mp4"):
    task = MagicMock()
    task.output = [video_url]
    return task


def test_run_generates_and_downloads_clip(project_root):
    mock_task = make_mock_task()
    mock_download = MagicMock()
    mock_download.status_code = 200
    mock_download.content = b"fake-video-bytes"

    with patch("runwayml.RunwayML") as mock_cls, \
         patch("requests.get", return_value=mock_download):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.image_to_video.create.return_value.wait_for_task_output.return_value = mock_task

        results = run("20260524-test-job", SAMPLE_GAPS, project_root)

    assert len(results) == 1
    assert results[0]["status"] == "generated"
    out = project_root / "footage" / "20260524-test-job" / "gaps" / "clip_01.mp4"
    assert out.exists()
    assert out.read_bytes() == b"fake-video-bytes"


def test_run_uses_correct_api_params(project_root):
    mock_task = make_mock_task()
    mock_download = MagicMock()
    mock_download.status_code = 200
    mock_download.content = b"bytes"

    with patch("runwayml.RunwayML") as mock_cls, \
         patch("requests.get", return_value=mock_download):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.image_to_video.create.return_value.wait_for_task_output.return_value = mock_task

        run("20260524-test-job", SAMPLE_GAPS, project_root)

    call_kwargs = mock_client.image_to_video.create.call_args[1]
    assert call_kwargs["model"] == "gen4_turbo"
    assert call_kwargs["ratio"] == "720:1280"
    assert call_kwargs["duration"] == 5
    assert "sniper" in call_kwargs["prompt_text"].lower()


def test_run_skips_cached_clip(project_root):
    gap_dir = project_root / "footage" / "20260524-test-job" / "gaps"
    gap_dir.mkdir(parents=True)
    (gap_dir / "clip_01.mp4").write_bytes(b"already-there")

    with patch("runwayml.RunwayML") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        results = run("20260524-test-job", SAMPLE_GAPS, project_root)

    mock_client.image_to_video.create.assert_not_called()
    assert results[0]["status"] == "cached"


def test_run_records_failure_without_raising(project_root):
    from runwayml import TaskFailedError

    with patch("runwayml.RunwayML") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.image_to_video.create.return_value.wait_for_task_output.side_effect = (
            TaskFailedError("task failed", task_details={"reason": "content_policy"})
        )

        results = run("20260524-test-job", SAMPLE_GAPS, project_root)

    assert results[0]["status"] == "failed"
    assert "content_policy" in str(results[0].get("error", ""))


def test_run_returns_empty_for_empty_gaps(project_root):
    results = run("20260524-test-job", [], project_root)
    assert results == []


def test_run_halts_before_generating_when_cap_exceeded(project_root):
    # 6 uncached gaps, cap is 5 → should raise before calling Runway at all
    gaps = [
        {
            "sentence_idx": i,
            "text": f"Sentence {i}.",
            "overlay": "TEST",
            "runway_prompt": f"prompt {i}",
            "needs_prop_library": False,
            "prop_description": None,
        }
        for i in range(6)
    ]
    with patch("runwayml.RunwayML") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        with pytest.raises(RuntimeError, match="cost cap"):
            run("20260524-test-job", gaps, project_root, max_clips=5)

    mock_client.image_to_video.create.assert_not_called()


def test_run_cached_clips_do_not_count_toward_cap(project_root):
    # 6 gaps but 2 are already cached → only 4 need generation → under cap of 5
    gap_dir = project_root / "footage" / "20260524-test-job" / "gaps"
    gap_dir.mkdir(parents=True)
    (gap_dir / "clip_00.mp4").write_bytes(b"cached")
    (gap_dir / "clip_01.mp4").write_bytes(b"cached")

    gaps = [
        {
            "sentence_idx": i,
            "text": f"Sentence {i}.",
            "overlay": "TEST",
            "runway_prompt": f"prompt {i}",
            "needs_prop_library": False,
            "prop_description": None,
        }
        for i in range(6)
    ]
    mock_task = make_mock_task()
    mock_download = MagicMock()
    mock_download.status_code = 200
    mock_download.content = b"video"

    with patch("runwayml.RunwayML") as mock_cls, \
         patch("requests.get", return_value=mock_download):
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.image_to_video.create.return_value.wait_for_task_output.return_value = mock_task

        results = run("20260524-test-job", gaps, project_root, max_clips=5)

    # 2 cached + 4 generated = 6 results, no cap error
    assert len(results) == 6
    assert mock_client.image_to_video.create.call_count == 4
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_generate_ai_footage.py -v
```

Expected: `ImportError` — module not yet created.

- [ ] **Step 3: Create `tools/generate_ai_footage.py`**

```python
import json
from pathlib import Path
import requests
from runwayml import RunwayML, TaskFailedError


COST_PER_CLIP = 0.25   # gen4_turbo: 5 credits/sec × 5 sec × $0.01/credit


def run(
    job_id: str,
    gaps: list[dict],
    project_root: Path,
    max_clips: int = 5,
) -> list[dict]:
    """
    Auto-generates footage for ai_gaps using the Runway API (gen4_turbo, 720:1280).
    Skips clips already present in footage/<job-id>/gaps/.
    Halts before generating anything if uncached gap count exceeds max_clips.
    Returns list of {idx, status, path|error} per gap.
    Reads RUNWAYML_API_SECRET from environment automatically via the SDK.
    """
    if not gaps:
        return []

    # Pre-check: count clips that actually need generation (not already cached)
    gaps_dir = project_root / "footage" / job_id / "gaps"
    uncached = [
        g for g in gaps
        if not (gaps_dir / f"clip_{g['sentence_idx']:02d}.mp4").exists()
    ]

    if len(uncached) > max_clips:
        est_cost = len(uncached) * COST_PER_CLIP
        raise RuntimeError(
            f"Runway cost cap exceeded: {len(uncached)} clips needed "
            f"(~${est_cost:.2f}) but max_clips={max_clips} (~${max_clips * COST_PER_CLIP:.2f}).\n"
            f"Options:\n"
            f"  1. Approve: pipeline.py --job {job_id} --max-ai-clips {len(uncached)}\n"
            f"  2. Reduce AI gaps by improving stock footage search queries in script.json\n"
            f"  3. Film some clips yourself and drop in footage/{job_id}/gaps/"
        )

    client = RunwayML()
    results = []

    for gap in gaps:
        idx = gap["sentence_idx"]
        out_dir = project_root / "footage" / job_id / "gaps"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"clip_{idx:02d}.mp4"

        if out_path.exists():
            print(f"  ⏭  Gap {idx:02d}: cached")
            results.append({"idx": idx, "status": "cached", "path": str(out_path)})
            continue

        print(f"  🎬 Gap {idx:02d}: generating via Runway API (~${COST_PER_CLIP:.2f})...")
        try:
            task = client.image_to_video.create(
                model="gen4_turbo",
                prompt_text=gap["runway_prompt"],
                ratio="720:1280",   # 9:16 portrait for Shorts
                duration=5,
            ).wait_for_task_output()

            video_url = task.output[0]
            r = requests.get(video_url, timeout=60)
            r.raise_for_status()
            out_path.write_bytes(r.content)
            print(f"  ✅ Gap {idx:02d}: generated → {out_path.name}")
            results.append({"idx": idx, "status": "generated", "path": str(out_path)})

        except TaskFailedError as e:
            print(f"  ❌ Gap {idx:02d}: Runway task failed — {e.task_details}")
            results.append({"idx": idx, "status": "failed", "error": str(e.task_details)})

    generated = sum(1 for r in results if r["status"] == "generated")
    failed = sum(1 for r in results if r["status"] == "failed")
    actual_cost = generated * COST_PER_CLIP
    print(f"\n✅ AI footage: {generated}/{len(gaps)} generated "
          f"(~${actual_cost:.2f})" +
          (f", {failed} failed" if failed else ""))
    return results


if __name__ == "__main__":
    import sys
    from tools.utils.config import load_config
    project_root = Path(__file__).parent.parent
    job_id = sys.argv[1]
    # Read gaps from footage-gaps.md is not needed — pass gaps directly from pipeline
    print("Run via pipeline.py, not standalone.")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/tools/test_generate_ai_footage.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/generate_ai_footage.py tests/tools/test_generate_ai_footage.py
git commit -m "feat: generate_ai_footage — Runway API auto-fill for footage gaps"
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


def test_run_writes_overlays_with_timestamps_and_color_pops(project_root, sample_script):
    add_footage(project_root, "20260524-test-job", count=2)
    add_voiceover(project_root, "20260524-test-job")
    add_music(project_root, "20260524-test-job")

    run("20260524-test-job", project_root)

    overlays = (project_root / "assets" / "20260524-test-job" / "overlays.txt").read_text()
    assert "[0:00]" in overlays
    assert "EVERY MOVIE" in overlays
    assert "color pop" in overlays  # color pop hint included


def test_run_writes_music_timing_and_loop_files(project_root, sample_script):
    add_footage(project_root, "20260524-test-job", count=2)
    add_voiceover(project_root, "20260524-test-job")
    add_music(project_root, "20260524-test-job")

    run("20260524-test-job", project_root)

    assets = project_root / "assets" / "20260524-test-job"
    assert (assets / "music-timing.txt").exists()
    assert "DIP" in (assets / "music-timing.txt").read_text()
    assert (assets / "loop.txt").exists()
    assert "OPENING SHOT" in (assets / "loop.txt").read_text()


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


def test_run_extracts_thumbnail_from_first_clip(project_root, sample_script):
    add_footage(project_root, "20260524-test-job", count=2)
    add_voiceover(project_root, "20260524-test-job")
    add_music(project_root, "20260524-test-job")

    with patch("subprocess.run") as mock_sub:
        mock_sub.return_value = MagicMock(returncode=0)
        run("20260524-test-job", project_root)

    ffmpeg_calls = [str(c.args) for c in mock_sub.call_args_list]
    assert any("vframes" in c for c in ffmpeg_calls)
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
import subprocess
from pathlib import Path


def _extract_thumbnail(clip_path: Path, out_path: Path) -> bool:
    result = subprocess.run(
        ["ffmpeg", "-i", str(clip_path), "-vframes", "1", "-q:v", "2", "-y", str(out_path)],
        capture_output=True,
    )
    return result.returncode == 0


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

    # Extract thumbnail from first clip
    first_clip = out_dir / "01_clip.mp4"
    if first_clip.exists():
        if _extract_thumbnail(first_clip, out_dir / "thumbnail.jpg"):
            print("✅ thumbnail.jpg extracted from clip 01 (ready for YouTube upload)")
        else:
            print("⚠️  Thumbnail extraction failed — save first frame of clip 01 manually as thumbnail.jpg")

    # Copy voiceover
    shutil.copy2(voiceover_src, out_dir / "voiceover.mp3")

    # script.txt — timestamped lines for reference while editing
    script_lines = [f"=== {job_id} ===\n"]
    for s in sentences:
        script_lines.append(f"[{s['timestamp_approx']}] {s['text']}")
    (out_dir / "script.txt").write_text("\n".join(script_lines))

    # overlays.txt — timestamp + keyword + color pop words for each sentence
    overlay_lines = []
    for s in sentences:
        pops = " ".join(s.get("color_pop_words", []))
        pop_note = f"  (color pop: {pops})" if pops else ""
        overlay_lines.append(f"[{s['timestamp_approx']}] {s['overlay']}{pop_note}")
    (out_dir / "overlays.txt").write_text("\n".join(overlay_lines))

    # music-timing.txt — EQ markers for CapCut assembly
    music_timing = script.get("music_timing", {})
    if music_timing:
        timing_lines = [
            f"Music EQ markers for {job_id}",
            f"",
            f"DIP:   [{music_timing.get('dip_timestamp_approx', '?')}] sentence {music_timing.get('dip_at_sentence_index', '?')}",
            f"       {music_timing.get('dip_instruction', '')}",
            f"",
            f"SWELL: [{music_timing.get('swell_timestamp_approx', '?')}] sentence {music_timing.get('swell_at_sentence_index', '?')}",
            f"       {music_timing.get('swell_instruction', '')}",
        ]
        (out_dir / "music-timing.txt").write_text("\n".join(timing_lines))

    # loop.txt — opening and closing shot descriptions for seamless loop
    loop = script.get("loop", {})
    if loop:
        loop_lines = [
            f"Seamless Loop Instructions — {job_id}",
            f"",
            f"OPENING SHOT (clip 01): {loop.get('opening_shot_description', '')}",
            f"CLOSING SHOT (last clip): {loop.get('closing_shot_description', '')}",
            f"",
            f"Loop confirmed: {loop.get('loop_match_confirmed', False)}",
            f"",
            f"RULE: First frame and last frame must match exactly. Zero exceptions.",
        ]
        (out_dir / "loop.txt").write_text("\n".join(loop_lines))

    clips_count = len(list(out_dir.glob("*_clip.mp4")))
    has_voiceover = (out_dir / "voiceover.mp3").exists()
    has_music = (out_dir / "music.mp3").exists()
    has_gaps = (out_dir / "footage-gaps.md").exists() and "No footage gaps" not in (
        out_dir / "footage-gaps.md"
    ).read_text()

    has_loop = (out_dir / "loop.txt").exists()
    has_timing = (out_dir / "music-timing.txt").exists()

    print(f"""
✅ Asset bundle ready: assets/{job_id}/

📋 EDIT CHECKLIST — open this folder in CapCut:
  {"✅" if has_voiceover else "❌"} voiceover.mp3
  {"✅" if has_music else "⚠️ "} music.mp3  (add a track if missing)
  {clips_count} clips numbered for assembly
  ✅ script.txt  (timestamped reference)
  ✅ overlays.txt  (timestamps + color pop words)
  {"✅" if has_timing else "⚠️ "} music-timing.txt  (EQ dip/swell markers)
  {"✅" if has_loop else "⚠️ "} loop.txt  (opening/closing shot descriptions)
  {"⚠️  footage-gaps.md has unresolved gaps" if has_gaps else "✅ no footage gaps"}

⚠️  SEAMLESS LOOP: Opening clip and closing clip must match — read loop.txt.
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
         patch("tools.check_footage_gaps.run", side_effect=lambda *a, **kw: call_order.append("check_footage_gaps") or {"ai_gaps": [], "prop_library_gaps": []}), \
         patch("tools.generate_ai_footage.run", side_effect=track("generate_ai_footage")), \
         patch("tools.package_assets.run", side_effect=track("package_assets")):
        import pipeline
        pipeline.main()

    assert call_order == [
        "generate_script", "check_compliance", "generate_voiceover",
        "select_music", "search_footage", "clear_footage",
        "check_footage_gaps", "generate_ai_footage", "package_assets",
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
         patch("tools.check_footage_gaps.run", return_value={"ai_gaps": [], "prop_library_gaps": []}), \
         patch("tools.generate_ai_footage.run", return_value=[]), \
         patch("tools.package_assets.run", return_value=MagicMock()):
        import pipeline
        pipeline.main()  # should not raise


def test_approve_topics_flag_updates_queue_interactively(project_root, config, monkeypatch):
    monkeypatch.setattr("sys.argv", ["pipeline.py", "--approve-topics"])
    queue = [
        {"id": "t1", "title": "Why do snipers avoid lasers?", "tier": 1, "tier_score": 9, "status": "pending"},
        {"id": "t2", "title": "Why did the M14 fail?", "tier": 2, "tier_score": 7, "status": "pending"},
    ]
    (project_root / "topics" / "queue.json").write_text(json.dumps(queue))

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("builtins.input", side_effect=["y", "n"]):
        import importlib
        import pipeline
        importlib.reload(pipeline)
        pipeline.main()

    updated = json.loads((project_root / "topics" / "queue.json").read_text())
    assert updated[0]["status"] == "approved"
    assert updated[1]["status"] == "pending"


def test_compliance_auto_retries_on_failure(project_root, config, sample_topic, monkeypatch):
    write_approved_queue(project_root, sample_topic)
    monkeypatch.setattr("sys.argv", ["pipeline.py"])
    script_dir = project_root / "scripts" / "20260524-why-do-real-snipers"
    script_dir.mkdir(parents=True, exist_ok=True)
    (script_dir / "script.json").write_text(json.dumps({"compliance": {"revision_notes": "fix it"}}))

    compliance_results = [
        {"status": "REVISION_REQUIRED", "notes": "originality too low"},
        {"status": "PASS"},
    ]

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.generate_script.run", return_value={"sentences": []}) as mock_script, \
         patch("tools.check_compliance.run", side_effect=compliance_results), \
         patch("tools.generate_voiceover.run", return_value=MagicMock()), \
         patch("tools.select_music.run", return_value=MagicMock()), \
         patch("tools.search_footage.run", return_value=[]), \
         patch("tools.clear_footage.run", return_value={}), \
         patch("tools.check_footage_gaps.run", return_value={"ai_gaps": [], "prop_library_gaps": []}), \
         patch("tools.generate_ai_footage.run", return_value=[]), \
         patch("tools.package_assets.run", return_value=MagicMock()):
        import pipeline
        pipeline.main()

    # generate_script called twice: initial + 1 auto-retry
    assert mock_script.call_count == 2


def test_prop_gaps_attempt_runway_fallback_by_default(project_root, config, sample_topic, monkeypatch):
    write_approved_queue(project_root, sample_topic)
    monkeypatch.setattr("sys.argv", ["pipeline.py"])

    prop_gap = [{"sentence_idx": 0, "runway_prompt": "desk prop", "needs_prop_library": True}]

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.generate_script.run", return_value={"sentences": []}), \
         patch("tools.check_compliance.run", return_value={"status": "PASS"}), \
         patch("tools.generate_voiceover.run", return_value=MagicMock()), \
         patch("tools.select_music.run", return_value=MagicMock()), \
         patch("tools.search_footage.run", return_value=[]), \
         patch("tools.clear_footage.run", return_value={}), \
         patch("tools.check_footage_gaps.run", return_value={"ai_gaps": [], "prop_library_gaps": prop_gap}), \
         patch("tools.generate_ai_footage.run", return_value=[{"status": "generated"}]) as mock_runway, \
         patch("tools.package_assets.run", return_value=MagicMock()):
        import pipeline
        pipeline.main()

    mock_runway.assert_called()


def test_prop_gaps_halt_with_strict_props_flag(project_root, config, sample_topic, monkeypatch):
    write_approved_queue(project_root, sample_topic)
    monkeypatch.setattr("sys.argv", ["pipeline.py", "--strict-props"])

    prop_gap = [{"sentence_idx": 0, "runway_prompt": "desk prop", "needs_prop_library": True}]

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.generate_script.run", return_value={"sentences": []}), \
         patch("tools.check_compliance.run", return_value={"status": "PASS"}), \
         patch("tools.generate_voiceover.run", return_value=MagicMock()), \
         patch("tools.select_music.run", return_value=MagicMock()), \
         patch("tools.search_footage.run", return_value=[]), \
         patch("tools.clear_footage.run", return_value={}), \
         patch("tools.check_footage_gaps.run", return_value={"ai_gaps": [], "prop_library_gaps": prop_gap}), \
         patch("tools.generate_ai_footage.run", return_value=[]) as mock_runway, \
         patch("tools.package_assets.run", return_value=MagicMock()):
        with pytest.raises(SystemExit) as exc:
            import pipeline
            pipeline.main()
        assert exc.value.code == 0  # clean pause, not error

    mock_runway.assert_not_called()  # Runway not attempted with --strict-props
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


def _interactive_approve_topics(project_root: Path) -> None:
    queue_file = project_root / "topics" / "queue.json"
    if not queue_file.exists():
        print("No topics queue found. Run --topics-only first.")
        return
    queue = json.loads(queue_file.read_text())
    pending = [t for t in queue if t.get("status") == "pending"]
    if not pending:
        print("No pending topics to approve.")
        return

    print(f"\n{len(pending)} pending topics:\n")
    for t in pending:
        tier = t.get("tier", "?")
        score = t.get("tier_score", "?")
        print(f"  [Tier {tier} | {score}/10] {t['title']}")
        ans = input("  Approve? [y/n]: ").strip().lower()
        if ans == "y":
            t["status"] = "approved"
            print("  → Approved\n")
        else:
            print("  → Skipped\n")

    queue_file.write_text(json.dumps(queue, indent=2))
    approved = sum(1 for t in queue if t.get("status") == "approved")
    print(f"✅ {approved} topic(s) approved in queue.")


def main() -> None:
    parser = argparse.ArgumentParser(description="YT Shorts pre-edit pipeline")
    parser.add_argument("--topics-only", action="store_true",
                        help="Generate and queue topics, then exit")
    parser.add_argument("--approve-topics", action="store_true",
                        help="Interactively approve pending topics from queue.json")
    parser.add_argument("--job", help="Resume or target specific job ID")
    parser.add_argument("--revise", action="store_true",
                        help="Re-run script generation after compliance failure")
    parser.add_argument("--voice", help="ElevenLabs voice ID override for this job")
    parser.add_argument("--max-ai-clips", type=int, default=5,
                        help="Max Runway API generations per job (default 5, ~$1.25)")
    parser.add_argument("--strict-props", action="store_true",
                        help="Halt on prop-library gaps instead of attempting Runway fallback")
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
    import tools.generate_ai_footage as generate_ai_footage
    import tools.package_assets as package_assets

    config = load_config()

    # ── approve-topics mode ───────────────────────────────────────────────────
    if args.approve_topics:
        _interactive_approve_topics(PROJECT_ROOT)
        return

    # ── topics-only mode ──────────────────────────────────────────────────────
    if args.topics_only:
        print("🔍 Generating topics...")
        topics = generate_topics.run(config, PROJECT_ROOT)
        generate_topics.append_to_queue(topics, PROJECT_ROOT)
        print("\n💡 Run: python pipeline.py --approve-topics")
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
        MAX_COMPLIANCE_RETRIES = 3
        for attempt in range(MAX_COMPLIANCE_RETRIES):
            result = check_compliance.run(job_id, PROJECT_ROOT)
            if result["status"] == "PASS":
                break
            if attempt < MAX_COMPLIANCE_RETRIES - 1:
                print(f"   Auto-retry {attempt + 1}/{MAX_COMPLIANCE_RETRIES - 1} — regenerating script with revision context...")
                saved = json.loads((PROJECT_ROOT / "scripts" / job_id / "script.json").read_text())
                revision_context = saved.get("compliance", {}).get("revision_notes") or result.get("notes")
                generate_script.run(job_id, topic, config, PROJECT_ROOT, revision_context)
            else:
                print(f"\n❌ Script failed compliance after {MAX_COMPLIANCE_RETRIES} attempts.")
                print(f"   Manual fix: python pipeline.py --job {job_id} --revise")
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
        gap_result = check_footage_gaps.run(job_id, PROJECT_ROOT)
        state = mark_complete("check_footage_gaps", state, PROJECT_ROOT)
        state["gap_result"] = gap_result
        save_state(state, PROJECT_ROOT)
    else:
        print("⏭  Gaps checked: already done")
        gap_result = state.get("gap_result", {"ai_gaps": [], "prop_library_gaps": []})

    if not is_complete("generate_ai_footage", state):
        ai_gaps = gap_result.get("ai_gaps", [])
        if ai_gaps:
            print(f"🤖 Auto-generating {len(ai_gaps)} AI footage gap(s) via Runway...")
            try:
                results = generate_ai_footage.run(
                    job_id, ai_gaps, PROJECT_ROOT, max_clips=args.max_ai_clips
                )
            except RuntimeError as e:
                print(f"\n❌ {e}")
                sys.exit(1)
            failed = [r for r in results if r["status"] == "failed"]
            if failed:
                print(f"❌ {len(failed)} Runway generation(s) failed — see footage-gaps.md")
                sys.exit(1)
        state = mark_complete("generate_ai_footage", state, PROJECT_ROOT)
        save_state(state, PROJECT_ROOT)
    else:
        print("⏭  AI footage: already done")

    prop_gaps = gap_result.get("prop_library_gaps", [])
    if prop_gaps:
        if args.strict_props:
            print(f"\n⏸  PAUSED — {len(prop_gaps)} prop library clip(s) need manual filming.")
            print(f"   Instructions: assets/{job_id}/footage-gaps.md")
            print(f"   Film the props, save to footage/{job_id}/gaps/, then re-run:")
            print(f"   python pipeline.py --job {job_id}")
            sys.exit(0)
        else:
            print(f"🤖 Attempting Runway fallback for {len(prop_gaps)} prop-library gap(s)...")
            try:
                prop_results = generate_ai_footage.run(
                    job_id, prop_gaps, PROJECT_ROOT, max_clips=args.max_ai_clips
                )
                failed_props = [r for r in prop_results if r["status"] == "failed"]
                if failed_props:
                    print(f"⚠️  {len(failed_props)} prop gap(s) unresolved — film manually or review footage-gaps.md")
            except RuntimeError as e:
                print(f"\n⚠️  Runway cap hit for prop gaps: {e}")
                print(f"   Film manually or raise cap: --max-ai-clips N --strict-props to halt instead")

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
  - Topic tier scoring (Tier 1/2/3 rubric, TOPIC_REJECTED for non-familiar hooks) → Task 3
  - Script generation with Claude API + prompt caching → Task 4
  - v2 script rules: 168–183 words, 183 WPM, familiar object check, ironic twist template → Task 4
  - Compliance gate (originality ≥7, advertiser ≥8) → Task 5
  - `--revise` flag → Task 12 (revise mode section)
  - Voiceover with `--voice` override → Task 6 + Task 12
  - Concurrent footage search → Task 7 (ThreadPoolExecutor)
  - ffmpeg audio strip + clearance log → Task 8
  - Music selection by mood → Task 9
  - Runway gap report with prompts → Task 10
  - AI gaps auto-generated via Runway API (gen4_turbo, 720:1280, 5s) → Task 10b
  - Prop-library gaps halt pipeline with manual filming instructions → Task 10 + Task 12
  - Gap-filled clips accepted from `gaps/` folder → Task 10 + Task 11
  - Numbered asset bundle → Task 11
  - Overlay timestamps at 183 WPM + color pop words → Task 4 (Claude generates) + Task 11 (overlays.txt)
  - Music timing markers (dip/swell) → Task 4 (Claude generates) + Task 11 (music-timing.txt)
  - Seamless loop instructions → Task 4 (Claude generates) + Task 11 (loop.txt)
  - Thumbnail + seamless loop reminders → Task 11 (`package_assets.py` checklist print)
  - Checkpoint / resume on failure → Task 2 (state utils) + Task 12 (all steps gated by `is_complete`)
  - Interactive `--approve-topics` CLI (no JSON editing) → Task 12
  - Auto-retry compliance loop up to 3x before halting → Task 12
  - Script word count local validation + auto-regenerate once if outside 168–183 → Task 4
  - Footage query Claude fallback when both Pexels+Pixabay return 0 results → Task 7
  - Auto-thumbnail extraction via ffmpeg (thumbnail.jpg in asset bundle) → Task 11
  - Published topics deduplication (topics/published.json injected into generate_topics prompt) → Task 3
  - Prop-library → Runway fallback by default (`--strict-props` to halt instead) → Task 12

- [x] **No placeholders** — all steps have complete code and exact commands.

- [x] **Type consistency** — `run()` signatures are consistent across tasks and how pipeline.py calls them.
