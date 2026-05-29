# Pipeline Demo Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a browser-only demo mode to PipelinePage that simulates a full 6-step pipeline run with realistic fake log lines — no backend or API keys required.

**Architecture:** A `useDemoMode` hook owns all simulation state (two `setInterval` refs — one for step progression, one for log delivery). `PipelinePage` calls the hook and switches its display data sources between real and demo based on `isDemoRunning`. Demo data never touches `PipelineContext` so it doesn't bleed into other pages.

**Tech Stack:** React 19, MUI v9, TypeScript. Working directory: `E:/digital-sorcery/master-planner/yt-shorts/frontend`.

---

## File Map

| File | Change |
|---|---|
| `src/hooks/useDemoMode.ts` | **Create** — simulation hook with step + log interval loops |
| `src/pages/PipelinePage.tsx` | **Modify** — import hook, add Demo button, demo banner, switch display sources |

---

## Task 1: `useDemoMode` Hook

**Files:**
- Create: `frontend/src/hooks/useDemoMode.ts`

- [ ] **Step 1: Create `frontend/src/hooks/useDemoMode.ts`**

```typescript
import { useState, useRef, useEffect } from 'react'

const STEPS = [
  'generate_script',
  'generate_voiceover',
  'search_footage',
  'generate_ai_footage',
  'check_footage_gaps',
  'package_assets',
]

const LOG_LINES = [
  // Step 1 — Generate Script
  '→ Generating script for: "Why snipers never aim for center mass"',
  '→ Calling Claude API (claude-sonnet-4-6)...',
  '✓ Script generated (178 words, 4 sentences)',
  '✓ Word count validated (178 — within 168–183 target)',
  '→ Running compliance check...',
  '✓ Originality score: 8/10 (PASS)',
  '✓ Advertiser-friendliness: 9/10 (PASS)',
  '✓ Script approved — advancing to voiceover',
  // Step 2 — Generate Voiceover
  '→ Calling ElevenLabs API...',
  '→ Streaming audio chunks...',
  '✓ Voiceover rendered (47.3s, mp3_44100_192)',
  '✓ Audio saved to .tmp/job-demo/voiceover.mp3',
  '✓ Word-per-minute validated (183 WPM)',
  // Step 3 — Search Footage
  '→ Searching Pexels: "sniper rifle scope close up"',
  '→ Searching Pixabay: "military sniper weapon" [concurrent]',
  '✓ Found 3 clips for sentence 1',
  '→ Searching Pexels: "US Army training exercise"',
  '✓ Found 2 clips for sentence 2',
  '→ Searching Pexels: "brain anatomy diagram"',
  '✓ Found 1 clip for sentence 3 (AI fallback queued for sentence 4)',
  '✓ Footage search complete — 6/8 clips found, 2 AI gaps',
  // Step 4 — Generate AI Footage
  '→ Generating AI clip for sentence 4 via Runway gen4_turbo...',
  '→ Prompt: "Close-up animation of brain stem cross-section, cinematic"',
  '✓ AI clip generated (5s, 720x1280)',
  '→ Stripping audio from all clips via ffmpeg...',
  '✓ Audio stripped (8 clips)',
  // Step 5 — Check Footage Gaps
  '→ Analysing clip coverage...',
  '✓ All 4 sentences covered',
  '✓ No prop-library gaps detected',
  '✓ Seamless loop: opening and closing clips match',
  // Step 6 — Package Assets
  '→ Generating overlay timestamps at 183 WPM...',
  '→ Writing overlays.txt, music-timing.txt, loop.txt...',
  '→ Extracting thumbnail from voiceover waveform...',
  '✓ Thumbnail saved (thumbnail.jpg)',
  '✓ Asset bundle complete — .tmp/job-demo/assets/',
  '✓ Pipeline complete. Ready for CapCut editing.',
]

export interface DemoMode {
  isDemoRunning: boolean
  demoJobId: string | null
  demoCompletedSteps: string[]
  demoLogLines: string[]
  startDemo: () => void
  stopDemo: () => void
}

export function useDemoMode(): DemoMode {
  const [isDemoRunning, setIsDemoRunning] = useState(false)
  const [demoJobId, setDemoJobId] = useState<string | null>(null)
  const [demoCompletedSteps, setDemoCompletedSteps] = useState<string[]>([])
  const [demoLogLines, setDemoLogLines] = useState<string[]>([])

  const stepIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const logIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopDemo = () => {
    if (stepIntervalRef.current) clearInterval(stepIntervalRef.current)
    if (logIntervalRef.current) clearInterval(logIntervalRef.current)
    stepIntervalRef.current = null
    logIntervalRef.current = null
    setIsDemoRunning(false)
    setDemoJobId(null)
    setDemoCompletedSteps([])
    setDemoLogLines([])
  }

  const startDemo = () => {
    stopDemo()
    const jobId = `job-demo-${Date.now()}`
    setDemoJobId(jobId)
    setIsDemoRunning(true)
    setDemoCompletedSteps([])
    setDemoLogLines([])

    let stepIndex = 0
    let logIndex = 0

    stepIntervalRef.current = setInterval(() => {
      if (stepIndex < STEPS.length) {
        const step = STEPS[stepIndex]
        setDemoCompletedSteps(prev => [...prev, step])
        stepIndex++
      }
      if (stepIndex >= STEPS.length) {
        clearInterval(stepIntervalRef.current!)
        stepIntervalRef.current = null
      }
    }, 5000)

    logIntervalRef.current = setInterval(() => {
      if (logIndex < LOG_LINES.length) {
        const line = LOG_LINES[logIndex]
        setDemoLogLines(prev => [...prev, line])
        logIndex++
      }
      if (logIndex >= LOG_LINES.length) {
        clearInterval(logIntervalRef.current!)
        logIntervalRef.current = null
        if (stepIntervalRef.current) {
          clearInterval(stepIntervalRef.current)
          stepIntervalRef.current = null
        }
        setIsDemoRunning(false)
      }
    }, 900)
  }

  useEffect(() => {
    return () => {
      if (stepIntervalRef.current) clearInterval(stepIntervalRef.current)
      if (logIntervalRef.current) clearInterval(logIntervalRef.current)
    }
  }, [])

  return { isDemoRunning, demoJobId, demoCompletedSteps, demoLogLines, startDemo, stopDemo }
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts/frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts && git add frontend/src/hooks/useDemoMode.ts && git commit -m "feat: add useDemoMode hook with step + log simulation"
```

---

## Task 2: PipelinePage Integration

**Files:**
- Modify: `frontend/src/pages/PipelinePage.tsx`

Replace the entire file with:

- [ ] **Step 1: Write `frontend/src/pages/PipelinePage.tsx`**

```tsx
import { useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import BoltIcon from '@mui/icons-material/Bolt'
import { pipelineApi } from '../api/pipeline'
import { usePipelineContext } from '../store/PipelineContext'
import { useJobState } from '../hooks/useJobState'
import { useSSE } from '../hooks/useSSE'
import { useDemoMode } from '../hooks/useDemoMode'
import StepTracker from '../components/StepTracker'
import LogPanel from '../components/LogPanel'
import ErrorAlert from '../components/ErrorAlert'
import SectionLabel from '../components/SectionLabel'
import { getAxiosErrorMessage } from '../utils/errors'
import { IZK } from '../theme'

export default function PipelinePage() {
  const { activeJobId, isRunning, setActiveJob, setRunning } = usePipelineContext()
  const [logLines, setLogLines] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const jobState = useJobState(activeJobId)
  const { isDemoRunning, demoJobId, demoCompletedSteps, demoLogLines, startDemo, stopDemo } = useDemoMode()

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
    } catch (e: unknown) {
      setError(getAxiosErrorMessage(e, 'Failed to start pipeline'))
    }
  }

  const displayJobId = isDemoRunning ? demoJobId : activeJobId
  const displayCompletedSteps = isDemoRunning ? demoCompletedSteps : (jobState?.completed_steps ?? [])
  const displayLogLines = isDemoRunning ? demoLogLines : logLines
  const displayIsRunning = isDemoRunning || isRunning

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Topbar */}
      <Box sx={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        px: 3, py: '14px', borderBottom: '1px solid', borderColor: IZK.subtleBorder,
        bgcolor: 'background.paper', flexShrink: 0,
      }}>
        <Typography sx={{ fontSize: 13, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', color: 'text.secondary' }}>
          Pipeline
        </Typography>
        {displayIsRunning && (
          <Box sx={{
            fontSize: 9, letterSpacing: '1.5px', color: 'primary.main',
            animation: 'pulse 1.5s ease-in-out infinite',
            '@keyframes pulse': { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.4 } },
          }}>
            ● RUNNING
          </Box>
        )}
      </Box>

      {/* Content */}
      <Box sx={{ flex: 1, overflowY: 'auto', p: 3 }}>
        <ErrorAlert error={error} onClose={() => setError(null)} />

        {/* Demo banner */}
        {isDemoRunning && (
          <Box sx={{
            display: 'flex', alignItems: 'center', gap: 1.5,
            p: '8px 14px', mb: 2,
            bgcolor: IZK.card,
            border: '1px solid', borderColor: '#ff6b3530',
            borderLeft: '2px solid', borderLeftColor: 'primary.main',
          }}>
            <Box sx={{
              width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
              bgcolor: 'primary.main', boxShadow: '0 0 6px #ff6b35',
              animation: 'demoPulse 1.5s ease-in-out infinite',
              '@keyframes demoPulse': { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.4 } },
            }} />
            <Typography sx={{ fontSize: 10, color: '#ff6b3580', letterSpacing: '1px' }}>
              DEMO MODE — simulated run, no API calls
            </Typography>
          </Box>
        )}

        {/* Job card */}
        <Box sx={{
          display: 'flex', alignItems: 'center', gap: 2,
          p: '14px 16px', mb: 2,
          bgcolor: IZK.card,
          border: '1px solid', borderColor: '#ff6b3530',
          borderLeft: '2px solid', borderLeftColor: 'primary.main',
        }}>
          <Box sx={{ flex: 1 }}>
            <Typography sx={{ fontSize: 12, fontWeight: 600, color: 'text.primary', fontFamily: 'monospace' }}>
              {displayJobId ?? 'Ready to run'}
            </Typography>
            <Typography sx={{ fontSize: 11, color: IZK.muted, mt: 0.25 }}>
              {isDemoRunning
                ? 'Pipeline running (demo)...'
                : isRunning
                ? 'Pipeline running...'
                : activeJobId
                ? 'Completed'
                : 'Runs the next topic in the approved queue (~5–8 min)'}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="outlined"
              disabled={isRunning}
              onClick={isDemoRunning ? stopDemo : startDemo}
              sx={{
                borderColor: '#ff6b3550', color: '#ff6b3570',
                '&:hover': { borderColor: 'primary.main', color: 'primary.main', bgcolor: '#ff6b3508' },
              }}
            >
              {isDemoRunning ? 'Stop Demo' : 'Demo'}
            </Button>
            <Button
              variant="contained"
              startIcon={<BoltIcon />}
              disabled={isRunning || isDemoRunning}
              onClick={handleRun}
            >
              {isRunning ? 'Running...' : 'Run Pipeline'}
            </Button>
          </Box>
        </Box>

        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
          <Box>
            <SectionLabel>Steps</SectionLabel>
            <StepTracker completedSteps={displayCompletedSteps} isRunning={displayIsRunning} />
          </Box>
          <Box>
            <SectionLabel>
              Live Log{displayIsRunning && <span style={{ color: '#ff6b35', marginLeft: 6 }}>● LIVE</span>}
            </SectionLabel>
            <LogPanel lines={displayLogLines} height={340} />
          </Box>
        </Box>
      </Box>
    </Box>
  )
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts/frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Build check**

```bash
npm run build
```

Expected: build succeeds, zero errors.

- [ ] **Step 4: Commit**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts && git add frontend/src/pages/PipelinePage.tsx && git commit -m "feat: add demo mode to PipelinePage (Demo/Stop Demo button + banner)"
```

---

## Final Verification

- [ ] **Start dev server**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts/frontend && npm run dev
```

Open `http://localhost:5173` and navigate to Pipeline. Verify:
- "Demo" button appears next to "Run Pipeline" in the job card
- Click "Demo" → amber "DEMO MODE" banner appears, "● RUNNING" badge shows in topbar, button changes to "Stop Demo"
- Steps begin checking off one by one (~5s each): Generate Script → Generate Voiceover → Search Footage → Generate AI Footage → Check Footage Gaps → Package Assets
- Log lines stream into the LogPanel at ~1/second with realistic content (✓ green for success, → amber for info)
- After ~50s all lines delivered → demo ends, UI returns to idle, "Demo" button restores
- Click "Stop Demo" mid-run → immediately resets to idle
- While demo running: "Run Pipeline" is disabled
- Navigating to Topics/Analytics and back: demo state is gone (hook unmounts → cleanup fires)
