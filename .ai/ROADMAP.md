# Study Planner — Roadmap

_Last updated 2026-08-04. See `.ai/TODO.md` for per-task detail and status._

## Current state

Backend (Flask 3.0 + SQLAlchemy + Alembic + PostgreSQL) is production-hardened
through phase 1:

- Application factory, split blueprints, env-only config.
- Two parallel auth systems (browser session-cookie + stateless signed API
  tokens with revocable refresh tokens).
- Rate limiting on all auth endpoints.
- REST API at `/api/*` ready for an SPA/mobile client.
- SQL aggregation for statistics; pagination on task lists.
- Structured JSON logging; optional Sentry; CLI admin bootstrap.
- 191 tests passing, ruff clean, CI pipeline, Docker + backup script.

Frontend is server-rendered Jinja templates + Bootstrap 5 + vanilla JS.
`dashboard.html` is 1039 lines, `admin.html` 598 — maintainable but heavy, and
not the shape a modern client wants.

---

## Priorities

**Phase 2 — Backend production hardening (P4, priority 1).** Close the gaps
that block scaling and a real SPA: Redis cache layer, finish the `/api/*`
surface, fix stats to read from `StudySession`, add health endpoints, harden
session cookies and HTTP headers, make the Docker migration runner safe under
replicas, and uplift CI (matrix + coverage + PostgreSQL-backed tests).

**Phase 3 — UI migration to Next.js + shadcn/ui (P5, priority 2).** Starts
only after phase 2 lands, so the SPA client builds against a complete, cached
API. The Jinja UI keeps running in parallel during the migration; no big-bang
cutover.

Lower priority/deferred: gamification (TASK-009) and smart planner
(TASK-010) remain P3 and are not on this roadmap until the above ships.

---

## Phase 2 — Backend production hardening

| Task | Title | Depends on | Risk |
|------|-------|-----------|------|
| TASK-025 | Redis caching layer | — | Medium (invalidation correctness) |
| TASK-026 | REST API gaps for SPA (me, courses, majors, logout) | — | Low |
| TASK-027 | Stats correctness: StudySession as hours signal | TASK-016 (done) | Medium (backfill decision) |
| TASK-028 | `/healthz` + `/readyz` endpoints | — | Low |
| TASK-029 | Security headers + cookie hardening | TASK-028 | Low |
| TASK-030 | Docker migration runner safety | — | Low (single-replica today) |
| TASK-031 | CI quality uplift (matrix, coverage, PG tests) | — | Low |

Sequencing notes:

- TASK-026 unblocks the UI migration and can proceed independently — start it
  first or in parallel with TASK-025.
- TASK-025 (Redis) lands before TASK-027 so the new stats path is cached from
  day one; invalidate on task writes.
- TASK-028 + TASK-029 are small and can be one PR.
- TASK-031 is incremental to CI and can run throughout the phase.

Exit criteria for phase 2: every `/api/*` endpoint the SPA needs exists and is
tested, hot reads are cached in Redis, statistics reflect real session time,
health endpoints respond, cookies/headers are hardened, and CI runs against
PostgreSQL.

---

## Phase 3 — UI migration to Next.js + shadcn/ui

Driven by the phase-2 API surface. See `.ai/PLAN_REACT_MIGRATION.md` for the
full design. Phases:

1. **Proof of concept** (TASK-032): a `frontend/` Next.js app renders a
   working dashboard listing tasks from `/api/tasks`, with create/toggle/
   delete. Proves auth flow, RTL, i18n, shadcn setup. Jinja UI untouched.
2. **Auth + profile screens**: login/register/logout, `/api/me` profile +
   theme + password change.
3. **Dashboard full feature parity**: task CRUD, session start/stop, course
   list, statistics, charts (replacing Chart.js with a shadcn-compatible
   chart or recharts).
4. **Admin panel**: the admin surface behind `is_admin` API guards.
5. **Dual-run + cutover**: both UIs served; feature-flag or route-prefix the
   new one; flip the default once parity is verified; retire the Jinja
   templates.

Constraints: the API is the contract — no new server-rendered features land
only in Jinja; everything new goes through `/api/*` so both UIs stay in sync.
RTL must be first-class from phase 1 (Tailwind logical properties + `dir`
attribute), not bolted on later.

---

## Out of scope for this roadmap

- Gamification (TASK-009) and smart planner (TASK-010) — P3, blocked on
  decisions after the UI migration. Revisit once phase 3 ships.
- Mobile native client — the API makes it possible, but it is not on the
  roadmap until a web SPA proves the contract.
