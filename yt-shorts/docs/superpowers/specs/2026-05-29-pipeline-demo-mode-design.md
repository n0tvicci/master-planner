# Pipeline Demo Mode Design

**Date:** 2026-05-29
**Scope:** Add a frontend-only demo mode to PipelinePage that simulates a full pipeline run with fake data — no backend or API keys required.

---

## Concept

A "Demo" button on the Pipeline page triggers a simulated run entirely in the browser. Steps advance automatically every ~5 seconds, fake log lines stream in at ~1 per second per step, and the UI completes all 6 steps in ~30 seconds. The exact same `StepTracker` and `LogPanel` components are used, so the demo shows precisely what a real run looks like. No backend calls are made.

---

## Files Changed

| File | Change |
|---|---|
| `frontend/src/hooks/useDemoMode.ts` | **Create** — hook that owns all demo simulation state |
| `frontend/src/pages/PipelinePage.tsx` | **Modify** — add Demo button, banner, and hook integration |

---

## `useDemoMode` Hook

**Signature:**
```ts
function useDemoMode(): {
  isDemoRunning: boolean
  demoJobId: string | null
  demoCompletedSteps: string[]
  demoLogLines: string[]
  startDemo: () => void
  stopDemo: () => void
}
```

**Behaviour:**

- `startDemo()`:
  1. Generates `demoJobId` = `"job-demo-" + Date.now()` (e.g. `job-demo-1748527200000`)
  2. Sets `isDemoRunning = true`
  3. Starts the step progression loop: every 5000ms, adds the next step key to `demoCompletedSteps`
  4. Starts the log line loop: every 900ms, appends the next pre-scripted log line to `demoLogLines`
  5. When the log delivery loop reaches the last line (index === LOG_LINES.length - 1), it clears both intervals and sets `isDemoRunning = false`. This is the single completion trigger — it fires after all log lines are delivered (~50s), which is always after all steps complete (~30s).

- `stopDemo()`: clears all intervals, resets all state to initial values

- On unmount: clears all intervals/timeouts (cleanup function in `useEffect`)

**Step progression order** (one every 5000ms):
```
generate_script → generate_voiceover → search_footage →
generate_ai_footage → check_footage_gaps → package_assets
```

**Pre-scripted log lines** (cycled in order, ~8–10 lines per step, delivered at 900ms intervals):

```
Step 1 — Generate Script:
  → Generating script for: "Why snipers never aim for center mass"
  → Calling Claude API (claude-sonnet-4-6)...
  ✓ Script generated (178 words, 4 sentences)
  ✓ Word count validated (178 — within 168–183 target)
  → Running compliance check...
  ✓ Originality score: 8/10 (PASS)
  ✓ Advertiser-friendliness: 9/10 (PASS)
  ✓ Script approved — advancing to voiceover

Step 2 — Generate Voiceover:
  → Calling ElevenLabs API...
  → Streaming audio chunks...
  ✓ Voiceover rendered (47.3s, mp3_44100_192)
  ✓ Audio saved to .tmp/job-demo/voiceover.mp3
  ✓ Word-per-minute validated (183 WPM)

Step 3 — Search Footage:
  → Searching Pexels: "sniper rifle scope close up"
  → Searching Pixabay: "military sniper weapon" [concurrent]
  ✓ Found 3 clips for sentence 1
  → Searching Pexels: "US Army training exercise"
  ✓ Found 2 clips for sentence 2
  → Searching Pexels: "brain anatomy diagram"
  ✓ Found 1 clip for sentence 3 (AI fallback queued for sentence 4)
  ✓ Footage search complete — 6/8 clips found, 2 AI gaps

Step 4 — Generate AI Footage:
  → Generating AI clip for sentence 4 via Runway gen4_turbo...
  → Prompt: "Close-up animation of brain stem cross-section, cinematic"
  ✓ AI clip generated (5s, 720x1280)
  → Stripping audio from all clips via ffmpeg...
  ✓ Audio stripped (8 clips)

Step 5 — Check Footage Gaps:
  → Analysing clip coverage...
  ✓ All 4 sentences covered
  ✓ No prop-library gaps detected
  ✓ Seamless loop: opening and closing clips match

Step 6 — Package Assets:
  → Generating overlay timestamps at 183 WPM...
  → Writing overlays.txt, music-timing.txt, loop.txt...
  → Extracting thumbnail from voiceover waveform...
  ✓ Thumbnail saved (thumbnail.jpg)
  ✓ Asset bundle complete — .tmp/job-demo/assets/
  ✓ Pipeline complete. Ready for CapCut editing.
```

All log lines are stored as a flat array in the hook. The log delivery loop uses an index pointer that increments every 900ms until all lines are delivered.

---

## PipelinePage Changes

**Demo button:** Placed alongside the "Run Pipeline" button in the job card:
```
[Demo]  [Run Pipeline]
```
- "Demo" is `variant="outlined"` with amber border/text (matches theme)
- While demo is active: button label becomes "Stop Demo", "Run Pipeline" is disabled
- While real pipeline is running: "Demo" button is disabled

**Demo banner:** Rendered between the topbar and job card only when `isDemoRunning`:
```
● DEMO MODE — simulated run, no API calls
```
- Styled as a slim amber-tinted Box (same as the window indicator in PublishPage): `bgcolor: IZK.card`, `borderLeft: 2px solid primary.main`, amber text at 60% opacity

**Job card while demo runs:**
- Job ID field shows `demoJobId`
- Subtitle shows `"Pipeline running (demo)..."`
- "Run Pipeline" button is disabled

**StepTracker:** receives `demoCompletedSteps` instead of `jobState?.completed_steps` when demo is active. `isRunning` receives `isDemoRunning`.

**LogPanel:** receives `demoLogLines` instead of `logLines` when demo is active.

**`● RUNNING` topbar badge:** shows when `isDemoRunning || isRunning`.

---

## State Logic

The hook uses two `useRef` values for the interval handles so cleanup is reliable:
- `stepIntervalRef` — drives step progression (cleared when stopDemo is called or log delivery finishes)
- `logIntervalRef` — drives log line delivery; self-terminates when the last line is delivered, triggering demo completion

Both are cleared in both `stopDemo()` and the `useEffect` cleanup. No memory leaks.

---

## Implementation Notes

- No new dependencies.
- The hook is self-contained — deleting `useDemoMode.ts` and removing the 4 lines referencing it in `PipelinePage` fully removes the feature when real API keys are ready.
- The log line array is defined as a `const` at module level (not inside the hook) so it doesn't re-allocate on render.
- Demo does not affect `PipelineContext` (`activeJobId`, `isRunning`) — the demo job ID and running state are local to the hook. This prevents the demo from accidentally auto-filling the job ID field in PublishPage or AnalyticsPage.
