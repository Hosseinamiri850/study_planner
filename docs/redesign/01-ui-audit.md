# 01 — UI Audit

_Live browser inspection of the Next.js SPA (frontend/) at commit 9f018e5, 2026-09-03._
_Inspected: login, register, dashboard, profile. Desktop 1440x900 + mobile 375x812. RTL (fa, default) + LTR (en). Dark theme (default)._

## Product context

- Two UIs exist today: legacy Jinja/Bootstrap (templates/) and the Next.js 15 SPA (frontend/). The SPA is the migration target per `.ai/PLAN_REACT_MIGRATION.md`. This redesign covers the **SPA**.
- The SPA is functionally complete but visually generic. It reads as "starter template", not product.

---

## Findings

Each finding: problem → why it matters → direction → priority.

### A. Typography

**A1. System font stack, no brand typeface. [P0]**
- Body computes to `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, ...`. Persian text renders in the OS fallback (Tahoma/Segoe UI), which is ugly and inconsistent across platforms.
- No Persian-optimized face (e.g. Vazirmatn / IRANSansX) and no display face for numerals/headers. The app's primary language is Persian — this is the single biggest "generic" tell.
- Direction: self-host a Persian-first variable font (Vazirmatn covers fa + Latin) + one distinctive display/numeric face for stats and timers. `next/font/local`.

**A2. Weak type scale. [P0]**
- h1 = 20px, stat values = 24px, body = 14–16px. Nearly everything sits within 2 sizes; no hierarchy. The dashboard greeting (the page's anchor) competes with a tertiary label.
- Direction: proper scale (12/13/14/16/18/22/28/36+), a real display size for the running timer and stat values, tighter label-vs-value contrast (uppercase tracking-out micro labels vs. large tabular numerals).

### B. Color & theming

**B1. Default Tailwind slate + indigo. [P1]**
- Palette is literally `bg-slate-50`, `bg-indigo-600` — the most common AI-generated combo. Zero brand identity, indigo used for nav-active, links, buttons, chart bars, progress bars indiscriminately.
- Direction: replace with a semantic token layer (`--color-bg/surface/border/accent/muted...`) over a custom primitive palette. Reserve accent for 1–2 surfaces per view.

**B2. Dark mode is a flat inversion. [P1]**
- Dark = slate-900 + slate-800 cards + slate-700 borders. No depth, no tint, same border-heavy construction as light. Large empty areas feel dead.
- Direction: dark theme gets its own tinted surface ramp (not gray inversion), elevation via surface color steps instead of borders.

**B3. Semantic colors only in badges/alerts. [P2]**
- Priority (low/med/high), running-session state, and completion all rely on tiny pill backgrounds. States don't read at a glance in the task list.
- Direction: status as design language — priority edge/rail marks, running state as a live timer treatment, not just a pulsing dot.

### C. Layout & density

**C1. Dashboard has no hierarchy. [P0]**
- Flow: greeting + button → 4 equal stat cards → 2 equal chart cards → task list. Four siblings, equal weight. Nothing tells the eye where to land.
- Direction: one dominant zone (this week's progress / running session), supporting stats compressed into a single row strip, charts de-emphasized or merged.

**C2. Stat cards are 4 identical boxes. [P1]**
- Generic "cards row" pattern. Zero visual differentiation between "today" (immediate) and "month" (context).
- Direction: collapse to one dense stat strip (label-over-value, no boxes) or a single hero metric + inline deltas.

**C3. Course progress list is unbounded noise. [P0]**
- All 14 seeded courses render as `0/0 · ۰٫۰ ساعت` rows. Zero-signal rows dominate the second half of the dashboard.
- Direction: hide/deprioritize zero-activity courses, sort by real activity, cap visible rows with "show all", or move to courses page. Progress bars need actual hour data to be meaningful.

**C4. Max-w-6xl container but content only fills half. [P2]**
- At 1440px the content is a narrow centered column; whitespace is unstructured.
- Direction: either a true wide layout with asymmetric zones (timer/tasks primary, charts secondary column) or narrower focused container — decide, don't split the difference.

### D. Components & patterns

**D1. Card-per-everything. [P1]**
- Every unit — stat, chart, task row, form section, profile block — is the same `rounded-xl border bg-white p-4`. Rhythm without meaning.
- Direction: define surface levels: page, panel, inset. Tasks could be list rows on a shared surface, not boxed islands.

**D2. Hand-rolled dialogs/modals. [P1]**
- `TaskFormDialog` and `ConfirmDialog` are custom portal divs. No focus trap in TaskFormDialog, no scroll lock, no portal-managed focus restore, Esc handling duplicated.
- Direction: adopt shadcn/ui Dialog (Radix) for accessibility + animation primitives; restyle to product skin.

**D3. Buttons: 4 flat variants, no size system. [P2]**
- Sizes hacked inline (`px-2 py-1 text-xs` everywhere in tasks-panel). Icon buttons are text buttons.
- Direction: variant × size matrix in the button primitive; icon-button variant; consistent density.

**D4. Native `<select>` for course/priority/language. [P2]**
- Unstylable, inconsistent cross-OS, RTL dropdown arrow quirks; language switcher is a bare select in the header.
- Direction: shadcn Select/Combobox; language switcher becomes a segmented control (فا/EN).

**D5. Chart is a div-bar mock. [P2]**
- WeeklyChart = 7 divs with `title` tooltips. No axis, no gridlines, no hover state, no empty-vs-data distinction.
- Direction: recharts or shadcn chart with proper a11y table fallback; match design tokens.

### E. States

**E1. Empty states are text-in-a-box. [P1]**
- `EmptyState` = dashed border + 2 lines + button. No illustration, no product personality, no guidance toward first success (which course to pick).
- Direction: first-run empty state is an onboarding moment — suggest course, seed example, show the one CTA that matters.

**E2. Loading = pulse skeletons + spinner. [P2]**
- Functional but generic. Spinner for auth gate, skeletons elsewhere, no route-level loading rhythm.
- Direction: keep skeletons but shape them to actual content; unify via one LoadingSurface per route.

**E3. Error states = raw API strings in red alert. [P1]**
- `errorMessage()` surfaces backend English strings ("Network error — check your connection.") untranslated in the fa UI; retry is a small ghost button inside the alert.
- Direction: error component with icon + translated message + retry; i18n the client-side error strings (gap in locales).

### F. Navigation & shell

**F1. Header is anonymous. [P1]**
- Logo = app name in indigo text. No brand mark, no identity. User's name floats as plain text; theme toggle is an emoji (☀️/🌙) button.
- Direction: wordmark + logomark; avatar/menu for identity; theme toggle as icon component, not emoji.

**F2. Mobile nav drops identity + controls into a cramped row. [P2]**
- Menu panel stuffs nav links + fullname + language select + theme + logout in one column; fine functionally, poor visually.
- Direction: mobile menu as proper sheet; identity block with avatar; controls grouped.

**F3. Admin link is bare text nav item. [P2]**
- Admin area entered without any "elevated zone" signal. (Non-admin users bounce via `router.replace` — no 403 page exists.)
- Direction: admin zone gets distinct surface treatment (accent rail / darker band); build 403 route for SPA parity.

### G. i18n / RTL

**G1. Logical properties used correctly — no regressions found.** Good baseline; keep and enforce (lint rule).
**G2. Chart week labels are LTR-ordered numerals inside RTL page (`28/8 … 3/9`).** Acceptable (temporal axis), but needs deliberate axis labeling (weekday initials per locale) rather than raw day/month fragments. [P2]
**G3. Locale keys missing for client-side strings** (`errors.ts` messages). [P1] — see E3.

### H. Accessibility

**H1. Focus management in hand-rolled dialogs** (no trap, no initial focus except ConfirmDialog's confirm button, no restore). [P0] — fix via Radix Dialog.
**H2. Toggle checkbox is a styled button with aria-pressed** — acceptable, but native semantics (input+label or Radix Checkbox) are cleaner. [P2]
**H3. Emoji theme toggle has aria-label — OK.** Contrast of `slate-400` placeholders on white is borderline. [P3]

---

## Priority summary

| # | Finding | Pri |
|---|---------|-----|
| 1 | Typography: no brand/Persian font, flat scale (A1, A2) | P0 |
| 2 | Dashboard hierarchy: stat boxes + 14 zero courses (C1, C3) | P0 |
| 3 | Dialog a11y + focus (H1, D2) | P0 |
| 4 | Color identity: default slate/indigo, flat dark mode (B1, B2) | P1 |
| 5 | Card-per-everything, no surface system (D1, C2) | P1 |
| 6 | Empty states, error i18n (E1, E3) | P1 |
| 7 | Header/brand identity, emoji toggle (F1) | P1 |
| 8 | Buttons/selects/chart primitives (D3, D4, D5) | P2 |
| 9 | Mobile nav, admin zone, 403 (F2, F3) | P2 |
| 10 | Axis labels, checkbox semantics, contrast (G2, H2, H3) | P2–P3 |

## What already works (keep)

- RTL logical properties everywhere (`ps-/pe-/ms-/me-`, `dir` flip at root).
- Server-backed theme + localStorage mirror; silent refresh auth with in-memory access token + httpOnly cookie (don't touch).
- Pagination, retry affordances, running-session restore after reload.
- Typed API client mirroring the Flask contract; locale files single-sourced from backend.
