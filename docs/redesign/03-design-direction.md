# 03 — Design Direction

**STATUS: APPROVED — built from interview answers (02) + UI audit (01). Source of truth for all visual decisions.**

## Product personality

**Calm focus, set in editorial type.**
Study Planner is the quiet, disciplined companion for serious students. The screen should feel like a well-set page: strong typographic hierarchy, visible structure, generous whitespace, one decisive accent. It rewards attention with clarity — it never shouts.

Personality in one line: *a printed study journal that happens to run live.*

## Direction keywords

Grid · discipline · editorial type · one accent · tabular numbers · calm surfaces · mirrored RTL/LTR

## The three identity pillars

### 1. Typography carries the identity (not decoration)

- **Body:** Vazirmatn (variable, OFL) — Persian-first with full Latin coverage. Self-hosted via `next/font/local`.
- **Display/numerals:** a distinctive display face for stat values, the live timer, and large figures — tabular numerals mandatory. Candidates evaluated in Phase 0 (e.g. a mono-flavored or grotesque display face; final pick documented here).
- Swiss/editorial means: visible baseline discipline, strong size contrast (48px timer vs 12px micro-label), tracking applied to **Latin micro-labels only, never to Persian** (joined script).
- Hierarchy rule: label is quiet and small, the number is the loudest thing on its surface.

### 2. One disciplined accent on editorial neutrals

- Neutral ramp: **paper** (warm-leaning light theme) and **ink** (deep neutral dark theme, not a gray inversion — own tinted ramp per audit B2).
- **Accent: deep ink-blue (draft `#1D4ED8`-family, final value in 04)** — chosen for calm authority; NOT the default indigo-600/SaaS violet, and no gradients.
- Accent appears max once per view-zone: primary CTA, running-timer emphasis, active nav item, or focus ring — never all at once on the same surface.
- Status hues (success/warning/danger) are functional only; priority is marked by typographic weight + edge marks, not pill color spam (fixes audit B3).

### 3. Structure is visible — the grid is part of the design

- Swiss/editorial construction: rules (hairlines) delineate zones; surfaces differentiate by **level, not border-boxes** (fixes audit D1).
- Dashboard: asymmetric two-zone (Q9) — left/start: workspace (RunningSessionBar → task list); right/end: context column (stat strip, weekly chart, course progress). Ruled dividers between zones instead of card moats.
- Running timer (Q8): prominent docked module at the top of the workspace zone — large tabular seconds, quiet session metadata, one stop control. The product's hero moment.
- Motion (Q7): purposeful accents only — timer emphasis, progress-fill on bars, 150–200ms surface transitions. No springs, no celebrations.

## Layout system

- Navigation (Q6): **stronger top bar** — logomark + wordmark (start), nav (center-start), UserMenu + segmented فا/EN control + icon theme toggle (end). Mobile: sheet menu with identity block.
- Desktop dashboard: 12-col grid, two zones (8/4 split), max-w ~1280.
- Mobile: single column in priority order (Q10 equal-first): timer → tasks → stats → courses.
- Radius (Q12): surfaces 12–16px, controls 8px, pills status-only.

## Voice & tone

- Copy: encouraging but factual. Empty state (Q13): single CTA + suggested course ("اولین تکلیفت رو اضافه کن" energy, not dashboards-speak).
- Errors: plain-language, translated (fixes audit E3), always paired with retry.
- No marketing fluff in UI; the product is a tool, copy reflects it.

## Explicitly rejected (anti-patterns)

- Purple/indigo SaaS gradients, glassmorphism, decorative blobs
- Inter-default, emoji icons (☀️/🌙), pill-spam
- Card-per-everything grids, identical layouts across pages
- Giant hero sections, generic dashboard skeletons

## Deliberate exceptions (intentional, not banned)

- The timer module may use the accent at full strength — it is the product's reason to exist.
- Hairline rules may feel "printed" — that is the editorial mood, used consistently.
- One chart may animate its fill — sanctioned by Q7 purposeful accents.

## Success test

A first-time viewer should describe it as *"clean, serious, typographic — nothing like a template."* A Persian-speaking student should feel the app was designed **for their language first**.
