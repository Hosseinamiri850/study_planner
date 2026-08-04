# Plan — Frontend migration to Next.js + shadcn/ui

_Last updated 2026-08-04. Scope: migrate the Study Planner UI from Jinja +
Bootstrap to Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui.
Backend Flask stays the source of truth; the SPA talks to `/api/*` only._

## Why

The current UI is server-rendered Jinja templates. `dashboard.html` is 1039
lines, `admin.html` 598 — heavy to extend. More importantly, a modern client
(RTL done right, component reuse, offline-friendly, future mobile) wants a
real frontend, and `/api/*` already exists to support it. This migration
happens AFTER the backend production-hardening (phase 2, see `.ai/ROADMAP.md`)
so the SPA builds against a complete, cached API.

## Constraints

- **No big-bang cutover.** Jinja templates keep running during the migration;
  both UIs are served in parallel. The new UI is feature-flagged or mounted
  under a route prefix (`/app/*` or a separate subdomain) until parity is
  verified, then the default flips and the Jinja templates are retired.
- **The API is the contract.** Every feature the new UI needs must exist on
  `/api/*` (TASK-026 fills the gaps). No new behavior is added Jinja-only;
  everything new goes through the API so both UIs stay in sync.
- **RTL is first-class from day one.** Persian is RTL; English is LTR. Use
  Tailwind logical properties (`ps-`/`pe-`/`ms-`/`me-`) and the `dir` attribute
  on `<html>`. shadcn/ui primitives (Radix-based) are RTL-safe; Tailwind must
  use logical properties, not `pl-`/`pr-`.
- **i18n reuses existing locale files.** `locales/fa.json` and `en.json` are
  the source of truth; the Next client loads them via `next-intl` (or a thin
  custom loader) so strings stay normalized across both UIs.
- **Auth.** Access token is short-lived (15 min) and held in memory; refresh
  token is an httpOnly cookie set by a thin server action (or a proxy route)
  so the SPA never touches it directly. Logout calls `POST /api/auth/logout`
  (TASK-026) to revoke the refresh token.

## Stack

- Next.js 15 (App Router), TypeScript.
- Tailwind CSS v3 (v4 when shadcn supports it cleanly).
- shadcn/ui (Radix primitives + Tailwind) for components.
- `next-intl` for i18n (App Router native, RTL-aware routing).
- `recharts` or shadcn's chart primitives to replace Chart.js.
- API layer: a typed client (`lib/api.ts`) generated from or hand-mirroring
  the Flask route shapes — keep types in sync with backend responses.
- Dev: `frontend/` runs `next dev` on a separate port; Flask serves `/api/*`
  and CORS is enabled for the dev origin only. In prod, Next is served by
  Next's own server (or static export where possible) and proxies API calls
  to Flask.

## Phased plan

### Phase 1 — Proof of concept (TASK-032)

Goal: a working dashboard route that lists tasks from `/api/tasks` and can
create/toggle/delete one. Proves the stack end-to-end.

- `frontend/` scaffolded: Next 15 App Router, TS, Tailwind, shadcn/ui init.
- `next-intl` wired with `locales/fa.json` + `en.json` copied read-only from
  backend (or symlinked in dev).
- Auth flow: login page posts to `/api/auth/login`, stores access token in
  memory, stores refresh token as httpOnly cookie via a server action. A
  route protector gates `/app/*` on a valid access token.
- RTL setup: `<html dir lang>` driven by locale; Tailwind logical properties.
- Dashboard route: task list + create/toggle/delete against `/api/tasks`.
- No Jinja templates removed. New UI mounted at `/app/*` (or a subdomain).

Exit: an authenticated user can log in and manage tasks in the Next UI while
the Jinja dashboard still works.

### Phase 2 — Auth + profile parity

- Register/logout screens.
- Profile page backed by `GET /api/me` + `PUT /api/me` (TASK-026): fullname,
  theme toggle, password change with current-password verification.
- Theme (dark/light) stored server-side via the API, mirrored in the UI via
  the `class` strategy on `<html>`.

### Phase 3 — Dashboard full parity

- Task CRUD (full fields: priority, estimated hours, course, description).
- Session start/stop with live timer + duration display, backed by
  `/api/tasks/<id>/sessions` (already exists).
- Statistics dashboard backed by `/api/statistics/dashboard`, charted with
  `recharts`/shadcn chart primitives (replacing Chart.js).
- Course + major selectors backed by the new `GET /api/courses` /
  `GET /api/majors` endpoints.
- Pagination UI on task lists (backend already paginates — TASK-018 backend).

### Phase 4 — Admin panel

- Admin surface (`/app/admin`) behind `is_admin` API guards (TASK-026 admin
  write endpoints).
- User management (delete, password reset), major/course CRUD, system-wide
  statistics chart. All via authenticated `/api/*`.

### Phase 5 — Dual-run + cutover

- Both UIs served; feature-flag or route-prefix chooses which is default.
- Flip the default once parity is verified against a checklist.
- Retire the Jinja templates and remove the now-dead server-render paths
  (browser blueprint routes can stay as auth redirects to the SPA).
- Update `STRUCTURE.md` and `README.md` to reflect the new frontend.

## Risk areas

- **RTL + shadcn.** Radix primitives are RTL-safe, but Tailwind utilities
  must use logical properties (`ps/pe/ms/me`), not physical (`pl/pr/ml/mr`).
  Set up an ESLint rule or a lint check to catch physical properties early.
- **Auth token storage.** Putting the access token in localStorage is
  simpler but XSS-exposed. Prefer in-memory access token + httpOnly refresh
  cookie via a server action. This is the main reason phase 1 needs a working
  server-action proxy, not a pure static export.
- **Proxy/CORS.** Dev needs CORS from the Next port to Flask; prod needs a
  proxy (Next middleware or reverse proxy) so the SPA and API share an
  origin and CORS is unnecessary.
- **String drift.** Both UIs must use the same `locales/*.json` to avoid
  divergence. Consider moving locale files to a shared package or a
  symlinked path so backend and frontend read the same files.
- **Feature parity verification.** Before cutover, maintain a parity
  checklist per route. Do not flip the default with gaps.

## Out of scope

- Mobile native (the API makes it possible; revisit after the web SPA ships).
- Offline-first/PWA — possible later, not required for cutover.
- Replacing Flask — backend stays; only the rendering layer moves.
