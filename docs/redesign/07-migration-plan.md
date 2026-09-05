# 07 — Migration Plan

**STATUS: DRAFT — phase order fixed; execution starts only after 03 direction is approved.**

Constraints: app stays functional between phases; no big-bang; no backend/API/auth/i18n-contract changes; `pytest`, `npm run typecheck`, `npm run lint`, and `next build` green at every phase boundary; every phase visually QA'd per 08-visual-qa.md before the next begins.

## Phase 0 — Foundations (no visible change)

- **Objective:** token layer + fonts in place without touching pages.
- **Files:** `frontend/app/globals.css` (add `@theme` tokens, keep existing classes working), `frontend/app/layout.tsx` (load fonts via `next/font/local`), `frontend/public/fonts/*` (new), `.eslintrc`/eslint config (logical-property lint rule, warn-only first).
- **Risks:** font licensing/files (Vazirmatn is OFL — safe); FA tracking regressions (mitigate: no tracking on `[lang=fa]`).
- **Acceptance:** pages render unchanged visually except typeface; typecheck/lint/build pass.

## Phase 1 — Primitive reskin

- **Objective:** `ui.tsx` primitives adopt tokens; call sites unchanged.
- **Files:** `components/ui.tsx`.
- **Steps:** Button (variants × sizes × icon-button), Field/Input/Textarea/Select, Card surface variants, Alert (+icon, retry slot), Badge, Skeleton, EmptyState, Spinner.
- **Risks:** inline class overrides at call sites (e.g. `px-2 py-1 text-xs` in tasks-panel) fighting new sizes — sweep in Phase 3.
- **Acceptance:** all pages still function; visual diff only from token colors/radius/spacing.

## Phase 2 — Accessibility-critical components

- **Objective:** Radix-backed dialogs; a11y debts cleared.
- **Files:** `package.json` (add shadcn/Radix deps), `components/confirm-dialog.tsx`, `components/task-form-dialog.tsx` (logic preserved), call sites unchanged via same props API.
- **Risks:** focus-trap behavior differences in tests — manual QA on both dialogs; z-index layering with header.
- **Acceptance:** keyboard-only flow: open → fill → save; open → Esc; delete confirm — all clean. Screen-reader labels intact.

## Phase 3 — App shell + navigation

- **Objective:** branded chrome, identity block, segmented lang control, icon theme toggle, mobile sheet.
- **Files:** `components/app-shell.tsx`, new `components/user-menu.tsx`, `lib/lang-context.tsx` untouched (only UI).
- **Risks:** mobile menu is the only "toggleable" region — QA at 375px both dirs; admin link gating logic must not change.
- **Acceptance:** desktop + mobile nav flows in fa/en, light/dark.

## Phase 4 — Dashboard rebuild (highest visible value)

- **Objective:** hierarchy per 06 §1.
- **Files:** `app/app/page.tsx`, `components/stats-cards.tsx` → StatsStrip + new chart, new `components/running-session-bar.tsx`, `components/course-progress-list.tsx`, `components/tasks-panel.tsx` (row anatomy + inline-size cleanup).
- **Steps:** 1) extract CourseProgressList with zero-filter/sort/cap; 2) RunningSessionBar; 3) stats strip; 4) chart swap; 5) task row anatomy.
- **Risks:** timer logic (`loadTasks`, `runningSince` restore) — **copy logic verbatim**, only presentation moves; session-restore path regression = highest danger, test reload mid-session both langs.
- **Acceptance:** all existing behaviors pass manual regression list (create/edit/delete/toggle/start/stop/reload-restore/pagination/empty/error).

## Phase 5 — Auth pages + profile + admin

- **Objective:** brand moments + form-system application + toasts.
- **Files:** `app/login/page.tsx`, `app/register/page.tsx`, `app/app/profile/page.tsx`, `app/app/admin/page.tsx`; add toast primitive.
- **Risks:** rate-limit error copy from backend is English-only — present via i18n error component; admin group-by-major rendering.
- **Acceptance:** register→login→logout; profile saves; admin CRUD incl. protected major.

## Phase 6 — Error routes + polish + enforcement

- **Objective:** 404/403 pages, motion pass, contrast audit, lint rule promote to error.
- **Files:** `app/not-found.tsx`, `app/forbidden/page.tsx` (or segment), ESLint config, misc token fixes from QA log.
- **Acceptance:** full 08 visual QA sweep green across 8 routes × 2 langs × 2 themes × 3 viewports.

## Explicitly out of scope (never touched)

- `lib/auth-context.tsx`, `lib/api.ts`, `app/api/**` (route handlers), `middleware.ts` auth logic.
- Flask app, migrations, tests' behavioral assertions.
- Locale JSON **keys** (values may gain new keys for missing strings — both files in sync, per CLAUDE.md).
