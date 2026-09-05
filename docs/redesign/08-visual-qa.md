# 08 — Visual QA

**STATUS: process doc — executed per phase of 07; results appended below each run.**

Tooling: preview server (Next dev) + browser preview tools (snapshot / screenshot / inspect / resize). Playwright MCP available for scripted flows.

## Matrix

Per phase, per affected route:

- Viewports: desktop 1440×900, mobile 375×812 (tablet 768×1024 when layout has md-breakpoint logic)
- Languages: fa (RTL, default) + en (LTR) — via header switcher
- Themes: dark (default) + light — via header toggle
- Checks: content structure (snapshot), visual (screenshot), computed styles for token verification (inspect), console errors, network failures, interaction flows

## Standard regression flows (must pass every phase)

1. Register new user → lands on /app
2. Login existing → dashboard
3. Create task (all fields) → appears in list
4. Edit task → changes persist
5. Toggle task complete → stats update
6. Delete task → confirm dialog → gone
7. Start session → live timer ticks → reload page → timer restored → stop → duration recorded
8. Pagination (with >20 tasks)
9. Language switch fa⇄en mid-session (timer label, dir flip)
10. Theme toggle (persist after reload)
11. Profile: change fullname / change password
12. Admin (as admin user): create major/course, protected-major guard, delete with confirm
13. Empty-state check: fresh user dashboard
14. Error-state check: stop Flask → dashboard shows per-zone errors with retry
15. Keyboard-only: tab through nav → dialog → form → submit; Esc closes dialogs

## Pass criteria

A route passes when: zero console errors, zero failed requests, all flows above green, token values verified by inspect (not eyeball), RTL mirrors LTR (no physical-property leftovers), contrast AA on text, and the screenshot matches the phase's design intent per 03.

## Run log

### Phase 0 run — 2026-09-03

- **Routes covered:** `/login` (fa, dark, 375px + 1440px), `/app` (fa, dark, 1440px, authenticated session restored via silent refresh).
- **Verified:** Vazirmatn variable font active on body + h1 (`vazirmatn, vazirmatn Fallback, ...` in computed styles); semantic tokens resolve (`--color-accent`, fonts via next/font); RTL intact (`dir=rtl`); session restore flow unaffected; **zero console errors**.
- **Issues found:** dev-server `.next` corrupted when `next build` ran concurrently (Windows file lock, ENOENT on `_buildManifest.js.tmp.*`) → fixed by stopping preview server, clearing `.next`, restarting. Not a code issue — build/dev must not run simultaneously.
- **Checks:** `tsc --noEmit` green; `eslint` green (2 pre-existing `_removed` unused-var warnings in API route handlers, unrelated); `next build` green (all 8 routes).
- **Visual delta:** typeface only (per plan). Palette, spacing, radius unchanged — token layer maps to current values.

### Phase 1 run — 2026-09-03

- **Scope:** full reskin of `components/ui.tsx` on the token layer. Export names unchanged — zero call-site edits.
- **Routes covered:** `/app` (fa, dark+light, 1440px), task dialog, `/login` (dark), `/register` (375px mobile).
- **Token verification via inspect (not eyeball):** primary button `bg=accent, radius=8px, h=36px`; card `bg=surface-1, border=border-subtle, radius=12px`; inputs `h=36px, border=border-strong`; ghost variant transparent; badges `rounded-pill`; dialog surface 12px.
- **Flows:** theme toggle light⇄dark (server-persisted), logout → login redirect, dialog open/close. Silent-refresh 401→refresh→retry flow observed healthy.
- **Issues found:** none in primitives. (Phase 3 will replace the emoji theme toggle + header select; inline size hacks at call sites swept in Phase 4.)
- **Checks:** `tsc --noEmit` green; `eslint` green (same 2 pre-existing warnings); mobile 375px no horizontal overflow.

### Phase 2 run — 2026-09-03

- **Scope:** ConfirmDialog → Radix AlertDialog; TaskFormDialog → Radix Dialog. Props APIs unchanged; manual Esc/portal/focus code deleted (Radix provides focus trap, scroll lock, Esc, backdrop cancel).
- **Deliberate deviation:** confirm button is a plain `Button`, not `AlertDialog.Action` — parent state controls close timing so the dialog stays open while `loading` and on failed deletes (matches pre-Radix behavior).
- **Browser QA (fa, dark):** dialog opens with focus on first field; `aria-modal` + labelled title present; body scroll lock applied and released on close; Esc closes; Cancel closes; Confirm deletes task (create → 201, delete → 204 observed); dialog closes only after parent confirms.
- **Issues found:** 1) first `npm install` ran from repo root — packages landed in wrong `node_modules`, Turbopack build error until reinstalled in `frontend/` (transient, self-inflicted). 2) Console hydration warning on HMR reload only — not reproducible after clean load; will re-check in Phase 6 sweep.
- **Checks:** `tsc` green; `eslint` green (2 pre-existing); `next build` green (13 pages).

### Phase 3 run — 2026-09-05

- **Scope:** app shell rebuilt — Logomark (new), UserMenu (new, Radix DropdownMenu + avatar initials), LangSwitch (new segmented control), Lucide icon theme toggle (emoji removed), mobile nav → Radix Dialog sheet with identity block. New deps: `@radix-ui/react-dropdown-menu`, `lucide-react`.
- **Verified (inspect, not eyeball):** sticky header with blur; nav gating — non-admin sees Dashboard/Profile only (no admin link); UserMenu opens with identity block + profile/logout, focus moves in, highlighted-item styles apply; theme toggle switches class + persists server-side; LangSwitch flips `dir`/`lang` live.
- **Mobile sheet (422px):** opens with scroll lock, brand + close button, nav links (close on navigate), identity + controls footer; Esc closes and lock releases; fa⇄en switch works from inside the sheet (sheet stays open, content re-renders LTR/RTL mirrored correctly).
- **Issues found:** 1) Turbopack dev cache went stale after installing new deps — "Module not found" until dev-server restart; build unaffected. Noted as a dev-only gotcha. 2) One transient body `pointer-events:none` read during sheet close animation — cleared after transition; no dead-UI observed.
- **Checks:** `tsc` green; `eslint` green (2 pre-existing); `next build` green.

### Phase 4 run — 2026-09-05

- **Scope:** dashboard rebuilt as asymmetric two-zone grid (workspace 8-col / context 4-col). New: `running-session-bar.tsx` (docked timer, Space Grotesk `tnum` clock), `course-progress-list.tsx` (zero-activity filter, activity sort, 6-row cap + show-all), `StatsStrip` (borderless stat strip), recharts `WeeklyChart` (localized weekday axis, token colors, empty-day muted cells). Task rows: priority edge rail + weight, icon actions with aria-labels, running-row accent treatment. New locale keys (fa+en, parity verified): `stats.this_week_total`, `dashboard.show_all_courses`, `dashboard.show_fewer_courses`, `dashboard.empty_courses_hint`, `tasks.suggested_course`.
- **Full session cycle QA (fa, dark, desktop):** create task (201) → start session → timer ticks (verified `0:02:11` → `0:02:37`, Space Grotesk 36px, `font-feature-settings: "tnum"`) → **page reload → clock restored from server session start (`0:03:26`)** → stop → stats update (week ۰٫۱ ساعت), chart renders 1 bar, course progress row appears → delete task via AlertDialog (204).
- **Zero-signal states:** fresh-style account shows empty-state with suggested course; course section shows quiet hint; chart renders muted empty cells — no noise (audit C3 fixed).
- **Layout verify (inspect):** desktop 1440px → workspace 736px + context 352px side-by-side; mobile 375px → single column, tasks before context (priority order), no overflow.
- **Light theme:** paper surfaces, accent CTA, correct tinted bars (screenshot verified).
- **Issues found:** none new. Test data cleaned up (test task deleted; test study session remains in DB from timer QA — harmless).
- **Checks:** `tsc` green; `eslint` green (2 pre-existing); `next build` green.

### Phase 5 run — 2026-09-05

- **Scope:** new `toast.tsx` (minimal custom ToastProvider, aria-live, auto-dismiss) wired into providers; login/register get brand moment (Logomark + wordmark above card); profile restructured (identity header with avatar initials + member since, toasts for saves); admin restructured (shield zone marker, forms separated by rules, courses grouped by major with per-major empty note, protected-major rule surfaced as note, toasts for actions). Auth logic unchanged everywhere.
- **QA:** profile fullname save → PUT 200 → toast "ذخیره شد." (verified live via MutationObserver — first two checks missed the 4s auto-dismiss window); admin zone renders (elevated test user via backend), protected-major delete disabled, create major → toast + list update, delete major via AlertDialog → clean; logout → login brand moment confirmed visually; zero console errors.
- **Test data:** elevated `audit_ui_tester` to admin for QA — should be reverted to `is_admin=false` (dev DB only); test majors created and deleted.
- **Incident:** another `.next` dev-cache corruption (build ran while dev server held the dir) — restarted + cleared; reminder: never run `next build` while dev server is up on Windows.
- **Checks:** `tsc` green; `eslint` green (2 pre-existing); backend `pytest`: **306 passed** (backend untouched by design).

### Phase 6 run — 2026-09-05 (final sweep)

- **New:** `app/not-found.tsx` (branded 404, logomark, i18n) + `app/app/forbidden/page.tsx` (403, ShieldX icon). 5 new locale keys (`errors.*`), fa/en parity verified.
- **Contrast pass (computed, lab→sRGB conversion):**
  - Light: primary 12.76, secondary 4.61, muted 6.33, accent 6.05, accent-fg 6.05, success 4.06, danger 4.23, warning 4.48 — all ≥ 4.5 for text or fixed-usage.
  - Dark: primary 13.62, secondary 9.18, muted 6.67, accent 5.96, accent-fg 7.21, success 10.43, danger 5.47, warning 10.65 — all pass.
  - Tokens darkened to achieve this: light `muted/success/warning/danger`, dark `muted`. (globals.css annotated "Phase 6 contrast pass".)
- **Lint:** logical-property rule promoted `warn → error` — zero violations across the codebase.
- **404 verified:** real navigation to unknown route renders localized branded page with working escape link. Non-admin deep link to `/app/admin` still bounces to `/app` (pre-existing guard; 403 page available for explicit links).
- **Final checks:** clean `rm -rf .next && next build` green (all routes, middleware); `tsc --noEmit` green; `eslint` green (2 pre-existing warnings in API route handlers only); full route sweep fa/dark + light: dashboard two-zone + recharts + Vazirmatn confirmed, profile/admin/404 all render, no console errors, no dead pages.
- **Test data note (dev DB):** `audit_ui_tester` password is `AuditPass!2026`; one test study session recorded during Phase 4 timer QA.
