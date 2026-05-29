# Geometric Background Shapes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 7 floating geometric shapes (rotating squares, drifting diamonds, glowing dot, line fragment) to the main content area background of the Neon Izakaya UI.

**Architecture:** One new purely-decorative component (`GeometricBackground`) placed absolutely behind `<Outlet />` in `AppShell`. Each shape is an absolutely-positioned MUI Box with its own CSS keyframe animation defined inline via the `sx` prop — same pattern used for the pulse animation in `StepTracker`. No new dependencies.

**Tech Stack:** React 19, MUI v9, TypeScript. Working directory: `E:/digital-sorcery/master-planner/yt-shorts/frontend`.

---

## File Map

| File | Change |
|---|---|
| `src/components/GeometricBackground.tsx` | **Create** — 7 absolutely-positioned shape Boxes, each with unique inline keyframe animation |
| `src/layouts/AppShell.tsx` | **Modify** — import `GeometricBackground`, add `position: relative` to main Box, render component behind `<Outlet />` |

---

## Task 1: GeometricBackground Component

**Files:**
- Create: `frontend/src/components/GeometricBackground.tsx`

- [ ] **Step 1: Create `frontend/src/components/GeometricBackground.tsx`**

```tsx
import Box from '@mui/material/Box'

export default function GeometricBackground() {
  return (
    <Box sx={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden' }}>

      {/* S1 — amber rotating square */}
      <Box sx={{
        position: 'absolute', top: '12%', left: '78%',
        width: 28, height: 28,
        border: '1px solid #ff6b35',
        opacity: 0.45,
        animation: 'izk-s1 7s ease-in-out infinite',
        '@keyframes izk-s1': {
          '0%':   { transform: 'translateY(0) rotate(0deg)' },
          '50%':  { transform: 'translateY(-18px) rotate(180deg)' },
          '100%': { transform: 'translateY(0) rotate(360deg)' },
        },
      }} />

      {/* S2 — amber drifting diamond */}
      <Box sx={{
        position: 'absolute', top: '48%', left: '62%',
        width: 36, height: 36,
        border: '1px solid #ff6b35',
        opacity: 0.30,
        animation: 'izk-s2 11s ease-in-out infinite 1.2s',
        '@keyframes izk-s2': {
          '0%,100%': { transform: 'translate(0, 0) rotate(45deg)' },
          '33%':     { transform: 'translate(8px, -12px) rotate(60deg)' },
          '66%':     { transform: 'translate(-6px, 8px) rotate(30deg)' },
        },
      }} />

      {/* S3 — green reverse-rotating square */}
      <Box sx={{
        position: 'absolute', top: '72%', left: '85%',
        width: 20, height: 20,
        border: '1px solid #2d6a4f',
        opacity: 0.35,
        animation: 'izk-s3 9s ease-in-out infinite 2.1s',
        '@keyframes izk-s3': {
          '0%':   { transform: 'translateY(0) rotate(0deg)' },
          '50%':  { transform: 'translateY(-14px) rotate(-180deg)' },
          '100%': { transform: 'translateY(0) rotate(-360deg)' },
        },
      }} />

      {/* S4 — large slow green diamond */}
      <Box sx={{
        position: 'absolute', top: '30%', left: '88%',
        width: 48, height: 48,
        border: '1px solid #2d6a4f',
        opacity: 0.25,
        animation: 'izk-s4 14s ease-in-out infinite 0.7s',
        '@keyframes izk-s4': {
          '0%,100%': { transform: 'translate(0, 0) rotate(45deg)' },
          '50%':     { transform: 'translate(-10px, -16px) rotate(60deg)' },
        },
      }} />

      {/* S5 — glowing amber dot */}
      <Box sx={{
        position: 'absolute', top: '20%', left: '70%',
        width: 7, height: 7,
        borderRadius: '50%',
        bgcolor: '#ff6b35',
        opacity: 0.60,
        boxShadow: '0 0 10px #ff6b35',
        animation: 'izk-s5 5s ease-in-out infinite 3.5s',
        '@keyframes izk-s5': {
          '0%,100%': { transform: 'translateY(0) scale(1)',    opacity: 0.60 },
          '50%':     { transform: 'translateY(-8px) scale(1.3)', opacity: 0.40 },
        },
      }} />

      {/* S6 — amber line fragment */}
      <Box sx={{
        position: 'absolute', top: '62%', left: '75%',
        width: 32, height: 1,
        bgcolor: '#ff6b35',
        opacity: 0.20,
        animation: 'izk-s6 12s ease-in-out infinite 1.8s',
        '@keyframes izk-s6': {
          '0%,100%': { transform: 'rotate(45deg) translateX(0)' },
          '50%':     { transform: 'rotate(65deg) translateX(8px)' },
        },
      }} />

      {/* S7 — large faint slowly-rotating filled square */}
      <Box sx={{
        position: 'absolute', top: '55%', left: '58%',
        width: 56, height: 56,
        bgcolor: '#ff6b35',
        opacity: 0.10,
        animation: 'izk-s7 18s linear infinite 0.3s',
        '@keyframes izk-s7': {
          '0%':   { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
      }} />

    </Box>
  )
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts/frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts && git add frontend/src/components/GeometricBackground.tsx && git commit -m "feat: add GeometricBackground component with 7 animated shapes"
```

---

## Task 2: Wire into AppShell

**Files:**
- Modify: `frontend/src/layouts/AppShell.tsx`

The current `<Box component="main">` (line 89–91) is:
```tsx
<Box component="main" sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', bgcolor: 'background.default' }}>
  <Outlet />
</Box>
```

- [ ] **Step 1: Update `frontend/src/layouts/AppShell.tsx`**

Add the import after the existing `IZK` import line (line 8):
```tsx
import GeometricBackground from '../components/GeometricBackground'
```

Replace the `<Box component="main">` block (lines 89–91) with:
```tsx
<Box component="main" sx={{ flex: 1, position: 'relative', overflow: 'hidden', bgcolor: 'background.default' }}>
  <GeometricBackground />
  <Box sx={{ position: 'relative', zIndex: 1, height: '100%', display: 'flex', flexDirection: 'column' }}>
    <Outlet />
  </Box>
</Box>
```

The full updated file should be:

```tsx
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import Box from '@mui/material/Box'
import Drawer from '@mui/material/Drawer'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemText from '@mui/material/ListItemText'
import Typography from '@mui/material/Typography'
import { IZK } from '../theme'
import GeometricBackground from '../components/GeometricBackground'

const W = 200
const NAV = [
  { label: 'Topics', path: '/' },
  { label: 'Pipeline', path: '/pipeline' },
  { label: 'Publish', path: '/publish' },
  { label: 'Analytics', path: '/analytics' },
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
                  slotProps={{
                    primary: {
                      sx: {
                        fontSize: 12,
                        letterSpacing: '0.5px',
                        color: active ? 'text.primary' : IZK.muted,
                      },
                    },
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

      <Box component="main" sx={{ flex: 1, position: 'relative', overflow: 'hidden', bgcolor: 'background.default' }}>
        <GeometricBackground />
        <Box sx={{ position: 'relative', zIndex: 1, height: '100%', display: 'flex', flexDirection: 'column' }}>
          <Outlet />
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
cd E:/digital-sorcery/master-planner/yt-shorts && git add frontend/src/layouts/AppShell.tsx && git commit -m "feat: render GeometricBackground in main content area"
```

---

## Final Verification

- [ ] **Start dev server and verify visually**

```bash
cd E:/digital-sorcery/master-planner/yt-shorts/frontend && npm run dev
```

Open `http://localhost:5173`. Verify:
- Shapes are visible in the content area behind page content (Topics, Pipeline, Publish, Analytics)
- Sidebar has no shapes — stays clean
- Content (cards, buttons, log panels) is fully clickable and readable
- Shapes animate continuously — rotating squares, drifting diamonds, pulsing dot, slow filled square
- No layout breakage (pages still scroll, topbars still visible)
