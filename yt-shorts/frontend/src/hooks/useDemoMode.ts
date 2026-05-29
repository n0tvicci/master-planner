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
