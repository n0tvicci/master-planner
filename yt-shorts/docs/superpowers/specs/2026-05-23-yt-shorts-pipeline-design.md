# YT Shorts Automation Pipeline — Design Spec

**Date:** 2026-05-23
**Project:** `yt-shorts` — Automated Faceless Military & Historical Weapons Channel
**Architecture:** WAT (Workflows, Agents, Tools)

---

## Overview

A two-phase local automation pipeline that takes a topic from queue to published YouTube Short with ~17–25 minutes of active human work per video. All execution runs on-demand from the user's local machine — no scheduling, no cloud infrastructure.

**Phase 1 (`pipeline.py`):** Topic → Script → Voiceover → Footage → Packaged asset bundle ready for CapCut.

**Phase 2 (`publish.py`):** Exported video → Compliance gate → Metadata → YouTube upload → Monitoring card.

---

## Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Topic selection | Queue-based (local JSON) | Enforces 30-day diversity rule, no scrambling for topics daily |
| AI video generation | Gap report + manual Runway ML | No reliable Runway API; pre-written prompts make manual step fast |
| Pipeline architecture | WAT-native (12 tool scripts + 2 orchestrators) | Isolated tools = resume on failure, no duplicate API charges |
| Queue storage | `topics/queue.json` | Local-only, no auth overhead, run fully on-demand |
| Footage search | Pexels + Pixabay concurrent | Cuts footage step from ~5 min to ~1 min |
| Audio stripping | ffmpeg (automated) | Every clip cleaned before packaging, no manual step |

---

## Phase 1 — Pre-Edit Pipeline

**Entry point:** `python pipeline.py`

**Flags:**
- `--topics-only` — generate and queue topics without running production pipeline
- `--job <id>` — resume a specific job from its last checkpoint

### Steps

On start, `pipeline.py` checks `topics/queue.json` for the oldest entry with `status: "approved"` (FIFO). If none exists, it runs `generate_topics.py` automatically, prints the list, and exits with instructions to approve a topic before re-running.

| # | Tool Script | API | Output |
|---|---|---|---|
| — | **Auto-check queue on start. If no approved topic: runs `generate_topics.py`, exits. User sets status → `"approved"` and re-runs.** | | |
| 2 | `generate_script.py` | Claude API | `scripts/<job-id>/script.json` — full script, scores, footage queries, overlay keywords |
| 3 | `check_compliance.py` | none | PASS or halt with revision instructions (originality ≥7, advertiser-friendly ≥8) |
| 4 | `generate_voiceover.py` | ElevenLabs | `voiceover/<job-id>/voiceover.mp3` |
| 5 | `search_footage.py` | Pexels + Pixabay | `footage/<job-id>/` — clips downloaded concurrently per sentence |
| 6 | `clear_footage.py` | ffmpeg (local) | Audio stripped from every clip + `compliance-logs/<job-id>/clearance.json` |
| 7 | `check_footage_gaps.py` | none | `assets/<job-id>/footage-gaps.md` — Runway ML prompts for missing clips |
| — | **PAUSE (if gaps): user generates clips in Runway ML, drops into `footage/<job-id>/gaps/`, re-runs pipeline.py** | | |
| 8 | `package_assets.py` | none | Numbered asset bundle in `assets/<job-id>/` + edit checklist printed to terminal |

### Job ID format

`YYYYMMDD-<slug>` e.g. `20260523-snipers-never-use-lasers`

Generated at pipeline start from the date + first 4 words of the topic title.

### Checkpoint / resume

Each completed step writes its result to `.tmp/<job-id>/state.json`. On re-run, completed steps are skipped. This means a failed ElevenLabs call does not re-trigger Claude API calls.

---

## Phase 2 — Post-Edit Pipeline

**Entry point:** `python publish.py --job <job-id>`

**Prerequisite:** `output/<job-id>/final.mp4` must exist (exported from CapCut).

**Flags:**
- `--dry-run` — generates and prints metadata without uploading

### Steps

| # | Tool Script | API | Output |
|---|---|---|---|
| 1 | `pre_upload_gate.py` | none | Validates full compliance checklist — halts on any failure |
| 2 | `generate_metadata.py` | Claude API | `metadata/<job-id>/metadata.json` — title, description, tags, pinned comment |
| 3 | `upload_youtube.py` | YouTube Data API v3 | Live upload with AI disclosure enabled + pinned comment posted |
| 4 | `monitor_upload.py` | none | Prints monitoring reminder card to terminal |

### YouTube upload parameters

Matches `instruction.md` Section 11: `categoryId: 19`, `defaultLanguage: en`, `selfDeclaredAiGeneratedContent: true`, `madeForKids: false`.

### Monitoring reminder card

Printed after upload:
```
✅ Uploaded: <title>
   Video ID: <yt-id>
   URL: https://youtube.com/shorts/<yt-id>

24h  → Check for copyright claims
48h  → Confirm monetization status is green
72h  → Check country distribution (target: 50%+ US)
```

---

## Daily Routine

**Once per week (~5 min):**
```
python pipeline.py --topics-only
```
Open `topics/queue.json`, find topics you like, set status to `"approved"`. Builds a week's backlog so you're never blocked on topic selection.

**Per video (~17–25 min active):**

| Step | Action | Time |
|---|---|---|
| 1 | `python pipeline.py` | 1 min to start, ~5–8 min unattended |
| 2 | Fill Runway gaps (if any) | 0–5 min |
| 3 | Edit in CapCut | ~15 min |
| 4 | `python publish.py --job <id>` | ~2 min |

---

## File Structure

```
yt-shorts/
├── pipeline.py
├── publish.py
├── tools/
│   ├── generate_topics.py
│   ├── generate_script.py
│   ├── check_compliance.py
│   ├── generate_voiceover.py
│   ├── search_footage.py
│   ├── clear_footage.py
│   ├── check_footage_gaps.py
│   ├── package_assets.py
│   ├── pre_upload_gate.py
│   ├── generate_metadata.py
│   ├── upload_youtube.py
│   └── monitor_upload.py
├── workflows/
│   └── <one .md per tool script>
├── topics/
│   └── queue.json
├── scripts/<job-id>/script.json
├── voiceover/<job-id>/voiceover.mp3
├── footage/<job-id>/
│   ├── clip_01.mp4          ← audio-stripped stock
│   └── gaps/                ← drop Runway clips here
├── assets/<job-id>/
│   ├── 01_clip.mp4          ← numbered for CapCut order
│   ├── voiceover.mp3
│   ├── script.txt
│   ├── overlays.txt         ← keyword overlay list
│   └── footage-gaps.md      ← Runway ML prompts (empty = no gaps)
├── output/<job-id>/final.mp4
├── metadata/<job-id>/metadata.json
├── compliance-logs/<job-id>/clearance.json
├── .tmp/<job-id>/state.json
└── .env
```

---

## Environment Variables (`.env`)

```
ANTHROPIC_API_KEY=
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
PEXELS_API_KEY=
PIXABAY_API_KEY=
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
```

Google OAuth for YouTube: `credentials.json` + `token.json` in project root (gitignored). First upload run triggers browser OAuth flow.

---

## Improvements Over `instruction.md`

| Original | Improvement | Reason |
|---|---|---|
| Steps 1–14 in a single implied flow | Checkpoint state after each step | Resume without re-paying API costs |
| Manual audio stripping mentioned | ffmpeg automated in `clear_footage.py` | Removes a manual step entirely |
| Footage search sequential | Pexels + Pixabay concurrent per sentence | ~5× faster footage step |
| AI video generation as a pipeline step | Runway gap report (`footage-gaps.md`) with pre-written prompts | No public API; pre-written prompts make the manual step under 2 min |
| No topic buffer | Weekly `--topics-only` batch + queue approval | Never start a day without an approved topic ready |
| No dry-run mode | `publish.py --dry-run` | Preview metadata before committing to upload |
| No job tracking | Job ID system | All assets stay grouped; publish.py knows exactly what to upload |

---

## Out of Scope

- Thumbnail generation (manual or separate future pipeline)
- Analytics dashboard (use YouTube Studio directly per `instruction.md` Section 15)
- Multi-channel or batch-video runs (Phase 3 concern per the 30/60/90-day roadmap)
- Kling API integration (evaluate when public API is stable)
