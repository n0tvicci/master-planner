# Post-Edit Pipeline (publish.py) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `publish.py` and its 5 tool scripts so that one command takes a CapCut-exported `final.mp4` through compliance gate → metadata generation → YouTube upload (with AI disclosure + pinned comment) → monitoring card; plus a `--analytics` flag that pulls 72h country distribution from the YouTube Analytics API.

**Architecture:** WAT (Workflows, Agents, Tools). `publish.py` mirrors `pipeline.py` — thin orchestrator that reads `.tmp/<job-id>/state.json`, calls each tool script's `run()` in sequence, checkpoints after each step, and halts cleanly on gate failure or upload window miss. All tool scripts are independently runnable and testable.

**Tech Stack:** Python 3.11+, `anthropic` SDK (claude-haiku-4-5 for metadata), `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib`, `zoneinfo` (stdlib), `tzdata` (Windows timezone backend), `pytest`, `pytest-mock`

---

## File Map

```
tools/utils/youtube_auth.py          Google OAuth helper: credentials.json → token.json → service client
tools/pre_upload_gate.py             interactive compliance checklist → {"status": "PASS"} or {"status": "FAIL"}
tools/generate_metadata.py          Claude API → metadata/<job-id>/metadata.json
tools/upload_youtube.py             YouTube Data API v3 upload + pinned comment + EST window helpers
tools/monitor_upload.py             print monitoring reminder card, write uploaded_at to state
tools/pull_analytics.py             YouTube Analytics API v2 → compliance-logs/<job-id>/audience-report.json
publish.py                          post-edit pipeline orchestrator (project root)
tests/tools/test_pre_upload_gate.py
tests/tools/test_generate_metadata.py
tests/tools/test_upload_youtube.py
tests/tools/test_monitor_upload.py
tests/tools/test_pull_analytics.py
tests/test_publish.py
```

Modified:
```
requirements.txt                    add Google API + tzdata
.env.example                        add YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET
tests/conftest.py                   inject PUBLISH_PROJECT_ROOT, add sample_metadata fixture
```

---

## Task 1: Project Foundation (Plan B)

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`
- Modify: `tests/conftest.py`
- Create: `tools/utils/youtube_auth.py`

- [ ] **Step 1: Update requirements.txt**

Replace the entire file with:

```
anthropic>=0.40.0
runwayml>=0.1.0
requests>=2.31.0
python-dotenv>=1.0.0
google-api-python-client>=2.120.0
google-auth-httplib2>=0.2.0
google-auth-oauthlib>=1.2.0
tzdata>=2024.1
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 2: Update .env.example**

Replace the entire file with:

```
ANTHROPIC_API_KEY=
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
PEXELS_API_KEY=
PIXABAY_API_KEY=
RUNWAYML_API_SECRET=

# YouTube Data API — OAuth 2.0 (place credentials.json from Google Console in project root)
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
```

- [ ] **Step 3: Install new dependencies**

Run: `pip install -r requirements.txt`

Expected: all packages install without error.

- [ ] **Step 4: Update tests/conftest.py**

Replace the entire file with:

```python
import json
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def project_root(tmp_path):
    for d in ["topics", ".tmp", "scripts", "voiceover", "footage", "assets",
              "music/tense", "music/dramatic", "music/suspenseful",
              "compliance-logs", "metadata", "output"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)

    saved_env = {}
    for key in ("PIPELINE_PROJECT_ROOT", "PUBLISH_PROJECT_ROOT"):
        saved_env[key] = os.environ.get(key)
        os.environ[key] = str(tmp_path)

    root_str = str(Path(__file__).parent.parent)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    active_patches = []
    for module_name in ("pipeline", "publish"):
        try:
            mod = __import__(module_name)
            p = patch.object(mod, "PROJECT_ROOT", tmp_path)
            p.start()
            active_patches.append(p)
        except (ImportError, AttributeError):
            pass

    yield tmp_path

    for p in active_patches:
        p.stop()
    for key, val in saved_env.items():
        if val is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = val


@pytest.fixture
def config():
    return {
        "anthropic_api_key": "test-key",
        "elevenlabs_api_key": "test-key",
        "elevenlabs_voice_id": "test-voice-id",
        "pexels_api_key": "test-key",
        "pixabay_api_key": "test-key",
        "runwayml_api_secret": "test-key",
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


@pytest.fixture
def sample_metadata():
    return {
        "title": "Why real snipers never use laser sights",
        "description": (
            "Laser sights reveal your position to enemy night vision. "
            "Real military snipers rely on scope magnification and iron sights. "
            "The laser sight is a Hollywood invention — deadly in movies, fatal in combat. "
            "Follow for more military history myths debunked."
        ),
        "tags": [
            "military history", "snipers", "weapons facts", "laser sights",
            "combat tactics", "did you know", "military myths", "special forces",
            "rifle", "historical weapons",
        ],
        "pinned_comment": "Would you risk it with a laser sight in real combat? Drop your answer below.",
    }
```

- [ ] **Step 5: Create tools/utils/youtube_auth.py**

```python
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# All scopes needed by upload_youtube.py and pull_analytics.py combined.
# Requesting them together means one OAuth consent and one token.json.
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def get_credentials(project_root: Path) -> Credentials:
    creds_file = project_root / "credentials.json"
    token_file = project_root / "token.json"
    if not creds_file.exists():
        raise FileNotFoundError(
            "credentials.json not found.\n"
            "Download OAuth 2.0 Desktop credentials from Google Console "
            "(APIs & Services → Credentials → Create OAuth client → Desktop) "
            "and place the file in the project root."
        )
    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json())
    return creds


def get_youtube_client(project_root: Path):
    return build("youtube", "v3", credentials=get_credentials(project_root))


def get_analytics_client(project_root: Path):
    return build("youtubeAnalytics", "v2", credentials=get_credentials(project_root))
```

- [ ] **Step 6: Verify existing tests still pass**

Run: `pytest tests/ -v`

Expected: 65 passed (no regressions from conftest.py changes).

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example tests/conftest.py tools/utils/youtube_auth.py
git commit -m "feat: Plan B foundation — Google API deps, youtube_auth helper, conftest updates"
```

---

## Task 2: pre_upload_gate.py

**Files:**
- Create: `tests/tools/test_pre_upload_gate.py`
- Create: `tools/pre_upload_gate.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/tools/test_pre_upload_gate.py`:

```python
import pytest
from unittest.mock import patch
import tools.pre_upload_gate as pre_upload_gate


def test_all_yes_returns_pass():
    # All 5 checks "y", final confirm "YES"
    answers = ["y", "y", "y", "y", "y", "YES"]
    with patch("builtins.input", side_effect=answers):
        result = pre_upload_gate.run()
    assert result == {"status": "PASS"}


def test_any_no_returns_fail_with_check_listed():
    # Third check fails
    answers = ["y", "y", "n", "y", "y"]
    with patch("builtins.input", side_effect=answers):
        result = pre_upload_gate.run()
    assert result["status"] == "FAIL"
    assert any("54–60 sec" in c for c in result["failed_checks"])


def test_multiple_no_answers_all_listed():
    answers = ["n", "y", "n", "y", "y"]
    with patch("builtins.input", side_effect=answers):
        result = pre_upload_gate.run()
    assert result["status"] == "FAIL"
    assert len(result["failed_checks"]) == 2


def test_final_no_returns_fail():
    # All checks pass but user types NO at final prompt
    answers = ["y", "y", "y", "y", "y", "NO"]
    with patch("builtins.input", side_effect=answers):
        result = pre_upload_gate.run()
    assert result["status"] == "FAIL"
    assert result["failed_checks"] == ["Final confirmation not given"]


def test_final_lowercase_yes_returns_fail():
    # "yes" is not the same as "YES" — must be exact
    answers = ["y", "y", "y", "y", "y", "yes"]
    with patch("builtins.input", side_effect=answers):
        result = pre_upload_gate.run()
    assert result["status"] == "FAIL"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/tools/test_pre_upload_gate.py -v`

Expected: 5 failures (module not found or run() not defined).

- [ ] **Step 3: Implement tools/pre_upload_gate.py**

```python
CHECKS = [
    "Loop confirmed — first frame matches last frame?",
    "Clip count is 22–25?",
    "Total length 54–60 sec?",
    "Captions syllable-synced?",
    "No copyrighted audio audible?",
]


def run() -> dict:
    print("\nHUMAN SIGN-OFF REQUIRED before upload:")
    failed = []
    for check in CHECKS:
        ans = input(f"  □ {check}  [y/n]: ").strip().lower()
        if ans != "y":
            failed.append(check)

    if failed:
        print("\nThe following checks did not pass:")
        for c in failed:
            print(f"  ✗ {c}")
        print("\nFix issues and re-run publish.py to retry.")
        return {"status": "FAIL", "failed_checks": failed}

    confirm = input("\nType YES to confirm all checks passed, or NO to abort upload: ").strip()
    if confirm == "YES":
        return {"status": "PASS"}

    return {"status": "FAIL", "failed_checks": ["Final confirmation not given"]}


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/tools/test_pre_upload_gate.py -v`

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/pre_upload_gate.py tests/tools/test_pre_upload_gate.py
git commit -m "feat: pre_upload_gate — interactive compliance checklist before YouTube upload"
```

---

## Task 3: generate_metadata.py

**Files:**
- Create: `tests/tools/test_generate_metadata.py`
- Create: `tools/generate_metadata.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/tools/test_generate_metadata.py`:

```python
import json
import pytest
from unittest.mock import MagicMock, patch
import tools.generate_metadata as generate_metadata


def test_run_calls_claude_and_saves_metadata(project_root, config, sample_script):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps({
        "title": "Why snipers never use lasers",
        "description": "Laser sights reveal your position. Military snipers avoid them.",
        "tags": ["military", "snipers", "weapons facts"],
        "pinned_comment": "Would you use a laser in combat?",
    }))]

    with patch("tools.generate_metadata.anthropic.Anthropic") as mock_client_cls:
        mock_client_cls.return_value.messages.create.return_value = mock_response
        result = generate_metadata.run("20260524-test-job", config, project_root)

    assert result["title"] == "Why snipers never use lasers"
    metadata_path = project_root / "metadata" / "20260524-test-job" / "metadata.json"
    assert metadata_path.exists()
    saved = json.loads(metadata_path.read_text())
    assert saved["title"] == "Why snipers never use lasers"


def test_run_raises_if_script_missing(project_root, config):
    with pytest.raises(FileNotFoundError, match="script.json"):
        generate_metadata.run("no-such-job", config, project_root)


def test_run_raises_on_non_json_claude_response(project_root, config, sample_script):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Sorry, I cannot help with that.")]

    with patch("tools.generate_metadata.anthropic.Anthropic") as mock_client_cls:
        mock_client_cls.return_value.messages.create.return_value = mock_response
        with pytest.raises(RuntimeError, match="non-JSON"):
            generate_metadata.run("20260524-test-job", config, project_root)


def test_run_raises_on_empty_claude_response(project_root, config, sample_script):
    mock_response = MagicMock()
    mock_response.content = []

    with patch("tools.generate_metadata.anthropic.Anthropic") as mock_client_cls:
        mock_client_cls.return_value.messages.create.return_value = mock_response
        with pytest.raises(RuntimeError, match="empty response"):
            generate_metadata.run("20260524-test-job", config, project_root)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/tools/test_generate_metadata.py -v`

Expected: 4 failures.

- [ ] **Step 3: Implement tools/generate_metadata.py**

```python
import json
from pathlib import Path

import anthropic

SYSTEM_PROMPT = """You write YouTube metadata for a faceless military-and-historical-weapons Shorts channel.
Audience: US adults 25–55. Videos are 54–60 sec myth-busting educational shorts.

Return ONLY a JSON object — no markdown, no code fences, no explanation:
{
  "title": "<string, ≤100 chars, opens with a hook or surprising fact, no ALL-CAPS words, no '!!' or '???'>",
  "description": "<string, 3–5 sentences: first is keyword-rich for YouTube search, last is a CTA>",
  "tags": ["10 to 15 lowercase tags: include weapon type, historical era, and broad terms like 'military history', 'weapons facts', 'did you know'"],
  "pinned_comment": "<string, 1–2 sentences, ends with a question to drive replies>"
}"""


def run(job_id: str, config: dict, project_root: Path) -> dict:
    script_path = project_root / "scripts" / job_id / "script.json"
    if not script_path.exists():
        raise FileNotFoundError(f"script.json not found for job {job_id}")
    try:
        script = json.loads(script_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise RuntimeError(f"Could not read script.json: {e}") from e

    hook = script.get("hook", "")
    sentences = script.get("sentences", [])
    script_text = (hook + " " + " ".join(s.get("text", "") for s in sentences)).strip()

    client = anthropic.Anthropic(api_key=config["anthropic_api_key"])
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Script:\n{script_text}"}],
    )

    if not response.content:
        raise RuntimeError("Claude API returned empty response for metadata generation")

    try:
        metadata = json.loads(response.content[0].text)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Claude returned non-JSON response: {e}\nRaw: {response.content[0].text[:200]}"
        ) from e

    out_dir = project_root / "metadata" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    return metadata


if __name__ == "__main__":
    import argparse
    from tools.utils.config import load_config

    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    args = parser.parse_args()
    cfg = load_config()
    import pathlib
    result = run(args.job, cfg, pathlib.Path(__file__).parent.parent)
    print(json.dumps(result, indent=2))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/tools/test_generate_metadata.py -v`

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/generate_metadata.py tests/tools/test_generate_metadata.py
git commit -m "feat: generate_metadata — Claude Haiku generates title/description/tags/pinned comment"
```

---

## Task 4: upload_youtube.py

**Files:**
- Create: `tests/tools/test_upload_youtube.py`
- Create: `tools/upload_youtube.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/tools/test_upload_youtube.py`:

```python
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import tools.upload_youtube as upload_youtube

EST = ZoneInfo("America/New_York")


# ── Window helpers ──────────────────────────────────────────────────────────

def test_is_in_upload_window_true_tuesday_morning():
    tue_8am = datetime(2026, 5, 26, 8, 0, tzinfo=EST)  # Tuesday 8 AM
    with patch("tools.upload_youtube._now", return_value=tue_8am):
        assert upload_youtube.is_in_upload_window() is True


def test_is_in_upload_window_false_monday():
    mon_8am = datetime(2026, 5, 25, 8, 0, tzinfo=EST)  # Monday 8 AM
    with patch("tools.upload_youtube._now", return_value=mon_8am):
        assert upload_youtube.is_in_upload_window() is False


def test_is_in_upload_window_false_outside_hours():
    tue_10am = datetime(2026, 5, 26, 10, 0, tzinfo=EST)  # Tuesday 10 AM (window 7–9)
    with patch("tools.upload_youtube._now", return_value=tue_10am):
        assert upload_youtube.is_in_upload_window() is False


def test_is_in_upload_window_true_saturday_morning():
    sat_10am = datetime(2026, 5, 30, 10, 0, tzinfo=EST)  # Saturday 10 AM
    with patch("tools.upload_youtube._now", return_value=sat_10am):
        assert upload_youtube.is_in_upload_window() is True


def test_next_upload_window_from_monday_returns_tuesday():
    # Monday 9 AM → next window is Tuesday 7 AM
    mon_9am = datetime(2026, 5, 25, 9, 0, tzinfo=EST)
    with patch("tools.upload_youtube._now", return_value=mon_9am):
        nw = upload_youtube.next_upload_window()
    assert nw.isoweekday() == 2  # Tuesday
    assert nw.hour == 7


def test_next_upload_window_from_tuesday_after_window():
    # Tuesday 9:30 AM (window closed) → next is Wednesday 7 AM
    tue_930am = datetime(2026, 5, 26, 9, 30, tzinfo=EST)
    with patch("tools.upload_youtube._now", return_value=tue_930am):
        nw = upload_youtube.next_upload_window()
    assert nw.isoweekday() == 3  # Wednesday
    assert nw.hour == 7


def test_next_upload_window_from_tuesday_before_window():
    # Tuesday 6:30 AM (window not yet open) → same day 7 AM
    tue_630am = datetime(2026, 5, 26, 6, 30, tzinfo=EST)
    with patch("tools.upload_youtube._now", return_value=tue_630am):
        nw = upload_youtube.next_upload_window()
    assert nw.isoweekday() == 2  # Still Tuesday
    assert nw.hour == 7


# ── Upload + pin ─────────────────────────────────────────────────────────────

def _make_mock_youtube():
    mock_yt = MagicMock()
    mock_yt.videos.return_value.insert.return_value.execute.return_value = {"id": "abc123"}
    mock_yt.commentThreads.return_value.insert.return_value.execute.return_value = {}
    return mock_yt


def test_run_uploads_and_returns_video_id(tmp_path, sample_metadata):
    video_path = tmp_path / "final.mp4"
    video_path.write_bytes(b"fake video data")
    (tmp_path / "credentials.json").write_text("{}")
    (tmp_path / "token.json").write_text("{}")

    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_yt = _make_mock_youtube()

    with patch("tools.utils.youtube_auth.Credentials.from_authorized_user_file",
               return_value=mock_creds), \
         patch("tools.utils.youtube_auth.build", return_value=mock_yt), \
         patch("tools.upload_youtube.MediaFileUpload"):
        result = upload_youtube.run("test-job", video_path, sample_metadata, tmp_path)

    assert result["video_id"] == "abc123"
    assert result["url"] == "https://youtube.com/shorts/abc123"


def test_run_pins_comment_after_upload(tmp_path, sample_metadata):
    video_path = tmp_path / "final.mp4"
    video_path.write_bytes(b"fake")
    (tmp_path / "credentials.json").write_text("{}")
    (tmp_path / "token.json").write_text("{}")

    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_yt = _make_mock_youtube()

    with patch("tools.utils.youtube_auth.Credentials.from_authorized_user_file",
               return_value=mock_creds), \
         patch("tools.utils.youtube_auth.build", return_value=mock_yt), \
         patch("tools.upload_youtube.MediaFileUpload"):
        upload_youtube.run("test-job", video_path, sample_metadata, tmp_path)

    mock_yt.commentThreads.return_value.insert.assert_called_once()
    call_kwargs = mock_yt.commentThreads.return_value.insert.call_args[1]
    pinned_text = (
        call_kwargs["body"]["snippet"]["topLevelComment"]["snippet"]["textOriginal"]
    )
    assert pinned_text == sample_metadata["pinned_comment"]


def test_run_pin_failure_is_non_fatal(tmp_path, sample_metadata):
    video_path = tmp_path / "final.mp4"
    video_path.write_bytes(b"fake")
    (tmp_path / "credentials.json").write_text("{}")
    (tmp_path / "token.json").write_text("{}")

    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_yt = _make_mock_youtube()
    mock_yt.commentThreads.return_value.insert.return_value.execute.side_effect = Exception(
        "video still processing"
    )

    with patch("tools.utils.youtube_auth.Credentials.from_authorized_user_file",
               return_value=mock_creds), \
         patch("tools.utils.youtube_auth.build", return_value=mock_yt), \
         patch("tools.upload_youtube.MediaFileUpload"):
        result = upload_youtube.run("test-job", video_path, sample_metadata, tmp_path)

    assert result["video_id"] == "abc123"  # upload still succeeded


def test_run_raises_if_credentials_json_missing(tmp_path, sample_metadata):
    video_path = tmp_path / "final.mp4"
    video_path.write_bytes(b"fake")
    # credentials.json intentionally NOT created
    with pytest.raises(FileNotFoundError, match="credentials.json"):
        upload_youtube.run("test-job", video_path, sample_metadata, tmp_path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/tools/test_upload_youtube.py -v`

Expected: 11 failures.

- [ ] **Step 3: Implement tools/upload_youtube.py**

```python
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from googleapiclient.http import MediaFileUpload

from tools.utils.youtube_auth import get_youtube_client

EST = ZoneInfo("America/New_York")

# isoweekday: 1=Mon 2=Tue 3=Wed 4=Thu 5=Fri 6=Sat 7=Sun
# Optimal windows: Tue/Wed/Thu 7–9 AM, Sat/Sun 9–11 AM (all EST)
_WINDOWS = {2: (7, 9), 3: (7, 9), 4: (7, 9), 6: (9, 11), 7: (9, 11)}


def _now() -> datetime:
    return datetime.now(tz=EST)


def is_in_upload_window() -> bool:
    now = _now()
    window = _WINDOWS.get(now.isoweekday())
    if window is None:
        return False
    return window[0] <= now.hour < window[1]


def next_upload_window() -> datetime:
    now = _now()
    for offset in range(8):
        candidate = now + timedelta(days=offset)
        window = _WINDOWS.get(candidate.isoweekday())
        if window is None:
            continue
        start_hour = window[0]
        window_start = candidate.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        if window_start > now:
            return window_start
    raise RuntimeError("Could not find next upload window within 7 days")


def run(job_id: str, video_path: Path, metadata: dict, project_root: Path) -> dict:
    youtube = get_youtube_client(project_root)

    body = {
        "snippet": {
            "title": metadata["title"],
            "description": metadata["description"],
            "tags": metadata["tags"],
            "categoryId": "19",
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredAiGeneratedContent": True,
            "madeForKids": False,
        },
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    response = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    ).execute()
    video_id = response["id"]

    try:
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {"textOriginal": metadata["pinned_comment"]}
                    },
                }
            },
        ).execute()
    except Exception as e:
        print(f"  Warning: pinned comment failed ({e}). Pin manually in YouTube Studio.")

    return {"video_id": video_id, "url": f"https://youtube.com/shorts/{video_id}"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/tools/test_upload_youtube.py -v`

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/upload_youtube.py tests/tools/test_upload_youtube.py
git commit -m "feat: upload_youtube — YouTube Data API v3 upload, pinned comment, EST window helpers"
```

---

## Task 5: monitor_upload.py + pull_analytics.py

**Files:**
- Create: `tests/tools/test_monitor_upload.py`
- Create: `tools/monitor_upload.py`
- Create: `tests/tools/test_pull_analytics.py`
- Create: `tools/pull_analytics.py`

- [ ] **Step 1: Write the failing tests for monitor_upload.py**

Create `tests/tools/test_monitor_upload.py`:

```python
import json
import pytest
from tools.utils.state import load_state
import tools.monitor_upload as monitor_upload


def test_run_prints_video_url(project_root, capsys):
    monitor_upload.run("test-job", "vid123", "Why Snipers Avoid Lasers", project_root)
    out = capsys.readouterr().out
    assert "vid123" in out
    assert "youtube.com/shorts/vid123" in out


def test_run_prints_24h_48h_72h_checkpoints(project_root, capsys):
    monitor_upload.run("test-job", "vid123", "Test Title", project_root)
    out = capsys.readouterr().out
    assert "24h" in out
    assert "48h" in out
    assert "72h" in out


def test_run_writes_uploaded_at_to_state(project_root):
    monitor_upload.run("test-job", "vid123", "Test Title", project_root)
    state = load_state("test-job", project_root)
    assert "uploaded_at" in state
    assert state["uploaded_at"]  # non-empty string


def test_run_prints_analytics_command(project_root, capsys):
    monitor_upload.run("test-job", "vid123", "Test Title", project_root)
    out = capsys.readouterr().out
    assert "--analytics" in out
    assert "test-job" in out
```

- [ ] **Step 2: Write the failing tests for pull_analytics.py**

Create `tests/tools/test_pull_analytics.py`:

```python
import json
import pytest
from unittest.mock import MagicMock, patch
import tools.pull_analytics as pull_analytics


def _mock_analytics_response(rows):
    mock_resp = {"rows": rows, "columnHeaders": [{"name": "country"}, {"name": "views"}]}
    mock_client = MagicMock()
    mock_client.reports.return_value.query.return_value.execute.return_value = mock_resp
    return mock_client


def test_run_writes_green_report(project_root):
    rows = [["US", 600], ["CA", 200], ["GB", 200]]
    mock_client = _mock_analytics_response(rows)

    with patch("tools.pull_analytics.get_analytics_client", return_value=mock_client):
        report = pull_analytics.run("test-job", "vid123", project_root)

    assert report["flag"] == "GREEN"
    assert report["us_share"] == pytest.approx(0.6)
    assert (project_root / "compliance-logs" / "test-job" / "audience-report.json").exists()


def test_run_writes_yellow_report(project_root):
    rows = [["US", 450], ["IN", 300], ["CA", 250]]
    mock_client = _mock_analytics_response(rows)

    with patch("tools.pull_analytics.get_analytics_client", return_value=mock_client):
        report = pull_analytics.run("test-job", "vid123", project_root)

    assert report["flag"] == "YELLOW"
    assert 0.4 <= report["us_share"] <= 0.5


def test_run_writes_red_report(project_root):
    rows = [["IN", 700], ["US", 150], ["PH", 150]]
    mock_client = _mock_analytics_response(rows)

    with patch("tools.pull_analytics.get_analytics_client", return_value=mock_client):
        report = pull_analytics.run("test-job", "vid123", project_root)

    assert report["flag"] == "RED"
    assert report["us_share"] < 0.4


def test_run_handles_no_views_returns_red(project_root):
    mock_client = _mock_analytics_response([])

    with patch("tools.pull_analytics.get_analytics_client", return_value=mock_client):
        report = pull_analytics.run("test-job", "vid123", project_root)

    assert report["flag"] == "RED"
    assert report["us_share"] == 0.0


def test_run_report_json_saved_correctly(project_root):
    rows = [["US", 800], ["CA", 200]]
    mock_client = _mock_analytics_response(rows)

    with patch("tools.pull_analytics.get_analytics_client", return_value=mock_client):
        pull_analytics.run("test-job", "vid123", project_root)

    saved = json.loads(
        (project_root / "compliance-logs" / "test-job" / "audience-report.json").read_text()
    )
    assert saved["video_id"] == "vid123"
    assert saved["job_id"] == "test-job"
    assert "pulled_at" in saved
    assert saved["country_breakdown"]["US"] == 800
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/tools/test_monitor_upload.py tests/tools/test_pull_analytics.py -v`

Expected: 10 failures.

- [ ] **Step 4: Implement tools/monitor_upload.py**

```python
from datetime import datetime, timezone
from pathlib import Path

from tools.utils.state import load_state, save_state


def run(job_id: str, video_id: str, title: str, project_root: Path) -> None:
    state = load_state(job_id, project_root)
    state["uploaded_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state, project_root)

    url = f"https://youtube.com/shorts/{video_id}"
    print(f"""
Uploaded: {title}
   Video ID: {video_id}
   URL: {url}

24h  -> Check for copyright claims
48h  -> Confirm monetization status is green
72h  -> Check country distribution (target: 50%+ US)
       Run: python publish.py --job {job_id} --analytics
""")
```

- [ ] **Step 5: Implement tools/pull_analytics.py**

```python
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.utils.youtube_auth import get_analytics_client


def run(job_id: str, video_id: str, project_root: Path) -> dict:
    analytics = get_analytics_client(project_root)

    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    response = analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        metrics="views",
        dimensions="country",
        filters=f"video=={video_id}",
        sort="-views",
    ).execute()

    rows = response.get("rows", [])
    total = sum(int(r[1]) for r in rows)
    us_views = next((int(r[1]) for r in rows if r[0] == "US"), 0)
    us_share = us_views / total if total > 0 else 0.0

    if us_share > 0.5:
        flag = "GREEN"
        notes = "US share >50% — target met"
    elif us_share >= 0.4:
        flag = "YELLOW"
        notes = "US share 40-50% — review upload timing"
    else:
        flag = "RED"
        notes = "US share <40% — review topic tier"

    report = {
        "video_id": video_id,
        "job_id": job_id,
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "us_share": round(us_share, 4),
        "flag": flag,
        "notes": notes,
        "country_breakdown": {r[0]: int(r[1]) for r in rows},
    }

    log_dir = project_root / "compliance-logs" / job_id
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "audience-report.json").write_text(json.dumps(report, indent=2))
    return report
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/tools/test_monitor_upload.py tests/tools/test_pull_analytics.py -v`

Expected: 10 passed.

- [ ] **Step 7: Commit**

```bash
git add tools/monitor_upload.py tests/tools/test_monitor_upload.py \
        tools/pull_analytics.py tests/tools/test_pull_analytics.py
git commit -m "feat: monitor_upload + pull_analytics — monitoring card and 72h audience report"
```

---

## Task 6: publish.py Orchestrator

**Files:**
- Create: `tests/test_publish.py`
- Create: `publish.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_publish.py`:

```python
import importlib
import json
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _reload_publish(project_root):
    if "publish" in sys.modules:
        del sys.modules["publish"]
    import os
    os.environ["PUBLISH_PROJECT_ROOT"] = str(project_root)
    import publish
    importlib.reload(publish)
    return publish


def _write_final_video(project_root, job_id):
    out_dir = project_root / "output" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "final.mp4").write_bytes(b"fake video")


def _write_metadata(project_root, job_id, meta):
    md_dir = project_root / "metadata" / job_id
    md_dir.mkdir(parents=True, exist_ok=True)
    (md_dir / "metadata.json").write_text(json.dumps(meta))


def _write_state(project_root, job_id, state_data):
    tmp_dir = project_root / ".tmp" / job_id
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / "state.json").write_text(json.dumps(state_data))


# ── Prerequisite guard ────────────────────────────────────────────────────────

def test_missing_final_video_exits_with_error(project_root, monkeypatch):
    publish = _reload_publish(project_root)
    monkeypatch.setattr(sys, "argv", ["publish.py", "--job", "test-job"])
    with pytest.raises(SystemExit) as exc_info:
        publish.main(project_root)
    assert exc_info.value.code == 1


# ── Gate failure ──────────────────────────────────────────────────────────────

def test_gate_failure_exits_nonzero(project_root, monkeypatch, sample_metadata):
    _write_final_video(project_root, "test-job")
    publish = _reload_publish(project_root)
    monkeypatch.setattr(sys, "argv", ["publish.py", "--job", "test-job"])

    with patch("tools.pre_upload_gate.run",
               return_value={"status": "FAIL", "failed_checks": ["Clip count is 22-25?"]}), \
         pytest.raises(SystemExit) as exc_info:
        publish.main(project_root)

    assert exc_info.value.code == 1


# ── Dry run ───────────────────────────────────────────────────────────────────

def test_dry_run_generates_metadata_and_skips_upload(
    project_root, monkeypatch, config, sample_script, sample_metadata, capsys
):
    _write_final_video(project_root, "20260524-test-job")
    publish = _reload_publish(project_root)
    monkeypatch.setattr(sys, "argv", ["publish.py", "--job", "20260524-test-job", "--dry-run"])

    mock_upload = MagicMock()

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.generate_metadata.run", return_value=sample_metadata) as mock_meta, \
         patch("tools.pre_upload_gate.run", return_value={"status": "PASS"}), \
         patch("tools.upload_youtube.run", mock_upload):
        # Write metadata as if generate_metadata.run created it
        _write_metadata(project_root, "20260524-test-job", sample_metadata)
        publish.main(project_root)

    mock_upload.assert_not_called()
    out = capsys.readouterr().out
    assert "DRY RUN" in out


# ── Upload window ─────────────────────────────────────────────────────────────

def test_outside_upload_window_exits_zero(
    project_root, monkeypatch, config, sample_script, sample_metadata
):
    _write_final_video(project_root, "20260524-test-job")
    _write_metadata(project_root, "20260524-test-job", sample_metadata)
    _write_state(project_root, "20260524-test-job", {
        "job_id": "20260524-test-job",
        "completed_steps": ["pre_upload_gate", "generate_metadata"],
    })
    publish = _reload_publish(project_root)
    monkeypatch.setattr(sys, "argv", ["publish.py", "--job", "20260524-test-job"])

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.upload_youtube.is_in_upload_window", return_value=False), \
         patch("tools.upload_youtube.next_upload_window") as mock_nw, \
         pytest.raises(SystemExit) as exc_info:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        mock_nw.return_value = datetime(2026, 5, 26, 7, 0, tzinfo=ZoneInfo("America/New_York"))
        publish.main(project_root)

    assert exc_info.value.code == 0


def test_immediate_flag_skips_window_check(
    project_root, monkeypatch, config, sample_script, sample_metadata
):
    _write_final_video(project_root, "20260524-test-job")
    _write_metadata(project_root, "20260524-test-job", sample_metadata)
    _write_state(project_root, "20260524-test-job", {
        "job_id": "20260524-test-job",
        "completed_steps": ["pre_upload_gate", "generate_metadata"],
    })
    publish = _reload_publish(project_root)
    monkeypatch.setattr(
        sys, "argv", ["publish.py", "--job", "20260524-test-job", "--immediate"]
    )

    mock_window_check = MagicMock(return_value=False)

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.upload_youtube.is_in_upload_window", mock_window_check), \
         patch("tools.upload_youtube.run",
               return_value={"video_id": "vid123", "url": "https://youtube.com/shorts/vid123"}), \
         patch("tools.monitor_upload.run"):
        publish.main(project_root)

    mock_window_check.assert_not_called()


# ── Happy path ────────────────────────────────────────────────────────────────

def test_happy_path_calls_all_steps_in_order(
    project_root, monkeypatch, config, sample_script, sample_metadata
):
    _write_final_video(project_root, "20260524-test-job")
    publish = _reload_publish(project_root)
    monkeypatch.setattr(
        sys, "argv", ["publish.py", "--job", "20260524-test-job", "--immediate"]
    )

    call_order = []

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.pre_upload_gate.run",
               side_effect=lambda: call_order.append("gate") or {"status": "PASS"}), \
         patch("tools.generate_metadata.run",
               side_effect=lambda *a: (call_order.append("metadata"),
                                       _write_metadata(project_root, "20260524-test-job",
                                                        sample_metadata),
                                       sample_metadata)[2]), \
         patch("tools.upload_youtube.run",
               side_effect=lambda *a: (call_order.append("upload"),
                                       {"video_id": "vid123",
                                        "url": "https://youtube.com/shorts/vid123"})[1]), \
         patch("tools.monitor_upload.run",
               side_effect=lambda *a: call_order.append("monitor")):
        publish.main(project_root)

    assert call_order == ["gate", "metadata", "upload", "monitor"]


# ── Analytics mode ────────────────────────────────────────────────────────────

def test_analytics_flag_calls_pull_analytics(project_root, monkeypatch, config):
    _write_state(project_root, "test-job", {
        "job_id": "test-job",
        "video_id": "vid456",
        "completed_steps": ["pre_upload_gate", "generate_metadata", "upload_youtube",
                            "monitor_upload"],
    })
    publish = _reload_publish(project_root)
    monkeypatch.setattr(sys, "argv", ["publish.py", "--job", "test-job", "--analytics"])

    mock_pull = MagicMock(return_value={
        "flag": "GREEN", "us_share": 0.62, "notes": "US share >50% — target met"
    })

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.pull_analytics.run", mock_pull):
        publish.main(project_root)

    mock_pull.assert_called_once_with("test-job", "vid456", project_root)


def test_analytics_without_video_id_exits(project_root, monkeypatch, config):
    _write_state(project_root, "test-job", {
        "job_id": "test-job",
        "completed_steps": [],
    })
    publish = _reload_publish(project_root)
    monkeypatch.setattr(sys, "argv", ["publish.py", "--job", "test-job", "--analytics"])

    with patch("tools.utils.config.load_config", return_value=config), \
         pytest.raises(SystemExit) as exc_info:
        publish.main(project_root)

    assert exc_info.value.code == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_publish.py -v`

Expected: 9 failures (publish module not found).

- [ ] **Step 3: Implement publish.py**

Create `publish.py` in the project root:

```python
#!/usr/bin/env python3
"""
Post-edit pipeline orchestrator.

Usage:
  python publish.py --job <id>              run full post-edit pipeline
  python publish.py --job <id> --dry-run    generate metadata, print preview, skip upload
  python publish.py --job <id> --immediate  skip upload window check
  python publish.py --job <id> --analytics  pull 72h audience analytics for uploaded video
"""
import argparse
import json
import sys
from pathlib import Path

import os as _os
PROJECT_ROOT = Path(_os.environ["PUBLISH_PROJECT_ROOT"]) if "PUBLISH_PROJECT_ROOT" in _os.environ else Path(__file__).parent


def main(project_root: Path | None = None) -> None:
    import publish as _self_module
    if project_root is None:
        project_root = _self_module.PROJECT_ROOT

    parser = argparse.ArgumentParser(description="YT Shorts post-edit pipeline")
    parser.add_argument("--job", required=True, help="Job ID to publish")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate metadata, print preview, skip upload")
    parser.add_argument("--immediate", action="store_true",
                        help="Skip upload window check")
    parser.add_argument("--analytics", action="store_true",
                        help="Pull 72h audience analytics for an uploaded video")
    args = parser.parse_args()

    job_id = args.job
    sys.path.insert(0, str(project_root))

    from tools.utils.config import load_config
    from tools.utils.state import load_state, save_state, mark_complete, is_complete
    import tools.pre_upload_gate as pre_upload_gate
    import tools.generate_metadata as generate_metadata
    import tools.upload_youtube as upload_youtube
    import tools.monitor_upload as monitor_upload
    import tools.pull_analytics as pull_analytics

    config = load_config()

    # -- analytics mode -------------------------------------------------------
    if args.analytics:
        state = load_state(job_id, project_root)
        video_id = state.get("video_id")
        if not video_id:
            print(f"No video_id in state for job {job_id}. Run without --analytics first.")
            sys.exit(1)
        print("Pulling audience analytics...")
        report = pull_analytics.run(job_id, video_id, project_root)
        flag = report["flag"]
        us_pct = round(report["us_share"] * 100, 1)
        print(f"\nAudience Report [{flag}] — US share: {us_pct}%")
        print(f"  {report['notes']}")
        print(f"  Full report: compliance-logs/{job_id}/audience-report.json")
        return

    # -- prerequisite ---------------------------------------------------------
    final_video = project_root / "output" / job_id / "final.mp4"
    if not final_video.exists():
        print(f"final.mp4 not found: output/{job_id}/final.mp4")
        print("Export the edited video from CapCut, save to that path, then re-run.")
        sys.exit(1)

    state = load_state(job_id, project_root)
    if not state:
        state = {"job_id": job_id, "completed_steps": []}
        save_state(state, project_root)

    # -- Step 1: pre_upload_gate ----------------------------------------------
    if not is_complete("pre_upload_gate", state):
        print("Pre-upload compliance gate...")
        result = pre_upload_gate.run()
        if result["status"] != "PASS":
            failed = result.get("failed_checks", [])
            print(f"\nGate failed ({len(failed)} check(s) did not pass). Upload aborted.")
            sys.exit(1)
        state = mark_complete("pre_upload_gate", state, project_root)
    else:
        print("Gate: already passed")

    # -- Step 2: generate_metadata --------------------------------------------
    if not is_complete("generate_metadata", state):
        print("Generating metadata...")
        generate_metadata.run(job_id, config, project_root)
        state = mark_complete("generate_metadata", state, project_root)
    else:
        print("Metadata: already done")

    metadata_path = project_root / "metadata" / job_id / "metadata.json"
    try:
        metadata = json.loads(metadata_path.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Could not read metadata.json: {e}")
        sys.exit(1)

    if args.dry_run:
        print("\n[DRY RUN] Metadata preview:")
        print(json.dumps(metadata, indent=2))
        return

    # -- upload window check --------------------------------------------------
    if not args.immediate:
        if not upload_youtube.is_in_upload_window():
            nw = upload_youtube.next_upload_window()
            print(f"\nOutside optimal upload window.")
            print(f"  Next window: {nw.strftime('%A %b %d at %I:%M %p EST')}")
            print(f"  Re-run then:  python publish.py --job {job_id}")
            print(f"  Or skip:      python publish.py --job {job_id} --immediate")
            sys.exit(0)

    # -- Step 3: upload_youtube -----------------------------------------------
    if not is_complete("upload_youtube", state):
        print("Uploading to YouTube...")
        result = upload_youtube.run(job_id, final_video, metadata, project_root)
        state["video_id"] = result["video_id"]
        state["video_url"] = result["url"]
        save_state(state, project_root)
        state = mark_complete("upload_youtube", state, project_root)
    else:
        print("Upload: already done")

    # -- Step 4: monitor_upload -----------------------------------------------
    if not is_complete("monitor_upload", state):
        monitor_upload.run(job_id, state["video_id"], metadata["title"], project_root)
        state = mark_complete("monitor_upload", state, project_root)
    else:
        print(f"Monitoring card: youtube.com/shorts/{state.get('video_id', 'unknown')}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_publish.py -v`

Expected: 9 passed.

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -v`

Expected: all tests pass (65 from Plan A + ~34 new = ~99 total).

- [ ] **Step 6: Commit**

```bash
git add publish.py tests/test_publish.py
git commit -m "feat: publish.py orchestrator — post-edit pipeline with gate, metadata, upload, monitoring"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| `publish.py --job <id>` entry point | Task 6 |
| `--dry-run` flag | Task 6 |
| `pre_upload_gate.py` halts on any failure | Task 2 |
| `generate_metadata.py` → Claude API | Task 3 |
| `upload_youtube.py` → YouTube Data API v3 | Task 4 |
| `categoryId: 19`, `selfDeclaredAiGeneratedContent: true`, `madeForKids: false` | Task 4 |
| AI disclosure + pinned comment | Task 4 |
| `monitor_upload.py` prints monitoring card | Task 5 |
| Memory constraint: human sign-off 5 checkboxes | Task 2 |
| Memory constraint: `next_window` default, `--immediate` override | Tasks 4 + 6 |
| Memory constraint: 72h analytics pull → `audience-report.json` | Tasks 5 (pull_analytics) + 6 (--analytics flag) |
| Memory constraint: GREEN/YELLOW/RED US share flags | Task 5 |
| Google OAuth: `credentials.json` + `token.json` | Task 1 (youtube_auth) |
| Checkpoint / resume on failure | Task 6 |

All requirements covered. No gaps found.

**Placeholder scan:** No TBDs, no "add appropriate error handling", no "similar to Task N". All code blocks are complete.

**Type consistency check:** `run()` signatures consistent throughout:
- `pre_upload_gate.run()` → `dict`
- `generate_metadata.run(job_id, config, project_root)` → `dict`
- `upload_youtube.run(job_id, video_path, metadata, project_root)` → `dict`
- `monitor_upload.run(job_id, video_id, title, project_root)` → `None`
- `pull_analytics.run(job_id, video_id, project_root)` → `dict`

All `project_root` args are `Path` objects passed consistently. `get_youtube_client`/`get_analytics_client` imported from `tools.utils.youtube_auth` in all tools that use them.
