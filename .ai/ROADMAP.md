# Study Planner — Roadmap

_Last updated 2026-08-10. See `.ai/TODO.md` for per-task detail and status._

## Current state

Backend (Flask 3.0 + SQLAlchemy + Alembic + PostgreSQL) is production-hardened
through phase 1, with phase 2 (backend hardening) planned:

- Application factory, split blueprints, env-only config.
- Two parallel auth systems (browser session-cookie + stateless signed API
  access tokens (15 min) + revocable refresh tokens (30 days, jti-tracked)).
- Rate limiting on all auth endpoints.
- REST API at `/api/*` ready for an SPA/mobile client, with task CRUD, study
  session start/stop, pagination, and dashboard statistics.
- SQL aggregation for statistics; pagination on task lists.
- Structured JSON logging; optional Sentry; CLI admin bootstrap.
- 191 tests passing, ruff clean, CI pipeline (Python 3.13), Docker +
  PostgreSQL/ Redis compose + backup script.

Frontend is server-rendered Jinja templates + Bootstrap 5 + vanilla JS.
`dashboard.html` is 1039 lines, `admin.html` 598 — maintainable but heavy, and
not the shape a modern client wants.

### What is NOT done yet (do not assume otherwise)

- **No RBAC.** Single `User.is_admin: bool`. No Manager / Student / Developer
  roles, no permission tables, no fine-grained API-level read/create/update/
  delete permission matrix.
- **No audit trail.** Structured JSON logs exist (TASK-021) but no independent
  Logging DB and no before/after change history on core tables.
- **No DB initialization at startup.** Docker entrypoint runs `flask db upgrade`
  but does NOT create the database if missing, and does not run idempotent
  seeding on boot. Re-run is not guaranteed safe under multiple replicas
  (TASK-030 open).
- **No Database Access Layer separation.** Routes and services use `Task.query`
  and `db.session` directly. Read/write split for a future PostgreSQL Read
  Replica is not possible without a rewrite.
- **Stats still measure the wrong signal.** `StudySession` is wired (API +
  dashboard UI), but `services/statistics.py` still aggregates `Task.hours` by
  `Task.created_at` instead of `StudySession.duration` by `started_at`
  (TASK-027 open).
- **Redis cache layer not wired.** `docker-compose.yml` ships Redis (used by
  rate-limit storage only); no application cache-aside layer exists
  (TASK-025 open).
- **Security headers + cookie hardening** not done (TASK-029 open).
- **Health endpoints** not done (TASK-028 open).

---

## Priorities — phased plan

Phase ordering is by dependency, risk, importance, and current state. Each
phase has exit criteria. No phase starts before its dependencies land unless
noted.

| Phase | Title | Priority | Pillars covered | Status |
|-------|-------|----------|-----------------|--------|
| 1 | Foundation (app factory, blueprints, models, REST API, auth, tests, CI, Docker, backups) | Done | — | DONE |
| 2 | Backend production hardening | 1 | Caching (partial), Stats correctness, Health, Headers, CI uplift, Docker migration safety | Planned |
| 3 | Deployment + idempotent DB initialization | 1 | Deployment, DB Init | New |
| 4 | RBAC — roles, permissions, API guards | 1 | RBAC | New |
| 5 | Logging DB + audit trail | 2 | Logging + Audit | New |
| 6 | Replication readiness — DB access layer | 2 | Replication Readiness | New |
| 7 | Frontend migration to Next.js + shadcn/ui | 3 | Frontend Migration | Planned (extends TASK-032) |

Lower priority / deferred: gamification (TASK-009) and smart planner
(TASK-010) remain P3 and are not on this roadmap until the above ships.

---

## Phase 1 — Foundation — DONE

Tasks TASK-001 through TASK-024. See `.ai/TODO.md`. Exit criteria met: app
factory, blueprints, Alembic, REST API, rate limiting, browser-route tests,
SQL stats aggregation, pagination, CI, Docker, Sentry, refresh tokens, backup
script.

---

## Phase 2 — Backend production hardening (priority 1)

| Task | Title | Depends on | Risk |
|------|-------|-----------|------|
| TASK-025 | Redis caching layer | TASK-039 (data access layer) for clean invalidation | Medium (invalidation correctness) |
| TASK-026 | REST API gaps for SPA (`/api/me`, `/api/courses`, `/api/majors`, `/api/auth/logout`) | — | Low |
| TASK-027 | Stats correctness: StudySession as the hours signal | TASK-016 DONE | Medium (backfill decision) |
| TASK-028 | `/healthz` + `/readyz` endpoints | — | Low |
| TASK-029 | Security headers + cookie hardening | TASK-028 | Low |
| TASK-030 | Docker migration runner safety | TASK-034 (DB init) | Low (single-replica today) |
| TASK-031 | CI quality uplift (matrix, coverage, PG tests) | — | Low |

Sequencing notes:

- TASK-026 unblocks the UI migration and can proceed independently — start it
  first or in parallel with TASK-025.
- TASK-025 (Redis) lands after TASK-039 (data access layer) so cache invalidation
  hooks sit at the data layer, not scattered across routes.
- TASK-028 + TASK-029 are small and can be one PR.
- TASK-031 is incremental to CI and can run throughout the phase.

Exit criteria: every `/api/*` endpoint the SPA needs exists and is tested, hot
reads are cached in Redis, statistics reflect real session time, health
endpoints respond, cookies/headers are hardened, and CI runs against
PostgreSQL.

---

## Phase 3 — Deployment + idempotent DB initialization (priority 1)

Goal: the app starts cleanly on any OS via Docker, with an idempotent
startup that connects to an existing DB or creates it, runs migrations, and
seeds base reference data — without duplicates or corruption on re-run.

| Task | Title | Depends on | Risk |
|------|-------|-----------|------|
| TASK-033 | OS-independent Docker hardening | TASK-020 DONE | Low |
| TASK-034 | Idempotent DB initialization at startup | TASK-033 | Medium (idempotency + race) |

TASK-033 — OS-independent Docker hardening:
- Confirm `Dockerfile` + `docker-compose.yml` run unchanged on Linux, macOS,
  Windows (Docker Desktop). No host-path assumptions that break cross-OS.
- Pin image digests for reproducible builds; non-root user inside the container.
- Healthcheck wired to `/healthz` (TASK-028); compose ` depends_on: condition:
  service_healthy` for postgres + redis before app starts.
- Env-var driven config (no secrets in images); `.env.example` documents every
  var. Separate compose files for dev vs prod overrides (optional).

TASK-034 — Idempotent DB initialization at startup:
- On boot: (1) connect to `DATABASE_URL`; (2) if the database does not exist,
  create it (via a bootstrap connection to `postgres` db + `CREATE DATABASE`);
  (3) run `flask db upgrade`; (4) run `seed-reference-data` idempotently.
- Seeding must be idempotent: `seed_reference_data()` already upserts by
  `key` — extend the guarantee to all base data and document which data is
  seed vs. user-created. Never re-create or duplicate user data.
- Under multiple replicas, migrations + seeding must not race: a one-shot
  init container (compose `init` service running migrations + seed, exiting
  before app containers start) OR a distributed advisory lock around the
  upgrade. Supersedes TASK-030 (migration runner safety) — fold that scope
  in here.
- Document the chosen approach in README + STRUCTURE.md.

Exit criteria: `docker compose up` on a clean host (no pre-existing DB) brings
the app up healthy, migrates, seeds base data once, and a second `up` changes
nothing. Works on Linux + macOS + Windows.

---

## Phase 4 — RBAC: roles, permissions, API guards (priority 1)

Goal: replace the single `is_admin: bool` with an extensible role/permission
model. Four roles: **Developer** (superuser / sysadmin — infra + all data),
**Admin** (system administrator — full app config, all users, majors/courses,
system stats), **Manager** (CRM — view student status, dashboards, reports,
logs, manage student data; no system config), **Student** (lowest — own tasks
CRUD, study sessions / time tracking, own results only).

| Task | Title | Depends on | Risk |
|------|-------|-----------|------|
| TASK-037 | RBAC model — roles + permissions tables + migration | — | Medium (migration of existing `is_admin`) |
| TASK-038 | Permission matrix + API-level guards | TASK-037 | Medium (UI + API surface breadth) |

TASK-037 — RBAC model:
- New tables: `roles`, `permissions`, `role_permissions` (M:N), `user_roles`
  (M:N). Or a simpler `users.role` enum + `permissions` bitmask if the matrix
  is small — decide during design, but the model must allow adding a new role
  or permission without a rewrite.
- `Developer` = superuser (bypasses all checks). `Admin`, `Manager`, `Student`
  each map to a set of permissions.
- Migration must preserve existing access: users with `is_admin=True` become
  `Admin` role; all others become `Student`. Backfill in the migration, do not
  drop `is_admin` until confirmation (legacy column retained per project
  convention).
- Permission granularity: Read / Create / Update / Delete per resource
  (users, majors, courses, tasks, study_sessions, statistics, logs, system).

TASK-038 — Permission matrix + API guards:
- Replace `admin_required` with `permission_required("resource:action")`.
  Existing admin routes map to `users:read`, `users:update`, `majors:*`,
  `courses:*`, `system:read`.
- API: every `/api/*` route declares its required permission(s).
- Permission matrix (subject to refinement in PRD):

  | Resource | Developer | Admin | Manager | Student |
  |---|---|---|---|---|
  | users (all) | CRUD | CRUD | Read | — |
  | users (self) | CRUD | CRUD | CRUD | R/U (profile, password) |
  | majors | CRUD | CRUD | Read | Read |
  | courses | CRUD | CRUD | Read | Read |
  | tasks (own) | CRUD | CRUD | CRUD | CRUD |
  | tasks (all) | CRUD | CRUD | Read (student monitoring) | — |
  | study_sessions (own) | CRUD | CRUD | CRUD | CRUD |
  | study_sessions (all) | CRUD | CRUD | Read | — |
  | statistics (system) | Read | Read | Read | — |
  | statistics (own) | Read | Read | Read | Read |
  | logs / audit | Read | Read | Read | — |
  | system config | CRUD | CRUD | — | — |

- Admin vs Manager distinction: Admin owns system config (majors, courses,
  user roles, system settings). Manager owns CRM (student status, reports,
  logs, student data) but cannot alter system config or roles.
- Extensibility: adding a role = insert `roles` + `role_permissions`; adding a
  permission = insert `permissions` + attach to roles. No code change to the
  guard decorator unless a new resource type appears.

Exit criteria: four roles enforced at the API layer, permission matrix
documented in PRD + DESIGN, existing admin access preserved, tests cover each
role × resource × action (allow + deny).

---

## Phase 5 — Logging DB + audit trail (priority 2)

Goal: an independent Logging database for system logs, plus an audit trail
that records every important action (CRUD + auth + admin actions) on core
tables with before/after state, actor identity, and session/IP context.

| Task | Title | Depends on | Risk |
|------|-------|-----------|------|
| TASK-035 | Independent logging DB + structured log routing | TASK-037 (actor identity) | Medium (second DB connection) |
| TASK-036 | Audit trail — generic audit log + before/after capture | TASK-035, TASK-037 | Medium (hooking all mutations) |

TASK-035 — Independent logging DB:
- A second database (or separate schema) for application + access logs,
  distinct from the business DB. Connection via `LOG_DATABASE_URL` (falls back
  to the main DB if unset, so dev stays single-DB).
- Structured logs (TASK-021 JSON formatter) write to this DB as well as
  stdout. Retention policy: configurable TTL, prune old log rows.
- Volume controls: log采样 for high-frequency events, cap row size.

TASK-036 — Audit trail:
- Generic `audit_log` table (preferred over one per business table) columns:
  `id`, `actor_user_id`, `actor_role`, `session_id`, `request_id`, `user_ip`,
  `action` (e.g. `task.update`), `resource_type`, `resource_id`,
  `before` (JSONB), `after` (JSONB), `status` (success/failed), `error`,
  `created_at`, `user_agent`.
- Capture before/after for update; full snapshot for create/delete.
- Hook mutations in the data access layer (TASK-039) so every write emits an
  audit record — not scattered through routes.
- Manager role can read audit logs (CRM visibility); Student cannot.

Exit criteria: independent logging DB configured, every core mutation produces
an audit row with before/after, retention documented, Manager can query logs
via API.

---

## Phase 6 — Replication readiness — DB access layer (priority 2)

Goal: separate business logic from the database connection so a PostgreSQL
Read Replica can be added later without a major rewrite. **No replication is
implemented in this phase** — only the architectural seam.

| Task | Title | Depends on | Risk |
|------|-------|-----------|------|
| TASK-039 | Database Access Layer + read/write split config | — | Medium (broad refactor of query sites) |

TASK-039 — Database Access Layer:
- Introduce a repository / data-access layer between services/routes and
  SQLAlchemy. Routes/services call repositories (`TaskRepo.list(...)`,
  `TaskRepo.create(...)`) which own the `db.session` usage.
- Connection config supports independent primary + replica URIs:
  `DATABASE_URL` (primary, read+write) and optional `DATABASE_REPLICA_URLS`
  (comma-separated read replicas). With no replica configured, all reads go
  to the primary.
- Logical read/write split at the data-access layer: read methods may target a
  replica session, write methods always target the primary. Business logic is
  not bound to a specific connection.
- Document consistency limits: replication lag, read-after-write expectations
  (a write then immediate read may hit a stale replica — route read-after-write
  to the primary, or accept eventual consistency).
- No failover / HA now; architecture must not block adding it later.
- Docker/config must not require a major rewrite for primary/replica topology.

Exit criteria: all `Task.query` / `db.session` direct usage in routes and
services is gone (lives only in the repository layer), `DATABASE_REPLICA_URLS`
env var documented, read/write split demonstrated with a single-unit test
even though no replica exists yet.

---

## Phase 7 — Frontend migration to Next.js + shadcn/ui (priority 3)

Driven by phases 2 + 4 (complete, RBAC-guarded API). See
`.ai/PLAN_REACT_MIGRATION.md` for the full design, updated to include
role-based dashboards (Developer / Admin / Manager / Student). Phases:

1. **Proof of concept** (TASK-032): a `frontend/` Next.js app renders a working
   dashboard listing tasks from `/api/tasks`, with create/toggle/delete. Proves
   auth flow, RTL, i18n, shadcn setup. Jinja UI untouched.
2. **Auth + profile screens**: login/register/logout, `/api/me` profile + theme
   + password change.
3. **Role-specific dashboards**: Student (own tasks/sessions/stats), Manager
   (CRM — student status, charts, logs, student data management), Admin
   (system config + users + majors/courses), Developer (superview + system).
4. **Dashboard full feature parity**: task CRUD, session start/stop, course
   list, statistics, charts (recharts replacing Chart.js).
5. **Admin + Manager panels**: admin + manager surfaces behind RBAC API guards.
6. **Dual-run + cutover**: both UIs served; feature-flag or route-prefix the
   new one; flip the default once parity is verified; retire the Jinja
   templates.

Constraints: the API is the contract — no new server-rendered features land
only in Jinja; everything new goes through `/api/*` so both UIs stay in sync.
RTL is first-class from phase 1 (Tailwind logical properties + `dir` attribute).

---

## Out of scope for this roadmap

- Gamification (TASK-009) and smart planner (TASK-010) — P3, blocked on
  decisions after the UI migration. Revisit once phase 7 ships.
- Mobile native client — the API makes it possible, but it is not on the
  roadmap until a web SPA proves the contract.
- Database high-availability / automatic failover — phase 6 prepares the seam
  but does not implement HA.
