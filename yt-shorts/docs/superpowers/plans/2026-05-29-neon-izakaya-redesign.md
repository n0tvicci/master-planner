# Neon Izakaya Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fully restyle the React + MUI frontend to a modern Japanese low-light "Neon Izakaya" aesthetic — deep purple-black backgrounds, amber neon primary accent, forest green for success, warm off-white text.

**Architecture:** Change is purely visual — no logic, no API, no routing changes. Work bottom-up: theme first (all MUI components inherit from it), then layout shell, then shared components, then pages. Each task is one file. TypeScript build check after each commit confirms no regressions.

**Tech Stack:** React 19, MUI v9, TypeScript, Vite. Working directory: `E:/digital-sorcery/master-planner/yt-shorts/frontend`.

---

## File Map

| File | Change |
|---|---|
| `src/theme/index.ts` | Full palette + MUI component overrides + export `IZK` constants |
| `src/layouts/AppShell.tsx` | Sidebar brand, nav dots, neon active state, footer |
| `src/components/SectionLabel.tsx` | Amber label + trailing gradient line |
| `src/components/StatusBadge.tsx` | Sharp-corner tier pill with neon amber/green |
| `src/components/LogPanel.tsx` | Terminal dark bg, monospace, prefix-based line coloring |
| `src/components/StepTracker.tsx` | Square nodes, amber active glow, connector lines |
| `src/components/TopicCard.tsx` | Square score badge, neon featured state, slim action buttons |
| `src/components/ErrorAlert.tsx` | Custom dark error panel (replaces MUI Alert) |
| `src/pages/TopicsPage.tsx` | Topbar pattern, izakaya queue items |
| `src/pages/PipelinePage.tsx` | Topbar, fix LIVE indicator color, job card reskin |
| `src/pages/PublishPage.tsx` | Topbar, fix missing Alert import bug, upload button reskin |
| `src/pages/AnalyticsPage.tsx` | Topbar, stat cards, amber US share glow |

---

## Task 1: Theme + IZK Constants

**Files:**
- Modify: `src/theme/index.ts`

- [ ] **Step 1: Replace `src/theme/index.ts` entirely**

```typescript
import { createTheme } from '@mui/material/styles'

export const IZK = {
  card: '#130f1e',
  terminal: '#080610',
  muted: '#4a3f5a',
  dim: '#3a3050',
  subtleBorder: '#1a1428',
} as const

export const theme = createTheme({
  shape: { borderRadius: 0 },
  palette: {
    mode: 'dark',
    primary: { main: '#ff6b35' },
    secondary: { main: '#2d6a4f' },
    background: { default: '#0e0b14', paper: '#0b0910' },
    text: { primary: '#e8ddd0', secondary: '#c4b4a4' },
    divider: '#2a2040',
    error: { main: '#c0392b' },
    warning: { main: '#d4a017' },
    success: { main: '#2d6a4f' },
  },
  typography: {
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: 'none' },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 0,
          textTransform: 'uppercase' as const,
          letterSpacing: '2px',
          fontSize: '10px',
          fontWeight: 600,
          boxShadow: 'none',
          '&:hover': { boxShadow: 'none' },
        },
        contained: {
          backgroundColor: '#ff6b35',
          color: '#0e0b14',
          '&:hover': { backgroundColor: '#ff8550', boxShadow: '0 0 12px #ff6b3540' },
          '&.Mui-disabled': { backgroundColor: '#2a2040', color: '#3a3050' },
        },
        outlined: {
          borderColor: '#ff6b35',
          color: '#ff6b35',
          '&:hover': { backgroundColor: '#ff6b3510', borderColor: '#ff6b35' },
          '&.Mui-disabled': { borderColor: '#2a2040', color: '#3a3050' },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 0,
          fontSize: '9px',
          letterSpacing: '1px',
          height: '22px',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 0,
            fontSize: '12px',
            backgroundColor: '#130f1e',
            '& fieldset': { borderColor: '#2a2040' },
            '&:hover fieldset': { borderColor: '#4a3f5a' },
            '&.Mui-focused fieldset': { borderColor: '#ff6b35' },
          },
          '& .MuiInputLabel-root.Mui-focused': { color: '#ff6b35' },
        },
      },
    },
    MuiCheckbox: {
      styleOverrides: {
        root: {
          color: '#2a2040',
          '&.Mui-checked': { color: '#ff6b35' },
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: { borderRadius: 0, backgroundColor: '#130f1e', height: 4 },
        bar: { backgroundColor: '#ff6b35', borderRadius: 0 },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: { borderColor: '#1a1428' },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: { backgroundColor: '#0b0910', borderRight: '1px solid #1a1428' },
      },
    },
    MuiCircularProgress: {
      styleOverrides: {
        root: { color: '#ff6b35' },
      },
    },
  },
})
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts/frontend
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/theme/index.ts
git commit -m "feat: neon izakaya — theme palette + MUI component overrides"
```

---

## Task 2: AppShell

**Files:**
- Modify: `src/layouts/AppShell.tsx`

- [ ] **Step 1: Replace `src/layouts/AppShell.tsx` entirely**

```tsx
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import Box from '@mui/material/Box'
import Drawer from '@mui/material/Drawer'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemText from '@mui/material/ListItemText'
import Typography from '@mui/material/Typography'
import ListAltIcon from '@mui/icons-material/ListAlt'
import BoltIcon from '@mui/icons-material/Bolt'
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch'
import BarChartIcon from '@mui/icons-material/BarChart'
import { IZK } from '../theme'

const W = 200
const NAV = [
  { label: 'Topics', path: '/', Icon: ListAltIcon },
  { label: 'Pipeline', path: '/pipeline', Icon: BoltIcon },
  { label: 'Publish', path: '/publish', Icon: RocketLaunchIcon },
  { label: 'Analytics', path: '/analytics', Icon: BarChartIcon },
]

export default function AppShell() {
  const navigate = useNavigate()
  const { pathname } = useLocation()

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <Drawer
        variant="permanent"
        sx={{ width: W, flexShrink: 0, '& .MuiDrawer-paper': { width: W } }}
      >
        <Box sx={{ p: '20px 16px 16px', borderBottom: '1px solid', borderColor: IZK.subtleBorder }}>
          <Typography sx={{
            fontSize: 11, fontWeight: 700, letterSpacing: '5px',
            textTransform: 'uppercase', color: 'primary.main',
            textShadow: '0 0 10px #ff6b3570', mb: 0.5,
          }}>
            Shorts
          </Typography>
          <Typography sx={{ fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: IZK.dim }}>
            YT Automation
          </Typography>
        </Box>

        <List dense sx={{ pt: 1.5, flex: 1 }}>
          {NAV.map(({ label, path }) => {
            const active = pathname === path
            return (
              <ListItemButton
                key={path}
                selected={active}
                onClick={() => navigate(path)}
                sx={{
                  borderLeft: '2px solid',
                  borderColor: active ? 'primary.main' : 'transparent',
                  background: active ? 'linear-gradient(90deg, #ff6b3510, transparent)' : 'transparent',
                  '&.Mui-selected': { bgcolor: 'transparent' },
                  '&.Mui-selected:hover': { bgcolor: '#ff6b3508' },
                  '&:hover': { bgcolor: '#ff6b3806' },
                  py: 1.25, px: 2,
                }}
              >
                <Box sx={{
                  width: 6, height: 6, borderRadius: '50%', mr: 1.5, flexShrink: 0,
                  bgcolor: active ? 'primary.main' : IZK.dim,
                  boxShadow: active ? '0 0 6px #ff6b35' : 'none',
                  transition: 'all 0.15s',
                }} />
                <ListItemText
                  primary={label}
                  primaryTypographyProps={{
                    fontSize: 12,
                    letterSpacing: '0.5px',
                    color: active ? 'text.primary' : IZK.muted,
                  }}
                />
              </ListItemButton>
            )
          })}
        </List>

        <Box sx={{ p: '12px 16px', borderTop: '1px solid', borderColor: IZK.subtleBorder }}>
          <Typography sx={{ fontSize: 9, color: IZK.dim, letterSpacing: '1px' }}>
            EST · UTC−5
          </Typography>
        </Box>
      </Drawer>

      <Box component="main" sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', bgcolor: 'background.default' }}>
        <Outlet />
      </Box>
    </Box>
  )
}
```

- [ ] **Step 2: TypeScript check**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/layouts/AppShell.tsx
git commit -m "feat: neon izakaya — AppShell sidebar with neon nav dots"
```

---

## Task 3: SectionLabel

**Files:**
- Modify: `src/components/SectionLabel.tsx`

- [ ] **Step 1: Replace `src/components/SectionLabel.tsx` entirely**

```tsx
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import type { ReactNode } from 'react'

export default function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.5 }}>
      <Typography sx={{
        fontSize: 9,
        letterSpacing: '3px',
        textTransform: 'uppercase',
        color: '#ff6b3599',
        flexShrink: 0,
        lineHeight: 1,
      }}>
        {children}
      </Typography>
      <Box sx={{ flex: 1, height: '1px', background: 'linear-gradient(90deg, #ff6b3525, transparent)' }} />
    </Box>
  )
}
```

- [ ] **Step 2: TypeScript check**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SectionLabel.tsx
git commit -m "feat: neon izakaya — SectionLabel amber gradient line"
```

---

## Task 4: StatusBadge

**Files:**
- Modify: `src/components/StatusBadge.tsx`

Props stay the same (`tier: number`, `score?: number`). Visual replaces the MUI Chip with a sharp-corner neon pill.

- [ ] **Step 1: Replace `src/components/StatusBadge.tsx` entirely**

```tsx
import Box from '@mui/material/Box'
import { IZK } from '../theme'

interface Props {
  tier: number
  score?: number
}

export default function StatusBadge({ tier, score }: Props) {
  const label = score != null ? `Tier ${tier} · ${score}/10` : `Tier ${tier}`
  const color = tier === 1 ? '#2d6a4f' : tier === 2 ? '#d4a017' : IZK.dim
  const borderColor = tier === 1 ? '#2d6a4f60' : tier === 2 ? '#d4a01750' : '#2a2040'

  return (
    <Box sx={{
      display: 'inline-flex',
      alignItems: 'center',
      fontSize: 8,
      letterSpacing: '1.5px',
      textTransform: 'uppercase',
      color,
      border: '1px solid',
      borderColor,
      px: 1,
      py: 0.25,
      lineHeight: 1.6,
      flexShrink: 0,
    }}>
      {label}
    </Box>
  )
}
```

- [ ] **Step 2: TypeScript check**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/StatusBadge.tsx
git commit -m "feat: neon izakaya — StatusBadge sharp-corner tier pill"
```

---

## Task 5: LogPanel

**Files:**
- Modify: `src/components/LogPanel.tsx`

Add prefix-based line coloring: `✓`/`OK` → green, `→`/`INFO` → amber at 60%, `✗`/`ERROR` → red, default → dim.

- [ ] **Step 1: Replace `src/components/LogPanel.tsx` entirely**

```tsx
import { useEffect, useRef } from 'react'
import Box from '@mui/material/Box'
import { IZK } from '../theme'

function lineColor(line: string): string {
  const t = line.trimStart()
  if (t.startsWith('✓') || t.startsWith('OK')) return '#2d6a4f'
  if (t.startsWith('✗') || t.startsWith('ERROR')) return '#c0392b'
  if (t.startsWith('→') || t.startsWith('INFO')) return '#ff6b3599'
  return IZK.dim
}

export default function LogPanel({ lines, height = 280 }: { lines: string[]; height?: number | string }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => { ref.current?.scrollIntoView({ behavior: 'smooth' }) }, [lines])

  return (
    <Box sx={{
      bgcolor: IZK.terminal,
      border: '1px solid',
      borderColor: IZK.subtleBorder,
      p: 1.5,
      height,
      overflowY: 'auto',
      fontFamily: '"Courier New", monospace',
    }}>
      {lines.length === 0
        ? <Box component="span" sx={{ fontSize: 11, color: IZK.dim }}>Waiting for output...</Box>
        : lines.map((line, i) => (
            <Box key={i} component="div" sx={{ fontSize: 11, lineHeight: 1.7, color: lineColor(line), whiteSpace: 'pre-wrap' }}>
              {line}
            </Box>
          ))
      }
      <div ref={ref} />
    </Box>
  )
}
```

- [ ] **Step 2: TypeScript check**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/LogPanel.tsx
git commit -m "feat: neon izakaya — LogPanel terminal dark bg + prefix coloring"
```

---

## Task 6: StepTracker

**Files:**
- Modify: `src/components/StepTracker.tsx`

Replace circular nodes with 28×28 square nodes. Amber glow on active. Remove `Paper` wrapper per step — use plain `Box` rows.

- [ ] **Step 1: Replace `src/components/StepTracker.tsx` entirely**

```tsx
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import { IZK } from '../theme'

const STEPS = [
  { key: 'generate_script', label: 'Generate Script' },
  { key: 'generate_voiceover', label: 'Generate Voiceover' },
  { key: 'search_footage', label: 'Search Footage' },
  { key: 'generate_ai_footage', label: 'Generate AI Footage' },
  { key: 'check_footage_gaps', label: 'Check Footage Gaps' },
  { key: 'package_assets', label: 'Package Assets' },
]

export default function StepTracker({ completedSteps, isRunning }: { completedSteps: string[]; isRunning: boolean }) {
  const done = new Set(completedSteps)
  const nextIdx = STEPS.findIndex(s => !done.has(s.key))

  return (
    <Box>
      {STEPS.map((step, i) => {
        const isDone = done.has(step.key)
        const isActive = isRunning && i === nextIdx
        return (
          <Box
            key={step.key}
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              p: '10px 12px',
              mb: 0.5,
              bgcolor: isActive ? '#ff6b3508' : IZK.card,
              border: '1px solid',
              borderColor: isActive ? '#ff6b3540' : IZK.subtleBorder,
              borderLeft: '2px solid',
              borderLeftColor: isDone ? '#2d6a4f60' : isActive ? 'primary.main' : 'transparent',
              transition: 'all 0.15s',
            }}
          >
            <Box sx={{
              width: 24,
              height: 24,
              flexShrink: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid',
              borderColor: isDone ? '#2d6a4f60' : isActive ? 'primary.main' : '#2a2040',
              bgcolor: isDone ? '#2d6a4f10' : isActive ? '#ff6b3510' : 'transparent',
              boxShadow: isActive ? '0 0 8px #ff6b3540' : 'none',
              color: isDone ? '#2d6a4f' : isActive ? 'primary.main' : IZK.dim,
              fontSize: 10,
              fontWeight: 700,
            }}>
              {isDone ? '✓' : i + 1}
            </Box>
            <Typography sx={{
              fontSize: 12,
              color: isDone ? 'text.secondary' : isActive ? 'text.primary' : IZK.dim,
              fontWeight: isActive ? 600 : 400,
              flex: 1,
            }}>
              {step.label}
            </Typography>
            {isActive && (
              <Box sx={{
                fontSize: 8,
                letterSpacing: '1.5px',
                color: 'primary.main',
                textTransform: 'uppercase',
                animation: 'pulse 1.5s ease-in-out infinite',
                '@keyframes pulse': { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.4 } },
              }}>
                Running
              </Box>
            )}
          </Box>
        )
      })}
    </Box>
  )
}
```

- [ ] **Step 2: TypeScript check**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/StepTracker.tsx
git commit -m "feat: neon izakaya — StepTracker square nodes with amber glow"
```

---

## Task 7: TopicCard

**Files:**
- Modify: `src/components/TopicCard.tsx`

Replace circular score badge with square. Featured state (tier 1) gets neon left border + inset glow. Approve/Reject buttons use theme styles.

- [ ] **Step 1: Replace `src/components/TopicCard.tsx` entirely**

```tsx
import { useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import CheckIcon from '@mui/icons-material/Check'
import CloseIcon from '@mui/icons-material/Close'
import StatusBadge from './StatusBadge'
import type { Topic } from '../types'
import { IZK } from '../theme'

interface Props {
  topic: Topic
  onApprove: (id: string) => Promise<void>
  onReject: (id: string) => Promise<void>
}

export default function TopicCard({ topic, onApprove, onReject }: Props) {
  const [busy, setBusy] = useState<'approve' | 'reject' | null>(null)

  const handle = (action: 'approve' | 'reject') => async () => {
    setBusy(action)
    try { action === 'approve' ? await onApprove(topic.id) : await onReject(topic.id) }
    finally { setBusy(null) }
  }

  const isFeatured = topic.tier === 1

  return (
    <Box sx={{
      display: 'flex',
      alignItems: 'center',
      gap: 2,
      p: '14px 16px',
      mb: 0.75,
      bgcolor: isFeatured ? '#160d1e' : IZK.card,
      border: '1px solid',
      borderColor: isFeatured ? '#2a2040' : IZK.subtleBorder,
      borderLeft: '2px solid',
      borderLeftColor: isFeatured ? 'primary.main' : 'transparent',
      boxShadow: isFeatured ? '0 0 20px #ff6b3510, inset 0 0 20px #ff6b3505' : 'none',
    }}>
      <Box sx={{
        width: 32,
        height: 32,
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        border: '1px solid',
        borderColor: isFeatured ? '#ff6b3550' : '#2a2040',
        color: isFeatured ? 'primary.main' : IZK.dim,
        fontSize: 11,
        fontWeight: 700,
        textShadow: isFeatured ? '0 0 8px #ff6b35' : 'none',
      }}>
        {topic.tier_score ?? topic.tier}
      </Box>

      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography sx={{
          fontSize: 12,
          color: isFeatured ? 'text.primary' : IZK.muted,
          fontWeight: isFeatured ? 500 : 400,
          mb: 0.5,
          lineHeight: 1.4,
        }} noWrap>
          {topic.title}
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <StatusBadge tier={topic.tier} score={topic.tier_score} />
          {topic.hook_object && (
            <Typography sx={{ fontSize: 9, color: IZK.dim, letterSpacing: '0.5px' }}>
              Hook: {topic.hook_object}
            </Typography>
          )}
        </Box>
      </Box>

      <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
        <Button
          size="small"
          variant="outlined"
          startIcon={<CheckIcon sx={{ fontSize: '12px !important' }} />}
          disabled={busy !== null}
          onClick={handle('approve')}
          sx={{ borderColor: '#2d6a4f', color: '#2d6a4f', '&:hover': { bgcolor: '#2d6a4f10', borderColor: '#2d6a4f' } }}
        >
          Approve
        </Button>
        <Button
          size="small"
          variant="outlined"
          startIcon={<CloseIcon sx={{ fontSize: '12px !important' }} />}
          disabled={busy !== null}
          onClick={handle('reject')}
          sx={{ borderColor: '#c0392b60', color: '#c0392b80', '&:hover': { bgcolor: '#c0392b08', borderColor: '#c0392b' } }}
        >
          Reject
        </Button>
      </Box>
    </Box>
  )
}
```

- [ ] **Step 2: TypeScript check**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/TopicCard.tsx
git commit -m "feat: neon izakaya — TopicCard square badge + neon featured state"
```

---

## Task 8: ErrorAlert

**Files:**
- Modify: `src/components/ErrorAlert.tsx`

Replace MUI `Alert` with a custom dark panel — consistent with the izakaya palette.

- [ ] **Step 1: Replace `src/components/ErrorAlert.tsx` entirely**

```tsx
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import IconButton from '@mui/material/IconButton'
import CloseIcon from '@mui/icons-material/Close'

const SEVERITY_COLORS = {
  error: { border: '#c0392b60', left: '#c0392b', bg: '#1a0a0a', text: '#e8c4c4' },
  warning: { border: '#d4a01760', left: '#d4a017', bg: '#1a1500', text: '#e8ddb0' },
  info: { border: '#ff6b3540', left: '#ff6b35', bg: '#130f1e', text: '#e8ddd0' },
} as const

interface Props {
  error: string | null
  onClose?: () => void
  severity?: 'error' | 'warning' | 'info'
}

export default function ErrorAlert({ error, onClose, severity = 'error' }: Props) {
  if (!error) return null
  const c = SEVERITY_COLORS[severity]
  return (
    <Box sx={{
      display: 'flex',
      alignItems: 'center',
      gap: 1.5,
      p: '10px 14px',
      mb: 2,
      bgcolor: c.bg,
      border: '1px solid',
      borderColor: c.border,
      borderLeft: '2px solid',
      borderLeftColor: c.left,
    }}>
      <Typography sx={{ flex: 1, fontSize: 12, color: c.text }}>{error}</Typography>
      {onClose && (
        <IconButton size="small" onClick={onClose} sx={{ color: c.left, p: 0.25 }}>
          <CloseIcon sx={{ fontSize: 14 }} />
        </IconButton>
      )}
    </Box>
  )
}
```

- [ ] **Step 2: TypeScript check**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ErrorAlert.tsx
git commit -m "feat: neon izakaya — ErrorAlert custom dark panel"
```

---

## Task 9: TopicsPage

**Files:**
- Modify: `src/pages/TopicsPage.tsx`

Add page topbar (title left, pending count right). Replace `Typography variant="h6"` header. Update queue item Paper → Box. Update `CircularProgress` color (inherits from theme). Keep all logic unchanged.

- [ ] **Step 1: Replace `src/pages/TopicsPage.tsx` entirely**

```tsx
import { useCallback, useEffect, useRef, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import Typography from '@mui/material/Typography'
import AddIcon from '@mui/icons-material/Add'
import TopicCard from '../components/TopicCard'
import ErrorAlert from '../components/ErrorAlert'
import SectionLabel from '../components/SectionLabel'
import { topicsApi } from '../api/topics'
import { IZK } from '../theme'
import type { Topic } from '../types'

export default function TopicsPage() {
  const [pending, setPending] = useState<Topic[]>([])
  const [queue, setQueue] = useState<Topic[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const refresh = useCallback(async () => {
    const [p, q] = await Promise.all([topicsApi.getPending(), topicsApi.getQueue()])
    setPending(p)
    setQueue(q)
  }, [])

  useEffect(() => {
    refresh().finally(() => setLoading(false))
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }
  }, [refresh])

  const handleGenerate = async () => {
    setError(null)
    setGenerating(true)
    try {
      await topicsApi.generate()
    } catch {
      setError('Failed to start topic generation')
      setGenerating(false)
      return
    }
    const before = pending.length
    pollRef.current = setInterval(async () => {
      try {
        const p = await topicsApi.getPending()
        if (p.length > before) {
          setPending(p)
          if (pollRef.current) clearInterval(pollRef.current)
          if (timeoutRef.current) clearTimeout(timeoutRef.current)
          setGenerating(false)
        }
      } catch { /* ignore poll errors */ }
    }, 2000)
    timeoutRef.current = setTimeout(() => {
      if (pollRef.current) clearInterval(pollRef.current)
      setGenerating(false)
    }, 90000)
  }

  const handleApprove = async (id: string) => {
    try { await topicsApi.approve(id); await refresh() }
    catch { setError('Failed to approve topic') }
  }

  const handleReject = async (id: string) => {
    try { await topicsApi.reject(id); await refresh() }
    catch { setError('Failed to reject topic') }
  }

  if (loading) return (
    <Box sx={{ display: 'flex', justifyContent: 'center', pt: 8 }}>
      <CircularProgress size={24} />
    </Box>
  )

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Topbar */}
      <Box sx={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        px: 3, py: '14px', borderBottom: '1px solid', borderColor: IZK.subtleBorder,
        bgcolor: 'background.paper', flexShrink: 0,
      }}>
        <Typography sx={{ fontSize: 13, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', color: 'text.secondary' }}>
          Topics
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          {pending.length > 0 && (
            <Box sx={{ fontSize: 9, letterSpacing: '1px', color: '#ff6b3560', bgcolor: '#ff6b3510', border: '1px solid #ff6b3520', px: 1, py: 0.25 }}>
              {pending.length} PENDING
            </Box>
          )}
          <Button
            variant="contained"
            startIcon={generating ? <CircularProgress size={12} sx={{ color: '#0e0b14' }} /> : <AddIcon />}
            disabled={generating}
            onClick={handleGenerate}
          >
            {generating ? 'Generating...' : 'Generate Topics'}
          </Button>
        </Box>
      </Box>

      {/* Content */}
      <Box sx={{ flex: 1, overflowY: 'auto', p: 3 }}>
        <ErrorAlert error={error} onClose={() => setError(null)} />

        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 3 }}>
          <Box>
            <SectionLabel>Pending Approval ({pending.length})</SectionLabel>
            {pending.length === 0
              ? <Typography sx={{ fontSize: 12, color: IZK.muted }}>No pending topics. Click Generate to create new ones.</Typography>
              : pending.map(t => <TopicCard key={t.id} topic={t} onApprove={handleApprove} onReject={handleReject} />)
            }
          </Box>

          <Box>
            <SectionLabel>Approved Queue ({queue.length})</SectionLabel>
            {queue.map((t, i) => (
              <Box key={t.id ?? i} sx={{
                display: 'flex', alignItems: 'center', gap: 1.5,
                p: '10px 12px', mb: 0.5,
                bgcolor: IZK.card, border: '1px solid', borderColor: IZK.subtleBorder,
              }}>
                <Typography sx={{ fontSize: 10, color: 'primary.main', fontWeight: 700, minWidth: 16 }}>{i + 1}</Typography>
                <Typography sx={{ fontSize: 12, color: 'text.secondary', flex: 1 }} noWrap>{t.title}</Typography>
                {t.tier_score && (
                  <Typography sx={{ fontSize: 9, color: IZK.dim, letterSpacing: '1px' }}>
                    {t.tier_score}/10
                  </Typography>
                )}
              </Box>
            ))}
            {queue.length === 0 && (
              <Typography sx={{ fontSize: 12, color: IZK.muted }}>No approved topics yet.</Typography>
            )}
          </Box>
        </Box>
      </Box>
    </Box>
  )
}
```

- [ ] **Step 2: TypeScript check**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/TopicsPage.tsx
git commit -m "feat: neon izakaya — TopicsPage topbar + queue items"
```

---

## Task 10: PipelinePage

**Files:**
- Modify: `src/pages/PipelinePage.tsx`

Add topbar. Replace `Paper` job card with `Box`. Fix `color: '#4f79ff'` hardcoded color. Keep all logic unchanged.

- [ ] **Step 1: Replace `src/pages/PipelinePage.tsx` entirely**

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
        {isRunning && (
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
              {activeJobId ?? 'Ready to run'}
            </Typography>
            <Typography sx={{ fontSize: 11, color: IZK.muted, mt: 0.25 }}>
              {isRunning ? 'Pipeline running...' : activeJobId ? 'Completed' : 'Runs the next topic in the approved queue (~5–8 min)'}
            </Typography>
          </Box>
          <Button variant="contained" startIcon={<BoltIcon />} disabled={isRunning} onClick={handleRun}>
            {isRunning ? 'Running...' : 'Run Pipeline'}
          </Button>
        </Box>

        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
          <Box>
            <SectionLabel>Steps</SectionLabel>
            <StepTracker completedSteps={jobState?.completed_steps ?? []} isRunning={isRunning} />
          </Box>
          <Box>
            <SectionLabel>
              Live Log{isRunning && <span style={{ color: '#ff6b35', marginLeft: 6 }}>● LIVE</span>}
            </SectionLabel>
            <LogPanel lines={logLines} height={340} />
          </Box>
        </Box>
      </Box>
    </Box>
  )
}
```

- [ ] **Step 2: TypeScript check**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/PipelinePage.tsx
git commit -m "feat: neon izakaya — PipelinePage topbar + job card reskin"
```

---

## Task 11: PublishPage

**Files:**
- Modify: `src/pages/PublishPage.tsx`

Add topbar. Fix bug: `Alert` is used but never imported — replace with the `ErrorAlert` component styled as `info`. Remove the hardcoded `background: linear-gradient(135deg, #4f79ff, #7c3aed)` on the upload button. Remove `Chip` import (replaced by metadata tag boxes). Keep all logic unchanged.

- [ ] **Step 1: Replace `src/pages/PublishPage.tsx` entirely**

```tsx
import { useCallback, useEffect, useRef, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import FormControlLabel from '@mui/material/FormControlLabel'
import Checkbox from '@mui/material/Checkbox'
import TextField from '@mui/material/TextField'
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch'
import { usePublishContext } from '../store/PublishContext'
import { usePipelineContext } from '../store/PipelineContext'
import { publishApi } from '../api/publish'
import { useSSE } from '../hooks/useSSE'
import LogPanel from '../components/LogPanel'
import ErrorAlert from '../components/ErrorAlert'
import SectionLabel from '../components/SectionLabel'
import { getAxiosErrorMessage } from '../utils/errors'
import { IZK } from '../theme'
import type { Metadata, UploadWindow } from '../types'

export default function PublishPage() {
  const { jobId, setJobId, checks, toggleCheck, allChecked, gateItems, resetChecks } = usePublishContext()
  const { activeJobId } = usePipelineContext()
  const [window_, setWindow_] = useState<UploadWindow | null>(null)
  const [metadata, setMetadata] = useState<Metadata | null>(null)
  const [uploading, setUploading] = useState(false)
  const [streamJobId, setStreamJobId] = useState<string | null>(null)
  const [logLines, setLogLines] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    publishApi.getWindow().then(setWindow_).catch(() => {})
    const id = setInterval(() => publishApi.getWindow().then(setWindow_).catch(() => {}), 60000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    if (activeJobId && !jobId) setJobId(activeJobId)
  }, [activeJobId])

  const loadMeta = useCallback(async (id: string) => {
    try { setMetadata(await publishApi.getMetadata(id)) }
    catch { setMetadata(null) }
  }, [])

  useEffect(() => { if (jobId) loadMeta(jobId); else setMetadata(null) }, [jobId, loadMeta])

  useSSE(streamJobId ? publishApi.streamUrl(streamJobId) : null,
    (line) => setLogLines(p => [...p, line]),
    () => setUploading(false))

  const handleJobChange = (val: string) => {
    setJobId(val || null); resetChecks(); setLogLines([]); setError(null)
  }

  const handleUpload = async () => {
    if (!jobId || !allChecked) return
    setError(null); setLogLines([]); setUploading(true)
    try { await publishApi.upload(jobId); setStreamJobId(jobId) }
    catch (e: unknown) {
      setError(getAxiosErrorMessage(e, 'Upload failed'))
      setUploading(false)
    }
  }

  const nextWindowStr = window_?.next_window
    ? new Date(window_.next_window).toLocaleString('en-US', { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' })
    : '...'

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Topbar */}
      <Box sx={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        px: 3, py: '14px', borderBottom: '1px solid', borderColor: IZK.subtleBorder,
        bgcolor: 'background.paper', flexShrink: 0,
      }}>
        <Typography sx={{ fontSize: 13, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', color: 'text.secondary' }}>
          Publish
        </Typography>
        <Button
          variant="outlined"
          size="small"
          disabled={!jobId || uploading}
          onClick={() => jobId && publishApi.upload(jobId, true).catch(() => {})}
        >
          Dry Run
        </Button>
      </Box>

      {/* Content */}
      <Box sx={{ flex: 1, overflowY: 'auto', p: 3 }}>
        <TextField
          label="Job ID"
          size="small"
          value={jobId ?? ''}
          placeholder="job-20260526-143021"
          onChange={e => handleJobChange(e.target.value)}
          sx={{ mb: 2, width: 300 }}
        />

        <ErrorAlert error={error} onClose={() => setError(null)} />

        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 3 }}>
          <Box>
            <SectionLabel>Pre-Upload Checklist</SectionLabel>
            <Box sx={{ bgcolor: IZK.card, border: '1px solid', borderColor: IZK.subtleBorder, p: 1.5, mb: 2 }}>
              {gateItems.map((item, i) => (
                <Box key={i} sx={{
                  borderBottom: i < gateItems.length - 1 ? '1px solid' : 'none',
                  borderColor: IZK.subtleBorder, py: 0.5,
                }}>
                  <FormControlLabel
                    control={<Checkbox size="small" checked={checks[i]} onChange={() => toggleCheck(i)} />}
                    label={<Typography sx={{ fontSize: 12, color: checks[i] ? 'text.primary' : IZK.muted }}>{item}</Typography>}
                  />
                </Box>
              ))}
            </Box>

            {window_ && (
              <Box sx={{
                p: '10px 14px', mb: 2,
                bgcolor: IZK.card,
                border: '1px solid',
                borderColor: window_.in_window ? '#2d6a4f40' : '#d4a01740',
                borderLeft: '2px solid',
                borderLeftColor: window_.in_window ? '#2d6a4f' : '#d4a017',
              }}>
                <Typography sx={{ fontSize: 12, color: window_.in_window ? '#2d6a4f' : '#d4a017' }}>
                  {window_.in_window ? '● In optimal upload window now' : `Next window: ${nextWindowStr}`}
                </Typography>
              </Box>
            )}

            <Button
              variant="contained"
              size="large"
              startIcon={<RocketLaunchIcon />}
              disabled={!allChecked || uploading || !jobId}
              onClick={handleUpload}
            >
              {uploading ? 'Uploading...' : 'Upload to YouTube'}
            </Button>
            {!allChecked && (
              <Typography sx={{ fontSize: 11, color: IZK.dim, display: 'block', mt: 1 }}>
                Complete checklist to enable upload
              </Typography>
            )}
          </Box>

          <Box>
            <SectionLabel>Metadata Preview</SectionLabel>
            {metadata ? (
              <Box sx={{ bgcolor: IZK.card, border: '1px solid', borderColor: IZK.subtleBorder, p: 2, mb: 2 }}>
                <Typography sx={{ fontSize: 9, color: IZK.dim, letterSpacing: '2px', textTransform: 'uppercase', mb: 0.5 }}>Title</Typography>
                <Typography sx={{ fontSize: 12, fontWeight: 600, color: 'text.primary', mb: 2 }}>{metadata.title}</Typography>

                <Typography sx={{ fontSize: 9, color: IZK.dim, letterSpacing: '2px', textTransform: 'uppercase', mb: 0.5 }}>Description</Typography>
                <Typography sx={{ fontSize: 11, color: 'text.secondary', mb: 2, lineHeight: 1.6 }}>{metadata.description}</Typography>

                <Typography sx={{ fontSize: 9, color: IZK.dim, letterSpacing: '2px', textTransform: 'uppercase', mb: 0.75 }}>Tags</Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 2 }}>
                  {metadata.tags.map(tag => (
                    <Box key={tag} sx={{ fontSize: 9, letterSpacing: '1px', color: IZK.muted, border: '1px solid #2a2040', px: 1, py: 0.25 }}>
                      {tag}
                    </Box>
                  ))}
                </Box>

                <Typography sx={{ fontSize: 9, color: IZK.dim, letterSpacing: '2px', textTransform: 'uppercase', mb: 0.5 }}>Pinned Comment</Typography>
                <Typography sx={{ fontSize: 11, color: 'text.secondary', lineHeight: 1.6 }}>{metadata.pinned_comment}</Typography>
              </Box>
            ) : (
              <Typography sx={{ fontSize: 12, color: IZK.muted }}>Enter a job ID to preview metadata.</Typography>
            )}
            {logLines.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <SectionLabel>Upload Log</SectionLabel>
                <LogPanel lines={logLines} height={180} />
              </Box>
            )}
          </Box>
        </Box>
      </Box>
    </Box>
  )
}
```

- [ ] **Step 2: TypeScript check**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/PublishPage.tsx
git commit -m "feat: neon izakaya — PublishPage topbar + fix Alert import bug"
```

---

## Task 12: AnalyticsPage

**Files:**
- Modify: `src/pages/AnalyticsPage.tsx`

Add topbar. Reskin stat card (US share goes neon amber when > 70%). Country breakdown uses `LinearProgress` — theme handles the amber color. Keep all logic unchanged.

- [ ] **Step 1: Replace `src/pages/AnalyticsPage.tsx` entirely**

```tsx
import { useEffect, useRef, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import TextField from '@mui/material/TextField'
import LinearProgress from '@mui/material/LinearProgress'
import RefreshIcon from '@mui/icons-material/Refresh'
import { analyticsApi } from '../api/analytics'
import { usePipelineContext } from '../store/PipelineContext'
import ErrorAlert from '../components/ErrorAlert'
import SectionLabel from '../components/SectionLabel'
import { IZK } from '../theme'
import type { AnalyticsReport } from '../types'

const POLL_INTERVAL = 4000
const POLL_MAX = 15

export default function AnalyticsPage() {
  const { activeJobId } = usePipelineContext()
  const [jobId, setJobId] = useState(activeJobId ?? '')
  const [report, setReport] = useState<AnalyticsReport | null>(null)
  const [pulling, setPulling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    setJobId(prev => prev || activeJobId || '')
  }, [activeJobId])

  useEffect(() => () => { if (pollRef.current) clearTimeout(pollRef.current) }, [])

  const load = async (id: string) => {
    setError(null)
    try { setReport(await analyticsApi.getReport(id)) }
    catch { setReport(null); setError('No report found. Click Pull Latest to fetch.') }
  }

  useEffect(() => { if (jobId) load(jobId) }, [jobId])

  const handlePull = async () => {
    if (!jobId) return
    setPulling(true); setError(null)
    try {
      await analyticsApi.pull(jobId)
      let attempts = 0
      const poll = () => {
        if (attempts >= POLL_MAX) {
          setPulling(false)
          setError('Analytics pull timed out — try again in a minute.')
          return
        }
        attempts++
        analyticsApi.getReport(jobId)
          .then(r => { setReport(r); setError(null); setPulling(false) })
          .catch(() => { pollRef.current = setTimeout(poll, POLL_INTERVAL) })
      }
      pollRef.current = setTimeout(poll, POLL_INTERVAL)
    } catch { setError('Failed to pull analytics'); setPulling(false) }
  }

  const usPct = report ? Math.round(report.us_share * 100) : 0
  const countries = report?.country_breakdown
    ? Object.entries(report.country_breakdown).sort((a, b) => b[1] - a[1]).slice(0, 6)
    : []

  const flagColor = report?.flag === 'GREEN' ? '#2d6a4f' : report?.flag === 'RED' ? '#c0392b' : '#d4a017'
  const usValueColor = usPct >= 70 ? 'primary.main' : flagColor

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Topbar */}
      <Box sx={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        px: 3, py: '14px', borderBottom: '1px solid', borderColor: IZK.subtleBorder,
        bgcolor: 'background.paper', flexShrink: 0,
      }}>
        <Typography sx={{ fontSize: 13, fontWeight: 600, letterSpacing: '2px', textTransform: 'uppercase', color: 'text.secondary' }}>
          Analytics
        </Typography>
        <Box sx={{ fontSize: 9, letterSpacing: '2px', color: IZK.dim }}>72H REPORT</Box>
      </Box>

      {/* Content */}
      <Box sx={{ flex: 1, overflowY: 'auto', p: 3 }}>
        <Box sx={{ display: 'flex', gap: 1.5, mb: 2, alignItems: 'flex-end' }}>
          <TextField
            label="Job ID"
            size="small"
            value={jobId}
            placeholder="job-20260526-143021"
            onChange={e => setJobId(e.target.value)}
            sx={{ width: 280 }}
          />
          <Button variant="contained" startIcon={<RefreshIcon />} disabled={!jobId || pulling} onClick={handlePull}>
            {pulling ? 'Pulling...' : 'Pull Latest'}
          </Button>
        </Box>

        <ErrorAlert error={error} severity="info" />

        {report && (
          <Box>
            {/* Stat cards row */}
            <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
              {/* US Share card */}
              <Box sx={{
                p: 3, width: 180, flexShrink: 0, textAlign: 'center',
                bgcolor: IZK.card, border: '1px solid',
                borderColor: flagColor + '50',
                borderLeft: '2px solid', borderLeftColor: flagColor,
              }}>
                <Typography sx={{ fontSize: 8, color: IZK.dim, letterSpacing: '2px', textTransform: 'uppercase', mb: 1 }}>
                  US Audience Share
                </Typography>
                <Typography sx={{
                  fontSize: 36, fontWeight: 800, color: usValueColor,
                  textShadow: usPct >= 70 ? '0 0 16px #ff6b3560' : 'none',
                  lineHeight: 1, mb: 0.5,
                }}>
                  {usPct}%
                </Typography>
                <Box sx={{
                  display: 'inline-flex', fontSize: 8, letterSpacing: '1.5px',
                  color: flagColor, border: '1px solid', borderColor: flagColor + '50',
                  px: 1, py: 0.25, mt: 0.5,
                }}>
                  {report.flag}
                </Box>
                <Typography sx={{ fontSize: 9, color: IZK.dim, display: 'block', mt: 0.75 }}>
                  Target: 50%+
                </Typography>
              </Box>

              {/* Notes card */}
              <Box sx={{ flex: 1, bgcolor: IZK.card, border: '1px solid', borderColor: IZK.subtleBorder, p: 2 }}>
                <SectionLabel>Report Details</SectionLabel>
                {report.notes && (
                  <Typography sx={{ fontSize: 12, color: 'text.secondary', lineHeight: 1.6 }}>{report.notes}</Typography>
                )}
              </Box>
            </Box>

            {/* Country breakdown */}
            {countries.length > 0 && (
              <>
                <SectionLabel>Country Breakdown</SectionLabel>
                <Box sx={{ bgcolor: IZK.card, border: '1px solid', borderColor: IZK.subtleBorder }}>
                  {countries.map(([country, share], i) => {
                    const pct = Math.round(share * 100)
                    return (
                      <Box key={country} sx={{
                        display: 'grid', gridTemplateColumns: '140px 52px 1fr',
                        alignItems: 'center', gap: 2, p: '12px 16px',
                        borderBottom: i < countries.length - 1 ? '1px solid' : 'none',
                        borderColor: IZK.subtleBorder,
                      }}>
                        <Typography sx={{ fontSize: 12, color: country === 'US' ? 'text.primary' : 'text.secondary' }}>
                          {country}
                        </Typography>
                        <Typography sx={{ fontSize: 12, fontWeight: 600, color: country === 'US' ? 'primary.main' : 'text.secondary' }}>
                          {pct}%
                        </Typography>
                        <LinearProgress variant="determinate" value={pct} />
                      </Box>
                    )
                  })}
                </Box>
              </>
            )}
          </Box>
        )}
      </Box>
    </Box>
  )
}
```

- [ ] **Step 2: TypeScript check**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/AnalyticsPage.tsx
git commit -m "feat: neon izakaya — AnalyticsPage topbar + stat cards"
```

---

## Task 13: Final Verification

- [ ] **Step 1: Full TypeScript build**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts/frontend
npm run build
```

Expected: build succeeds, zero TypeScript errors, zero import errors.

- [ ] **Step 2: Start dev server and verify visually**

```bash
npm run dev
```

Open `http://localhost:5173`. Verify:
- Sidebar: dark purple-black, amber "Shorts" brand glow, amber dot on active nav item
- Topics page: topbar with uppercase title, neon amber featured TopicCard left border, amber score badge
- Pipeline page: topbar, square step nodes, dark terminal log panel
- Publish page: topbar, dark checklist panel, no crashes on window alert box
- Analytics page: topbar, "72H REPORT" label, amber US share glow if ≥ 70%

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: neon izakaya redesign complete"
```
