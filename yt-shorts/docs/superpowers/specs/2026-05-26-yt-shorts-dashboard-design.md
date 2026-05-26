# YT Shorts Dashboard — Design Spec

**Date:** 2026-05-26  
**Status:** Approved  
**Stack:** React 18 + TypeScript + Vite + MUI v5 (frontend) · FastAPI (backend)

---

## 1. Overview

A local web dashboard that replaces CLI interactions for the YT Shorts automation pipeline. Targets one user (JM) running on localhost. No auth, no database — the backend reads and writes the same local filesystem that `pipeline.py` and `publish.py` use.

**Goals:**
- Approve/reject generated topics without touching JSON files
- Watch pipeline progress in real time (step tracker + live log stream)
- Complete the pre-upload checklist and trigger YouTube upload from the browser
- Pull and view 72h audience analytics per video

**Out of scope:** multi-user, remote deployment, video editing, CapCut integration.

---

## 2. Architecture

```
Browser (React)
    ↕ REST + SSE
FastAPI (localhost:8000)
    ↕ subprocess / filesystem
pipeline.py · publish.py · tools/
    ↕ filesystem
topics/ · .tmp/ · output/ · metadata/ · compliance-logs/
```

**Frontend** (`frontend/`) — Vite dev server on port 5173. Proxies `/api` to FastAPI.

**Backend** (`backend/`) — FastAPI on port 8000. Wraps subprocess calls to `pipeline.py` / `publish.py` and exposes the local filesystem as JSON. Uses `asyncio.create_subprocess_exec` for non-blocking subprocess execution. SSE via `StreamingResponse`.

No ORM, no Redis, no message queue. State lives in `.tmp/<job-id>/state.json` (existing pipeline format).

---

## 3. Frontend Structure

```
frontend/
  src/
    api/            # Axios client + typed request functions
    components/     # Shared UI: StatusBadge, LogPanel, StepTracker, TopicCard
    hooks/          # useSSE, useJobState, usePipelineStatus
    layouts/        # AppShell (sidebar + topbar), PrivateLayout
    pages/          # Topics, Pipeline, Publish, Analytics
    router/         # React Router v6 config
    store/          # Context providers (PipelineContext, PublishContext)
    theme/          # MUI theme (dark, #4f79ff primary)
    types/          # Shared TypeScript interfaces
    utils/          # formatters, constants
  index.html
  vite.config.ts    # proxy /api → localhost:8000
  tsconfig.json
```

**Key conventions (from best-practices guide):**
- MUI path imports: `import Button from '@mui/material/Button'`
- Strict TypeScript (`strict: true`)
- Zod for env validation (`VITE_API_URL`)
- Context API for shared state (no Redux)
- `useSSE` hook wraps `EventSource`, handles reconnect, cleanup on unmount

---

## 4. Backend Structure

```
backend/
  main.py           # FastAPI app, CORS, router registration
  config.py         # Pydantic BaseSettings (PROJECT_ROOT, PORT)
  routers/
    topics.py       # /api/v1/topics/*
    pipeline.py     # /api/v1/pipeline/*
    publish.py      # /api/v1/publish/*
    analytics.py    # /api/v1/analytics/*
  services/
    subprocess_runner.py   # async subprocess wrapper + SSE generator
    filesystem.py          # read/write helpers for local JSON files
```

All routes versioned at `/api/v1/`. `config.py` reads `PROJECT_ROOT` (defaults to `../` relative to `backend/`).

---

## 5. Pages

### 5.1 Topics

**Purpose:** Review generated topics, approve or reject each, view the approved queue.

**Layout:** Two-column. Left: pending approval list. Right: approved queue (ordered).

**Interactions:**
- **Generate Topics** button → `POST /api/v1/topics/generate` → runs `pipeline.py --topics-only` as subprocess → polls until complete → refreshes pending list
- Each topic card shows: title, score (ring), tier badge (Tier 1 green / Tier 2 amber), hook object
- **Approve** → `POST /api/v1/topics/{topic_id}/approve` → moves topic from `topics/pending.json` to `topics/queue.json`
- **Reject** → `POST /api/v1/topics/{topic_id}/reject` → removes from `topics/pending.json`
- **View Published** button → navigates to a read-only list of `topics/published.json`

**Topic file format (new `topics/pending.json`):**
```json
[{"id": "uuid4", "title": "...", "score": 9, "tier": 1, "hook": "AK-47 rifle"}]
```
The backend's generate handler writes scored topics to `pending.json` instead of directly appending to `queue.json`. The approve action moves them to `queue.json`.

### 5.2 Pipeline

**Purpose:** Run the pre-edit pipeline for the next queued topic; watch it progress live.

**Layout:** Two rows. Top: job selector + run button. Bottom: step tracker (left) + live log panel (right).

**Interactions:**
- **Run Pipeline** button → `POST /api/v1/pipeline/run` → spawns `pipeline.py` subprocess for front-of-queue topic → returns `job_id`
- Step tracker polls `GET /api/v1/pipeline/{job_id}/state` every 3s → reads `state.json` → shows 6 steps (Script, Voiceover, Search Footage, AI Footage, Check Gaps, Package Assets) as pending / running / done
- Log panel subscribes to `GET /api/v1/pipeline/{job_id}/stream` (SSE) → FastAPI pipes subprocess stdout line-by-line → auto-scrolls
- Job selector shows current or most recent job; past jobs selectable from dropdown
- If pipeline already running, Run button is disabled (one job at a time)
- If user navigates away while the pipeline is running, the SSE connection closes but the subprocess continues running unattended — this is expected behavior. Returning to the Pipeline page reconnects to the stream.

**Step mapping** (from `state.json` `completed_steps` array):

| Step # | Display name | `state.json` key |
|--------|-------------|-----------------|
| 1 | Generate Script | `generate_script` |
| 2 | Generate Voiceover | `generate_voiceover` |
| 3 | Search Footage | `search_footage` |
| 4 | Generate AI Footage | `generate_ai_footage` |
| 5 | Check Footage Gaps | `check_footage_gaps` |
| 6 | Package Assets | `package_assets` |

### 5.3 Publish

**Purpose:** Complete the pre-upload checklist and push the edited video to YouTube.

**Layout:** Two-column. Left: checklist + window banner + upload button. Right: metadata preview.

**Prerequisite:** `output/{job_id}/final.mp4` must exist (user saved edited video from CapCut). Backend checks this and shows a warning if missing.

**Interactions:**
- Job selector (completed pipeline jobs with `final.mp4`) at the top
- Checklist: 5 MUI Checkbox items (client-side state only — no API call per check)
  1. Video plays start to finish without issues
  2. Hook lands in the first 3 seconds
  3. Captions are readable and accurate
  4. No copyrighted music or footage
  5. Loop is seamless (first = last clip)
- Upload window banner: green ("In window") or amber ("Next window: Thu 7 AM EST") — driven by `GET /api/v1/publish/window`
- **Upload to YouTube** button: disabled until all 5 boxes checked; clicking calls `POST /api/v1/publish/{job_id}/upload`
  - Backend first writes the gate as complete in `state.json` using `mark_complete("pre_upload_gate", state)` — so `publish.py` sees the gate as already passed and skips its interactive CLI prompt
  - Backend then runs `publish.py --job {job_id} --immediate` as subprocess
  - SSE stream shows upload progress
  - On success, displays video URL
- **Dry Run** button in topbar → `POST /api/v1/publish/{job_id}/upload?dry_run=true` → shows metadata JSON preview without uploading
- Metadata preview: reads `metadata/{job_id}/metadata.json` → displays title, description, tags, pinned comment

### 5.4 Analytics

**Purpose:** View the 72h US audience share report for an uploaded video.

**Layout:** Top row: flag card (US %, GREEN/YELLOW/RED) + meta card (video ID, upload time, monetization). Bottom: country breakdown table with bar chart.

**Interactions:**
- Job selector: jobs with `video_id` in state
- **Pull Latest** button → `POST /api/v1/analytics/{job_id}/pull` → runs `publish.py --job {job_id} --analytics` as subprocess → refreshes report
- Report data from `GET /api/v1/analytics/{job_id}` → reads `compliance-logs/{job_id}/audience-report.json`
- Flag colors: GREEN (`us_share ≥ 0.50`), YELLOW (`0.40–0.49`), RED (`< 0.40`)

---

## 6. API Endpoints

### Topics
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/topics/pending` | List pending topics from `topics/pending.json` |
| GET | `/api/v1/topics/queue` | List approved queue from `topics/queue.json` |
| GET | `/api/v1/topics/published` | List published from `topics/published.json` |
| POST | `/api/v1/topics/generate` | Run `pipeline.py --topics-only`, write to `pending.json` |
| POST | `/api/v1/topics/{topic_id}/approve` | Move topic to `queue.json` |
| POST | `/api/v1/topics/{topic_id}/reject` | Remove from `pending.json` |

### Pipeline
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/pipeline/jobs` | List job IDs + status from `.tmp/` dirs |
| GET | `/api/v1/pipeline/{job_id}/state` | Read `.tmp/{job_id}/state.json` |
| POST | `/api/v1/pipeline/run` | Start `pipeline.py` for next queued topic |
| GET | `/api/v1/pipeline/{job_id}/stream` | SSE: pipe subprocess stdout line-by-line |

### Publish
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/publish/window` | Check upload window; return `{in_window, next_window}` |
| GET | `/api/v1/publish/{job_id}/metadata` | Read `metadata/{job_id}/metadata.json` |
| POST | `/api/v1/publish/{job_id}/upload` | Run `publish.py --job {job_id} [--immediate] [--dry-run]` |
| GET | `/api/v1/publish/{job_id}/stream` | SSE: pipe upload subprocess stdout |

### Analytics
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/analytics/{job_id}` | Read `compliance-logs/{job_id}/audience-report.json` |
| POST | `/api/v1/analytics/{job_id}/pull` | Run `publish.py --job {job_id} --analytics` |

---

## 7. Real-Time (SSE)

FastAPI SSE pattern:
```python
async def event_generator(job_id: str):
    proc = await asyncio.create_subprocess_exec(
        "python", "pipeline.py", "--job", job_id,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    async for line in proc.stdout:
        yield f"data: {line.decode().rstrip()}\n\n"
    yield "data: [DONE]\n\n"

@router.get("/{job_id}/stream")
async def stream(job_id: str):
    return StreamingResponse(event_generator(job_id), media_type="text/event-stream")
```

React `useSSE` hook:
```ts
const useSSE = (url: string, onMessage: (line: string) => void) => {
  useEffect(() => {
    const es = new EventSource(url);
    es.onmessage = (e) => { if (e.data !== '[DONE]') onMessage(e.data); else es.close(); };
    es.onerror = () => es.close();
    return () => es.close();
  }, [url]);
};
```

Step state polling uses `setInterval(3000)` in `useJobState`, reading `/api/v1/pipeline/{job_id}/state`.

---

## 8. State Management

Context API — two providers:

**`PipelineContext`** — active `job_id`, running status, step completion map. Consumed by Pipeline page.

**`PublishContext`** — selected `job_id`, checklist state (5 booleans), upload status. Consumed by Publish page.

No global store. Topics and Analytics pages manage state locally with `useState` + `useEffect`.

---

## 9. MUI Theme

Dark mode. Primary: `#4f79ff`. Background: `#0d1117` (paper: `#1e2533`). Sidebar: `#1a1f2e`. Default font: Inter.

---

## 10. Topics Pending File (New)

The existing pipeline writes scored Tier 1+2 topics directly to `topics/queue.json`. The dashboard introduces `topics/pending.json` as a staging area so users can review before committing to the queue.

**Implementation:** Add `--staging` flag to `generate_topics.py`. When set, writes to `topics/pending.json` instead of `topics/queue.json`. The backend's generate handler calls `generate_topics.py --staging`.

The CLI workflow is unchanged — `pipeline.py --topics-only` still writes directly to `queue.json` as before. Only the web UI uses `--staging`.

---

## 11. Dev Setup

```bash
# Backend
cd backend
pip install fastapi uvicorn python-dotenv
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm create vite@latest . -- --template react-ts
npm install @mui/material @emotion/react @emotion/styled axios
npm run dev  # port 5173
```

`vite.config.ts` proxy:
```ts
server: { proxy: { '/api': 'http://localhost:8000' } }
```

---

## 12. Error Handling

- Subprocess fails → SSE sends `data: [ERROR] <message>\n\n` → frontend shows red alert
- `final.mp4` missing → Publish page shows inline warning, upload button hidden
- `pending.json` / `queue.json` missing → backend returns empty array (not 404)
- Upload window check: if outside window and `--immediate` not set, backend returns `{in_window: false, next_window: "..."}` → frontend shows amber banner, Upload button disabled
