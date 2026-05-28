# Platform Redesign — Design Spec
**Date:** 2026-05-28
**Status:** Approved

## Overview

Redesign the repo from a WAT (Workflows/Agents/Tools) script-runner into a proper web platform with a FastAPI backend and a React frontend. The platform is not YT Shorts-only — it hosts multiple automation features under a shared shell. YT Shorts is the first feature.

**Goals:**
- Every pipeline function has its own independently callable REST endpoint
- Approval/regeneration loops work per-item without restarting the pipeline
- Adding a new feature means adding a folder, not restructuring the app
- TypeScript types on the frontend are derived from the same Pydantic models as the backend

---

## Architecture

Three layers:

```
┌─────────────────────────────────────────┐
│  Frontend — React + MUI + Vite + TS     │
│  core/: AppShell, JobsPanel, api client │
│  features/yt-shorts/: pages + api       │
│  features/<next>/: future feature       │
└──────────────────┬──────────────────────┘
                   │ HTTP / SSE
┌──────────────────┴──────────────────────┐
│  Backend — FastAPI + Python             │
│  features/yt_shorts/: routers+services  │
│  features/<next>/: future feature       │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────┴──────────────────────┐
│  Shared Core                            │
│  core/: jobs, store, notifications,     │
│         settings                        │
└─────────────────────────────────────────┘
```

**Key decisions:**
- Project-scoped REST: all YT Shorts endpoints nested under `/api/yt-shorts/projects/{id}/`
- Per-item approval + commit for multi-clip steps (footage, AI footage)
- Tools directory eliminated — logic migrates into `backend/features/yt_shorts/services/`
- Project state stored as JSON on disk at `.tmp/projects/{id}/state.json`

---

## Directory Structure

### Backend

```
backend/
├── main.py                        # FastAPI app init, CORS, router registration
├── config.py                      # Pydantic Settings, loads from .env
├── requirements.txt
├── core/
│   ├── jobs.py                    # Background job tracking (status, progress, errors)
│   ├── store.py                   # Project state read/write (.tmp/projects/{id}/)
│   ├── notifications.py           # SSE event broadcast (step complete, errors)
│   └── models.py                  # Shared base Pydantic models (JobStatus, etc.)
├── features/
│   └── yt_shorts/
│       ├── router.py              # Registers all sub-routers under /api/yt-shorts
│       ├── routers/               # Thin HTTP handlers — validate, call service, return
│       │   ├── projects.py
│       │   ├── topics.py
│       │   ├── script.py
│       │   ├── voiceover.py
│       │   ├── footage.py
│       │   ├── music.py
│       │   ├── assets.py
│       │   ├── gate.py
│       │   ├── metadata.py
│       │   ├── publish.py
│       │   ├── monitor.py
│       │   └── analytics.py
│       ├── services/              # Business logic (migrated from tools/)
│       │   ├── topics.py          # ← generate_topics.py
│       │   ├── script.py          # ← generate_script.py
│       │   ├── compliance.py      # ← check_compliance.py
│       │   ├── voiceover.py       # ← generate_voiceover.py
│       │   ├── footage_search.py  # ← search_footage.py + check_footage_gaps.py
│       │   ├── footage_ai.py      # ← generate_ai_footage.py + clear_footage.py
│       │   ├── music.py           # ← select_music.py
│       │   ├── assets.py          # ← package_assets.py
│       │   ├── gate.py            # ← pre_upload_gate.py
│       │   ├── metadata.py        # ← generate_metadata.py
│       │   ├── publish.py         # ← upload_youtube.py
│       │   ├── monitor.py         # ← monitor_upload.py
│       │   └── analytics.py       # ← pull_analytics.py
│       └── models/                # Pydantic request/response schemas
│           ├── project.py
│           ├── topic.py
│           ├── script.py
│           ├── voiceover.py
│           ├── footage.py
│           ├── music.py
│           ├── assets.py
│           ├── gate.py
│           ├── metadata.py
│           ├── publish.py
│           ├── monitor.py
│           └── analytics.py
└── tests/
    └── features/
        └── yt_shorts/
```

### Frontend

```
frontend/src/
├── core/
│   ├── AppShell.tsx               # Sidebar, feature switcher, layout wrapper
│   ├── JobsPanel.tsx              # Live status of background jobs across features
│   ├── ProjectContext.tsx         # Active project_id in React context
│   └── api/
│       └── client.ts              # Base typed fetch client, error handling, SSE helpers
├── features/
│   └── yt-shorts/
│       ├── pages/
│       │   ├── ProjectsPage.tsx   # List + create projects
│       │   ├── TopicsPage.tsx     # Generate + approve topic
│       │   ├── ScriptPage.tsx     # Generate, compliance check, approve script
│       │   ├── VoiceoverPage.tsx  # Generate + approve voiceover
│       │   ├── FootagePage.tsx    # Stock search, gap check, per-clip approve, commit
│       │   ├── AiFootagePage.tsx  # AI generation, per-clip approve/regenerate, commit
│       │   ├── MusicPage.tsx      # Select + approve background track
│       │   ├── AssetsPage.tsx     # Package + download editor folder
│       │   ├── GatePage.tsx       # Pre-upload checklist + human sign-off
│       │   ├── MetadataPage.tsx   # Generate + approve title/description/tags
│       │   ├── PublishPage.tsx    # Upload with SSE progress stream
│       │   ├── MonitorPage.tsx    # Copyright + monetization status
│       │   └── AnalyticsPage.tsx  # Views, watch time, geo breakdown
│       ├── components/            # Shared YT Shorts UI components
│       └── api/
│           └── yt-shorts.ts       # Typed API client for all YT Shorts endpoints
└── App.tsx
```

---

## Project State Model

Each video in progress is a **Project**. State persists at `.tmp/projects/{id}/state.json`.

```python
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

class Project(BaseModel):
    id: str
    title: str
    current_step: ProjectStep
    created_at: datetime
    updated_at: datetime
    # Step outputs appended as project advances
    approved_topic: Topic | None
    script_draft: Script | None
    compliance_report: ComplianceReport | None
    voiceover: Voiceover | None
    footage_clips: list[FootageClip]      # each has: sentence_id, source, status
    ai_clips: list[AiClip]               # each has: sentence_id, provider, status
    selected_track: MusicTrack | None
    assets_path: str | None
    gate_result: GateResult | None
    metadata: Metadata | None
    youtube_video_id: str | None
```

### Footage Sentence State

Each script sentence tracks its own coverage:

```python
class FootageClip(BaseModel):
    id: str
    sentence_id: str
    sentence_text: str
    source: Literal["pexels", "pixabay", "ai"]
    url: str
    status: Literal["pending", "approved", "rejected"]

# Gap = sentence where no clip has status "approved"
# AI generate reads project.footage_clips, finds gaps automatically
```

---

## API Endpoint Map

All YT Shorts endpoints are prefixed `/api/yt-shorts/`.

### Project Management

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects` | Create project, returns `project_id` |
| GET | `/projects` | List all projects |
| GET | `/projects/{id}` | Full project state |

### Step 1 — Topics

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects/{id}/topics/generate` | Generate 10 ideas (re-call to regenerate) |
| GET | `/projects/{id}/topics` | List generated topics |
| POST | `/projects/{id}/topics/{topic_id}/approve` | Select topic, advance to script |

### Step 2 — Script

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects/{id}/script/generate` | Generate script (re-call to regenerate) |
| GET | `/projects/{id}/script` | Get current draft |
| POST | `/projects/{id}/script/compliance` | Run compliance check |
| POST | `/projects/{id}/script/approve` | Approve, advance to voiceover |

### Step 3 — Voiceover

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects/{id}/voiceover/generate` | Generate via ElevenLabs (re-call to regenerate) |
| GET | `/projects/{id}/voiceover` | Status + audio file path |
| POST | `/projects/{id}/voiceover/approve` | Approve, advance to footage search |

### Step 4 — Stock Footage

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects/{id}/footage/search` | Search Pexels + Pixabay per sentence |
| GET | `/projects/{id}/footage` | All clips with approve/reject status |
| GET | `/projects/{id}/footage/gaps` | Sentences with no approved clip (preview) |
| POST | `/projects/{id}/footage/{clip_id}/approve` | Approve individual clip |
| POST | `/projects/{id}/footage/{clip_id}/reject` | Reject, triggers new search for that sentence |
| POST | `/projects/{id}/footage/commit` | Lock approved clips, advance to AI footage |

### Step 5 — AI Footage

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects/{id}/footage/ai/generate` | Auto-targets gap sentences from project state |
| GET | `/projects/{id}/footage/ai` | AI clips with status |
| POST | `/projects/{id}/footage/ai/{clip_id}/approve` | Approve individual AI clip |
| POST | `/projects/{id}/footage/ai/{clip_id}/regenerate` | Regenerate just this clip |
| POST | `/projects/{id}/footage/ai/commit` | Lock approved AI clips, advance to music |

### Step 6 — Music

| Method | Path | Description |
|--------|------|-------------|
| GET | `/projects/{id}/music/options` | Available background tracks |
| POST | `/projects/{id}/music/{track_id}/approve` | Select track, advance to assets |

### Step 7 — Package Assets

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects/{id}/assets/package` | Bundle clips + voiceover + music |
| GET | `/projects/{id}/assets` | Package status + output path |

### Step 8 — Pre-Upload Gate *(after manual edit)*

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects/{id}/gate/check` | Run compliance checklist |
| GET | `/projects/{id}/gate` | Gate status — passed/failed items |
| POST | `/projects/{id}/gate/approve` | Human sign-off, unlocks metadata + upload |

### Step 9 — Metadata

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects/{id}/metadata/generate` | Generate title, description, tags (re-call to regenerate) |
| GET | `/projects/{id}/metadata` | Current draft |
| POST | `/projects/{id}/metadata/approve` | Approve, unlock upload |

### Step 10 — Publish

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects/{id}/publish/upload` | Upload to YouTube Data API v3 |
| SSE | `/projects/{id}/publish/stream` | Live upload progress events |
| GET | `/projects/{id}/publish` | Upload status + `youtube_video_id` on success |

### Step 11 — Monitor

| Method | Path | Description |
|--------|------|-------------|
| GET | `/projects/{id}/monitor` | Copyright (24h) + monetization (48h) status |
| POST | `/projects/{id}/monitor/refresh` | Force re-check |

### Step 12 — Analytics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/projects/{id}/analytics` | Views, watch time, US% share, geo breakdown |
| POST | `/projects/{id}/analytics/refresh` | Pull latest from YouTube Analytics API |

### Shared Core (`/api/core/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/core/jobs` | All running/completed background jobs |
| SSE | `/core/jobs/{job_id}/stream` | Live log stream for a job |
| SSE | `/core/events` | Global event feed — step complete, approvals needed, errors |

---

## Approval Patterns

**Single-item approve** (topics, script, voiceover, music, gate, metadata):
- Call `POST .../approve` once the item looks good
- Re-call the generate endpoint to replace the draft; approval resets

**Per-item + commit** (stock footage, AI footage):
- Approve or reject each clip individually
- Call `POST .../commit` when the whole set is ready — pipeline advances only then
- Rejected clips trigger a new search/generate for that sentence only
- Commit is only allowed when every sentence has at least one approved clip

---

## Shared Core — Jobs

Long-running operations (AI generation, upload, voiceover synthesis) run as background jobs tracked in `core/jobs.py`. Each job has:

```python
class Job(BaseModel):
    id: str
    feature: str          # "yt_shorts"
    project_id: str
    step: str             # "footage_ai", "voiceover", etc.
    status: Literal["queued", "running", "complete", "failed"]
    progress: int         # 0–100
    log: list[str]        # append-only event log
    created_at: datetime
    updated_at: datetime
```

The frontend `JobsPanel` subscribes to `/api/core/events` SSE and shows live status across all features.

---

## Migration from Existing Backend

The existing `backend/` structure (flat routers + services) is replaced entirely by the feature-module layout. Existing files are deleted, not refactored in place:

| Old file | Disposition |
|----------|-------------|
| `backend/routers/topics.py` | Replaced by `features/yt_shorts/routers/topics.py` |
| `backend/routers/pipeline.py` | Split into per-step routers in `features/yt_shorts/routers/` |
| `backend/routers/publish.py` | Replaced by `features/yt_shorts/routers/publish.py` |
| `backend/routers/analytics.py` | Replaced by `features/yt_shorts/routers/analytics.py` |
| `backend/services/filesystem.py` | Logic absorbed into `core/store.py` |
| `backend/services/subprocess_runner.py` | Deleted — no subprocess calls in new design |
| `backend/tests/` | Recreated under `backend/tests/features/yt_shorts/` |

---

## Migration from tools/

| Old script | New location |
|------------|-------------|
| `tools/generate_topics.py` | `features/yt_shorts/services/topics.py` |
| `tools/generate_script.py` | `features/yt_shorts/services/script.py` |
| `tools/check_compliance.py` | `features/yt_shorts/services/compliance.py` |
| `tools/generate_voiceover.py` | `features/yt_shorts/services/voiceover.py` |
| `tools/search_footage.py` | `features/yt_shorts/services/footage_search.py` |
| `tools/check_footage_gaps.py` | `features/yt_shorts/services/footage_search.py` |
| `tools/generate_ai_footage.py` | `features/yt_shorts/services/footage_ai.py` |
| `tools/clear_footage.py` | `features/yt_shorts/services/footage_ai.py` |
| `tools/select_music.py` | `features/yt_shorts/services/music.py` |
| `tools/package_assets.py` | `features/yt_shorts/services/assets.py` |
| `tools/pre_upload_gate.py` | `features/yt_shorts/services/gate.py` |
| `tools/generate_metadata.py` | `features/yt_shorts/services/metadata.py` |
| `tools/upload_youtube.py` | `features/yt_shorts/services/publish.py` |
| `tools/monitor_upload.py` | `features/yt_shorts/services/monitor.py` |
| `tools/pull_analytics.py` | `features/yt_shorts/services/analytics.py` |

`tools/` directory is deleted after migration. `backend/services/subprocess_runner.py` is also deleted — no subprocess calls.

---

## Best Practices

- Backend follows `fastapi-best-practices.md` — thin routers, service layer, Pydantic models throughout, no raw dicts in responses
- Frontend follows `react-mui-vite-ts-best-practices.md` — typed API clients, no `any`, MUI theming, shared utilities in `core/`
- All Pydantic response models use `model_config = ConfigDict(from_attributes=True)` for TS compatibility
- SSE streams use `text/event-stream` with `data: {json}\n\n` format
