# Geometric Background Shapes Design

**Date:** 2026-05-29
**Scope:** Add floating geometric background shapes to the main content area of the Neon Izakaya UI

---

## Concept

Slow-drifting geometric shapes — rotating squares, diamonds, a glowing dot, a line fragment — rendered behind all page content in the main content area. Shapes use the Neon Izakaya palette at 30–50% opacity. The sidebar stays completely clean. The effect adds depth and visual energy without competing with content.

Style reference: Option C "Active Fragments" from brainstorming — rotating squares, drifting diamonds, a neon glowing dot, amber and green colors, continuous slow animation.

---

## Architecture

**New file:** `frontend/src/components/GeometricBackground.tsx`
- Absolutely positioned container (`inset: 0`, `pointerEvents: none`, `zIndex: 0`)
- Renders 7 shape elements, each with its own CSS keyframe animation via MUI `sx`
- No props needed — purely decorative, no external data
- Uses `IZK` constants from `../theme`

**Modified file:** `frontend/src/layouts/AppShell.tsx`
- Import `GeometricBackground`
- Inside `<Box component="main">`, wrap content in a `position: relative` Box
- Place `<GeometricBackground />` as a sibling to `<Outlet />` inside that wrapper, rendered first (behind)

---

## Shapes

7 shapes total, all in the right half of the content area (away from where the sidebar ends):

| Shape | Type | Color | Opacity | Size | Animation |
|---|---|---|---|---|---|
| S1 | Rotating square (border only) | `#ff6b35` | 45% | 28×28px | Rotate 0→360°, drift up/down, 7s |
| S2 | Rotating diamond (border only) | `#ff6b35` | 30% | 36×36px | Rotate 45→225°, drift, 11s |
| S3 | Rotating square (border only) | `#2d6a4f` | 35% | 20×20px | Rotate 0→-360°, float, 9s |
| S4 | Drifting diamond (border only) | `#2d6a4f` | 25% | 48×48px | Slow drift, slight rotate, 14s |
| S5 | Filled dot (circle) | `#ff6b35` | 60% | 7×7px | Scale pulse + drift, 5s, glow |
| S6 | Line fragment | `#ff6b35` | 20% | 32px × 1px | Rotate + drift, 12s |
| S7 | Rotating square (filled) | `#ff6b35` | 10% | 56×56px | Very slow rotate, 18s |

**Positioning** (all `position: absolute`, `left` values are percentages of the main content width — they all sit in the 55%–92% range so they're well clear of the sidebar):

| Shape | top | left |
|---|---|---|
| S1 | 12% | 78% |
| S2 | 48% | 62% |
| S3 | 72% | 85% |
| S4 | 30% | 88% |
| S5 | 20% | 70% |
| S6 | 62% | 75% |
| S7 | 55% | 58% |

Each shape has a unique `animationDelay` (0–3.5s) so they never move in sync.

---

## Animation Keyframes

Three named keyframe patterns, mixed across shapes:

**`@keyframes floatRotate`** — rotate full 360° while drifting vertically ±15–20px:
```
0%   { transform: translateY(0)     rotate(0deg);   opacity: [base] }
50%  { transform: translateY(-18px) rotate(180deg); opacity: [base * 0.6] }
100% { transform: translateY(0)     rotate(360deg); opacity: [base] }
```

**`@keyframes floatDrift`** — translate diagonally ±10–15px, slight rotate:
```
0%,100% { transform: translate(0, 0)       rotate(45deg) }
33%     { transform: translate(8px, -12px) rotate(60deg) }
66%     { transform: translate(-6px, 8px)  rotate(30deg) }
```

**`@keyframes pulseDot`** — scale pulse + vertical drift for the filled dot:
```
0%,100% { transform: translateY(0)    scale(1);   opacity: 0.6 }
50%     { transform: translateY(-8px) scale(1.3); opacity: 0.4 }
```

---

## Implementation Notes

- All animations use `ease-in-out infinite` — never jarring, never stop.
- Keyframes are defined inline via MUI `sx` `@keyframes` syntax (same pattern as `StepTracker`'s pulse).
- `pointerEvents: none` on the container ensures shapes never block clicks.
- `overflow: hidden` on the `<Box component="main">` wrapper clips shapes that drift outside bounds.
- No `will-change` or GPU hints needed — CSS transform animations are already composited by default.
- No tests needed — purely decorative, no logic.

---

## Files Changed

| File | Change |
|---|---|
| `frontend/src/components/GeometricBackground.tsx` | **Create** — new decorative component |
| `frontend/src/layouts/AppShell.tsx` | **Modify** — import + render `GeometricBackground` behind `Outlet` |
