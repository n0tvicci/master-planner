# YT Shorts Dashboard

Local web dashboard for the YouTube Shorts automation pipeline. Replaces CLI interactions with a browser UI for topic approval, pipeline monitoring, YouTube upload, and audience analytics.

---

## Prerequisites

- Python 3.13 + `.venv` set up (`pip install -r requirements.txt` and `pip install -r backend/requirements.txt`)
- Node.js 18+ (for the frontend)
- `.env` file with all API keys (copy `.env.example`)
- `credentials.json` from Google Cloud Console (for YouTube OAuth)

---

## Starting the App

Open two terminals from the project root (`yt-shorts/`).

**Terminal 1 — Backend (FastAPI)**
```bash
.venv\Scripts\activate
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend (Vite)**
```bash
cd frontend
npm install   # first time only
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Pages

### Topics

Manage the content queue before running the pipeline.

- **Generate Topics** — calls Claude to research and score new topics, stages them in `topics/pending.json`
- **Approve** — moves a topic to `topics/queue.json` (next pipeline run picks it up)
- **Reject** — removes it from the pending list

Approved topics appear in the queue column on the right, in FIFO order.

### Pipeline

Run the pre-edit pipeline for the next topic in the queue.

- **Run Pipeline** — executes `pipeline.py` against the first topic in `topics/queue.json`
- **Steps panel** — tracks the 6 pipeline steps in real time (reads from `.tmp/<job-id>/state.json`)
- **Live Log** — SSE stream of `pipeline.py` output while the job runs

The job ID (`job-YYYYMMDD-HHmmss`) is what you'll need for the Publish page after editing in CapCut.

### Publish

Upload an edited video to YouTube.

1. **Enter the Job ID** from the pipeline run
2. **Check all 5 items** in the pre-upload checklist (this is your sign-off gate)
3. The **Metadata Preview** panel shows the Claude-generated title, description, tags, and pinned comment
4. The **Upload Window** banner tells you if you're in an optimal EST posting window
5. Click **Upload to YouTube** — the upload runs in the background and the log streams below

Use **Dry Run** (top-right) to test the full publish flow without actually uploading.

> **Upload window:** The banner is advisory — clicking Upload always proceeds immediately regardless of the window. If you want to enforce the window, wait until the banner turns green before clicking.

> **Job ID auto-fill:** After running the pipeline, the job ID is automatically pre-filled on the Publish and Analytics pages.

### Analytics

View the 72-hour audience report after a video has been live.

1. **Enter the Job ID**
2. If a report exists it loads automatically — shows US audience share %, flag (GREEN ≥ 50% / YELLOW 30–49% / RED < 30%), and country breakdown bars
3. **Pull Latest** — triggers `pull_analytics` to fetch fresh data from YouTube, then polls until the report is ready (up to ~60 seconds)

---

## Daily Workflow

```
1. Topics page → Generate Topics → Approve 1–3 topics
2. Pipeline page → Run Pipeline → wait ~5–8 min
3. Edit in CapCut (~15 min) → export final.mp4 to output/<job-id>/final.mp4
4. Publish page → enter job ID → check all 5 items → Upload to YouTube
5. Analytics page → check report 72h after upload
```

---

## Backend API

Runs on `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

| Prefix | Description |
|---|---|
| `/api/v1/topics/` | Pending, queue, published lists; approve/reject/generate |
| `/api/v1/pipeline/` | Job list, state, run, SSE log stream |
| `/api/v1/publish/` | Upload window, metadata, upload trigger, SSE stream |
| `/api/v1/analytics/` | Audience report, pull latest |

---

## File Locations

| What | Where |
|---|---|
| Pending topics | `topics/pending.json` |
| Approved queue | `topics/queue.json` |
| Published log | `topics/published.json` |
| Pipeline job state | `.tmp/<job-id>/state.json` |
| Pipeline log | `.tmp/<job-id>/pipeline.log` |
| Edited video | `output/<job-id>/final.mp4` |
| Upload metadata | `metadata/<job-id>/metadata.json` |
| Audience report | `compliance-logs/<job-id>/audience-report.json` |
