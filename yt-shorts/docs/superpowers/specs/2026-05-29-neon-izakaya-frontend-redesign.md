# Neon Izakaya Frontend Redesign

**Date:** 2026-05-29  
**Scope:** Full frontend redesign — MUI theme, AppShell, all shared components, all pages  
**Stack:** React 19 + MUI v9 + Vite + TypeScript  

---

## Design Concept

Modern Japanese low-light aesthetic — "Neon Izakaya." Deep purple-black backgrounds layered for depth, a single amber-orange neon accent for primary actions and active states, forest green reserved for success/approval, and warm off-white for readable text. No Japanese characters — purely the visual language: moody darkness, glowing edges, editorial typography with uppercase letter-spacing labels.

---

## Color Palette

| Token | Hex | Usage |
|---|---|---|
| `background.default` | `#0e0b14` | App background |
| `background.paper` | `#0b0910` | Sidebar, elevated surfaces |
| `background.card` | `#130f1e` | Cards, panels |
| `background.terminal` | `#080610` | Log panel |
| `primary.main` | `#ff6b35` | Neon amber — active states, primary buttons, accents |
| `secondary.main` | `#2d6a4f` | Forest green — success, approve actions only |
| `text.primary` | `#e8ddd0` | Warm off-white — headings, card titles |
| `text.secondary` | `#c4b4a4` | Body text |
| `text.muted` | `#4a3f5a` | Inactive nav, meta labels |
| `text.dim` | `#3a3050` | Deepest inactive text |
| `divider` | `#2a2040` | Borders, separators |
| `divider.subtle` | `#1a1428` | Very subtle borders |
| `error.main` | `#c0392b` | Error states |
| `warning.main` | `#d4a017` | Warning states |

---

## Typography

- **Font:** System UI stack (keep existing) — no new font dependency
- **Page titles:** 13px, 700 weight, `letterSpacing: 2px`, `textTransform: uppercase`, `color: text.secondary`
- **Section labels:** 9px, `letterSpacing: 3px`, `textTransform: uppercase`, `color: primary.main` at 60% opacity, with a neon gradient line trailing to the right
- **Card titles:** 12–13px, `color: text.primary` (active) or `text.muted` (inactive)
- **Meta/badge text:** 8–9px, `letterSpacing: 1–2px`, `textTransform: uppercase`
- **Log panel:** `'Courier New', monospace`, 11px, `color: text.dim`

---

## Files Changed

### Modified
- `frontend/src/theme/index.ts` — full MUI palette + component overrides
- `frontend/src/layouts/AppShell.tsx` — sidebar + per-page topbar
- `frontend/src/components/SectionLabel.tsx`
- `frontend/src/components/StatusBadge.tsx`
- `frontend/src/components/LogPanel.tsx`
- `frontend/src/components/StepTracker.tsx`
- `frontend/src/components/TopicCard.tsx`
- `frontend/src/components/ErrorAlert.tsx`
- `frontend/src/pages/TopicsPage.tsx`
- `frontend/src/pages/PipelinePage.tsx`
- `frontend/src/pages/PublishPage.tsx`
- `frontend/src/pages/AnalyticsPage.tsx`

---

## Theme (`theme/index.ts`)

Full MUI theme with:
- Palette as per color table above
- `MuiPaper`: no background image, `background.paper` default, sharp corners (`borderRadius: 0`)
- `MuiButton`:
  - `contained` variant: neon amber fill, no box shadow, uppercase, letter-spacing 2px, sharp corners; hover brightens slightly
  - `outlined` variant: neon amber border + text, transparent background; hover adds subtle amber glow background
  - `text` variant: amber text, no border
  - Disabled state: dim purple-gray, no glow
- `MuiChip`: sharp corners, `background.card` fill, `divider` border, small font
- `MuiTextField`: sharp corners, `divider` border color, amber focus ring (no glow), `background.card` fill
- `MuiCheckbox`: amber accent when checked
- `MuiLinearProgress`: `background.card` track, amber fill
- `MuiDivider`: `divider.subtle` color
- `MuiDrawer`: `background.paper` fill, `divider.subtle` right border

---

## AppShell (`layouts/AppShell.tsx`)

### Sidebar (permanent drawer, 200px)

- **Brand area (top):**
  - "SHORTS" in 11px, 700 weight, 5px letter-spacing, amber neon color with `textShadow: '0 0 10px #ff6b3570'`
  - "YT Automation" in 9px, `text.dim`, 2px letter-spacing
  - Bottom border: `divider.subtle`

- **Nav items:**
  - Inactive: `text.muted`, no border
  - Active: `text.primary`, `borderLeft: '2px solid primary.main'`, `background: linear-gradient(90deg, #ff6b3510, transparent)`
  - Active icon/dot: amber color

- **Footer (bottom of sidebar):**
  - Small text: `text.dim`, e.g. `"EST · UTC−5"` (static)

### Main area

- **Per-page topbar** (added inside `<Box component="main">`):
  - Left: page title (uppercase, letter-spaced)
  - Right: contextual counter badge (e.g. "10 QUEUED") in amber tint
  - Bottom border: `divider.subtle`
  - Background: `background.paper`

- **Content area:** `padding: 24px`, `background.default`

---

## Components

### `SectionLabel`
- 9px, uppercase, `letterSpacing: 3px`, `color: primary.main` at 60% opacity
- Trailing horizontal gradient line: `linear-gradient(90deg, primary.main at 20%, transparent)`
- Displayed as a flex row: label + line

### `StatusBadge`
- Sharp-cornered pill (no `borderRadius`)
- Border + text color driven by status:
  - `pending` → amber border/text at 50–60% opacity
  - `approved` → green border/text
  - `queued` → dim purple
  - `running` → amber, pulsing opacity animation
  - `complete` → green
  - `failed` → red
- 8px, `letterSpacing: 1.5px`, uppercase

### `LogPanel`
- Background: `background.terminal` (`#080610`)
- Border: `divider.subtle`
- Monospace 11px font
- Timestamp prefix: `text.dim`
- Log line coloring by prefix:
  - Lines starting with `✓` or `OK`: `secondary.main` (green)
  - Lines starting with `→` or `INFO`: amber at 60%
  - Lines starting with `✗` or `ERROR`: `error.main`
  - Default: `text.dim`
- Scrolls to bottom on new lines (existing behavior preserved)

### `StepTracker`
- Step nodes: 28×28px, sharp corners, `background.card` fill, `divider` border
  - Completed: amber border at 50%, amber checkmark text, faint amber background
  - Active: full amber border + amber glow (`boxShadow: 0 0 8px primary.main + 40`)
  - Pending: `divider` border, `text.dim`
- Connector lines:
  - Completed segment: amber gradient (`linear-gradient(90deg, amber40, dim)`)
  - Pending: `divider.subtle`
- Step labels below nodes: 8px, `text.dim` (pending) or `text.muted` (active/done)

### `TopicCard`
- Background: `background.card`
- Border: `divider`
- Featured/selected: `borderLeft: '2px solid primary.main'`, deeper card background, subtle amber box-shadow inset
- Score badge: 32×32px, sharp corners
  - High score (8–10): amber border + amber text + glow
  - Mid score (6–7): dim border + `text.dim`
- Title: `text.primary` (featured) or `text.muted` (inactive)
- Meta line: 8px uppercase, amber opacity (featured) or `text.dim`
- Status pill: right-aligned `StatusBadge`

### `ErrorAlert`
- Background: `#1a0a0a`
- Border: `error.main` at 40% opacity, left accent bar at full `error.main`
- Text: `#e8c4c4` (warm red-white)
- Close button: `error.main`

---

## Pages

All pages follow a consistent structure:
1. **Topbar** (in AppShell, driven by route): page title left, counter/status badge right
2. **Content area** with `SectionLabel` groupings
3. No free-floating `Typography variant="h6"` headings — the topbar handles page identity

### TopicsPage
- Topbar: "TOPICS" left, `"{n} QUEUED"` badge right
- Pending section: `SectionLabel` + vertical list of `TopicCard`
- Queue section: `SectionLabel` + vertical list of `TopicCard` (approved style)
- Action row: "Generate Topics" (amber outlined button) + "Approve Selected" (green outlined button)
- Empty states: dim centered text ("No topics yet. Generate some.")

### PipelinePage
- Topbar: "PIPELINE" left, job status badge right (`StatusBadge` for running/idle/complete)
- Job card: `background.card`, sharp border, job ID in monospace, status + description; "Run Pipeline" amber contained button
- Two-column grid: Steps (StepTracker) | Live Log (LogPanel)
- Live indicator: `"● LIVE"` in amber with pulse animation when running

### PublishPage
- Topbar: "PUBLISH" left, next-window timestamp right (dim text)
- Job ID input: `TextField` styled per theme
- Gate checklist: `Checkbox` + label rows in `background.card` panel
- Metadata preview: `background.card` panel, monospace values
- Upload button: amber contained, disabled until all checks pass
- Upload window info: green text for next window time

### AnalyticsPage
- Topbar: "ANALYTICS" left, "72H REPORT" label right
- Job ID + pull button row
- Stat cards row: 3 cards side-by-side (`background.card`), large value, small label, delta in green
  - US Share stat: value in amber neon if > 70%
- Country breakdown: `LinearProgress` bars per country, amber fill, `text.muted` labels
- Flag badge: `StatusBadge`-style — GREEN/YELLOW/RED

---

## Implementation Notes

- **No new dependencies.** All styling via MUI `sx` prop, theme `components` overrides, and inline styles for glow effects (since MUI theme doesn't support `textShadow` directly on all tokens).

- **Non-standard palette tokens.** `background.card` (`#130f1e`), `background.terminal` (`#080610`), `text.muted` (`#4a3f5a`), `text.dim` (`#3a3050`), and `divider.subtle` (`#1a1428`) are not standard MUI palette slots. Define them as named constants exported from `theme/index.ts` (e.g. `export const IZK = { card: '#130f1e', terminal: '#080610', muted: '#4a3f5a', dim: '#3a3050', subtleBorder: '#1a1428' } as const`) and import this object in components that need these values. Do not attempt MUI module augmentation — it adds complexity for no gain here.

- **Glow effects** use `boxShadow` and `textShadow` inline on the few elements that need it (brand name, active score badge, primary button). Keep these minimal — overuse kills the aesthetic.

- **Sharp corners everywhere.** Set `shape: { borderRadius: 0 }` in the theme. The square edge is part of the izakaya industrial feel.

- **No animations except:** `StatusBadge` running state (opacity pulse, `1.5s ease-in-out infinite`) and the amber glow hover on buttons (`transition: 0.15s`).

- **PageHeader pattern.** AppShell renders the sidebar and a `<Box component="main">` that contains `<Outlet />`. Each page renders its own topbar as the first element inside its JSX — a `<Box>` with `display: flex`, `justifyContent: space-between`, `borderBottom`, `background.paper`, and `padding: '14px 24px'`. This avoids prop-drilling a counter/badge through AppShell and keeps each page self-contained. The topbar is NOT a shared component — each page owns its header.
