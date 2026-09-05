# 04 — Design System

**STATUS: DRAFT SKELETON — tokens depend on direction (03) which is blocked on the interview.**

Structure is fixed now; values land after direction is approved. Frontend implements this via Tailwind v4 `@theme` tokens in `globals.css` + CSS custom properties (dark mode already on `class` strategy).

**Phase 0 note:** token layer + fonts are now implemented (`globals.css` + `app/layout.tsx` + `public/fonts/`). Semantic tokens currently map to the *existing* palette (zero visual delta); later phases shift values without touching component classes. The logical-property ESLint rule is live at `warn` level.

## 1. Typography

| Role | Token | Font | Notes |
|------|-------|------|-------|
| Body FA | `--font-sans` | **Vazirmatn variable (100–900), self-hosted OFL** | covers fa + latin |
| Display/numerals | `--font-display` | **Space Grotesk variable (300–700), self-hosted OFL** | stat values, timer, dates |
| Code/keys | `--font-mono` | Space Grotesk (same face) | course keys |

Scale (draft): `12 / 13 / 14 / 16 / 18 / 22 / 28 / 36 / 48`. Timer + stat values get `tabular-nums`. Line-height: 1.5 body, 1.1 display. Weights: 400/500/600/700 only.

_FA typography rules:_ no faux-bold with Tahoma fallback; letter-spacing/tracking **disabled** for Persian text (tracking breaks joined script — apply only to LTR micro-labels).

## 2. Color

Three-layer tokens:

- **Primitives** — custom neutral ramp + 1–2 accent families + semantic hues (values post-interview).
- **Semantic** — `--color-bg, --color-surface-1..3, --color-border-subtle/strong, --color-text-primary/secondary/muted, --color-accent, --color-accent-fg, --color-success/warning/danger, --color-focus`.
- **Component** — mapped in `@theme` (e.g. `--color-background: var(--color-bg)`).

Light + dark defined as separate ramps (dark is not an inversion — own tinted surfaces per audit B2). Contrast floor: WCAG AA for all text; AAA for body on long-form surfaces.

Accent usage rule: **one dominant accent zone per view**. Priority/status hues never reuse the accent.

## 3. Spacing, radius, borders, elevation

- Spacing scale: Tailwind default 4px base; page gutters 16/24/32; section gaps 24/40.
- Radius vocabulary (draft, Q12 pending): surfaces `12–16`, controls `8`, pills only for status. No full-rounded cards.
- Borders: 1px `border-subtle` default; strong only for interactive boundaries. Borders are not the primary elevation device.
- Elevation: light = 2 shadow steps max (rest/hover); dark = surface-color steps, shadows only for true overlays (dialogs, sheets).

## 4. Focus & interaction states

- Focus: 2px `--color-focus` ring, 2px offset, `:focus-visible` only. Never remove without replacement.
- Hover: surface tint step, 100–150ms. Press: scale 0.98 on large targets only, 80ms.
- Disabled: opacity + `cursor-not-allowed`; no color-only indication (pair with icon).
- Loading: buttons swap label→spinner + keep width (min-width reservation); no layout shift.

## 5. Motion

- Durations: instant 80ms / fast 150ms / base 200ms / slow 320ms.
- Easing: standard `ease-out` for enters, `ease-in` for exits; springs only if interview picks expressive level (Q7b/c).
- Rules: no motion for text; respect `prefers-reduced-motion` (global disable); timer pulse and progress fill are the two sanctioned continuous animations (pending Q8).

## 6. Iconography

Lucide (Radix-compatible, tree-shaken). Stroke width 1.75. Sizes: 16 (inline), 20 (controls), 24 (nav). Icons always paired with accessible name; decorative icons `aria-hidden`.

## 7. Layout & breakpoints

- Breakpoints: `sm 640 / md 768 / lg 1024 / xl 1280 / 2xl 1440`.
- App container: TBD by C4 decision (asymmetric wide vs focused).
- Grid: dashboard uses a 12-col grid with defined zones (workspace / context column) once Q9 answers land.

## 8. RTL/LTR system

- All spacing/positioning via logical properties (`ps/pe/ms/me/start/end`); `pl/pr/ml/mr/left/right` banned in app code — enforce with ESLint rule (planned migration step).
- Icons with direction (arrows, progress chevrons) flip via `[dir]` variant or are direction-neutral.
- Numbers: Latin digits in LTR contexts, locale-aware digits via `Intl` in FA (current `format.ts` behavior kept).
- Charts: axis direction follows `dir`; temporal axes stay LTR-order with localized weekday labels (audit G2 fix).

## 9. Component states matrix

Every interactive primitive ships: default / hover / focus-visible / active / disabled / loading. Forms additionally: invalid (message via `role=alert`) / valid / hint. Data displays: empty / loading (skeleton) / error (retry) / populated.

## 10. shadcn/ui adoption map

| shadcn primitive | Replaces | Product skin |
|---|---|---|
| Dialog + AlertDialog | TaskFormDialog, ConfirmDialog | token surfaces, radius, motion |
| Select / Combobox | native selects (course, priority) | keep native for mobile-first lists if Q10 favors it |
| DropdownMenu | header user menu (new) | avatar block |
| Tabs | (future) stats views | — |
| Tooltip | icon buttons | — |
| Checkbox | task toggle | custom completion affordance |
| Sonner/Toast | inline action errors (supplement) | — |

shadcn provides behavior/a11y; **all visual classes come from our tokens — no default shadcn gray/`ring` look**.
