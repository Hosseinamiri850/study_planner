# Product Requirements Document — Study Planner

_Last updated 2026-08-10. Companion to `.ai/ROADMAP.md` (phased plan),
`.ai/TODO.md` (task detail), `.ai/DESIGN.md` (architecture), and
`.ai/PLAN_REACT_MIGRATION.md` (frontend)._

## 1. Product overview

Study Planner is a web application that helps students track courses, tasks,
and study hours, with full Persian (RTL) / English (LTR) i18n. The server-
rendered (Jinja + Bootstrap) UI is the production client today; a JSON REST
API under `/api/*` supports a future SPA/mobile client and is the contract
any new client builds against.

**Stage:** past foundation; production-hardening in progress. The roadmap
(target state below) is not yet shipped.

## 2. Roles (RBAC — target state)

Four roles, replacing today's single `User.is_admin: bool`. See DESIGN.md
for the model and PLAN_REACT_MIGRATION.md for UI implications.

| Role | Scope | Description |
|------|-------|-------------|
| **Developer** | Superuser | Infrastructure + all data; bypasses permission checks. Sysadmin/ops access. |
| **Admin** | System | Full app configuration: users + roles, majors, courses, system stats, system settings. |
| **Manager** | CRM | View student status, dashboards/charts, reports, logs, student data management. Cannot alter system config or roles. |
| **Student** | Self | Lowest privilege: own tasks CRUD, study sessions / time tracking, own results only. |

Admin vs Manager distinction: Admin owns **system configuration** (majors,
courses, user roles, system settings). Manager owns **CRM** (student status,
reports, logs, student data) but cannot alter system config or roles.

## 3. Permission matrix (target state)

Granularity: Read / Create / Update / Delete per resource. `*` = all four.

| Resource | Developer | Admin | Manager | Student |
|---|---|---|---|---|
| users (all) | * | * | Read | — |
| users (self) | * | * | * | Read, Update (profile, password) |
| majors | * | * | Read | Read |
| courses | * | * | Read | Read |
| tasks (own) | * | * | * | * |
| tasks (all) | * | * | Read (student monitoring) | — |
| study_sessions (own) | * | * | * | * |
| study_sessions (all) | * | * | Read | — |
| statistics (system) | Read | Read | Read | — |
| statistics (own) | Read | Read | Read | Read |
| logs / audit | Read | Read | Read | — |
| system config | * | * | — | — |

Extensibility: adding a role = insert `roles` + `role_permissions`; adding a
permission = insert `permissions` + attach to roles. No guard-decorator code
change unless a new resource type appears.

## 4. Feature pillars (target state)

### 4.1 Deployment — OS-independent
The app runs on any host OS via Docker. `Dockerfile` + `docker-compose.yml`
work on Linux, macOS, Windows (Docker Desktop) without host-path hacks.
Reproducible builds (pinned digests), non-root container user, healthchecks
wired to `/healthz` + `/readyz`. No secrets baked into images — all config
via env vars. (TASK-033.)

### 4.2 Database Initialization at startup — idempotent
On boot the app connects to `DATABASE_URL`; creates the database if missing;
runs `flask db upgrade`; runs idempotent seed for base reference data
(majors/courses). Re-run changes nothing — no duplicates, no corruption,
no user data touched. Safe under multiple replicas (init container or
advisory lock). Default/seed data set: reference majors/courses only; **no
admin account** (security call — admin via `create-admin` CLI or promotion).
(TASK-034, supersedes TASK-030.)

### 4.3 Logging System — independent DB + audit trail
An independent Logging database (or separate schema) for application + access
logs, distinct from the business DB. Configurable retention/TTL and volume
controls. Audit trail records every important action (CRUD + auth + admin)
on core tables with before/after state, actor identity, session/IP context,
and request id. A **generic `audit_log` table** is preferred over one log
table per business table — it keeps the mutation hook in one place and
supports any resource. (TASK-035, TASK-036.)

Minimum audit fields: `actor_user_id`, `actor_role`, `session_id`,
`request_id`, `user_ip`, `action`, `resource_type`, `resource_id`, `before`
(JSONB), `after` (JSONB), `status`, `error`, `created_at`, `user_agent`.
Production extras (specify during design): `idempotency_key`, `txn_id`,
`source` (api/web/cli), `latency_ms`.

### 4.4 RBAC — roles, permissions, API guards
See sections 2 + 3. Permissions enforced at the API layer
(`permission_required("resource:action")`). Existing admin routes map to
`users:read`, `users:update`, `majors:*`, `courses:*`, `system:read`.
Migration preserves existing access (`is_admin=True` -> Admin; others ->
Student); legacy `is_admin` retained until confirmation. (TASK-037,
TASK-038.)

### 4.5 Frontend migration — React/Next.js/App Router/TypeScript/shadcn/ui
Plan-only in this phase. The Jinja UI keeps running in parallel during the
migration (no big-bang cutover). New UI mounted under `/app/*` or a subdomain;
flips default after parity verification; Jinja templates retired after.
Main pages, layouts, navigation, auth flow, authorization/role-based UI,
API contracts, data fetching, state, error/loading/form handling, validation,
component structure, folder structure, frontend-backend communication, and
role-specific dashboards are specified in `.ai/PLAN_REACT_MIGRATION.md`.

### 4.6 Caching Layer — Redis cache-aside
Redis sits between the API and the DB for hot read paths (course list, major
list, statistics dashboard, translator availability). Cache checked before
DB queries where appropriate. Cache-aside with explicit invalidation on
Create/Update/Delete through the data access layer. No sensitive data cached
without explicit design. Graceful degradation: Redis down -> fall through to
DB, never crash. Key naming, TTLs per category, invalidation events, stale-data
prevention documented in DESIGN.md. (TASK-025, blocked on TASK-039.)

### 4.7 Future Database Replication Readiness — architectural seam only
**Not implemented** in this roadmap. Design so a PostgreSQL Read Replica can
be added later without a major rewrite:
- Database Access Layer separate from business logic (TASK-039).
- Connection config supports independent primary + replica URIs
  (`DATABASE_URL`, `DATABASE_REPLICA_URLS`).
- Logical read/write split at the data-access layer (reads may target a
  replica; writes always primary). Business logic not bound to a specific
  connection.
- Support 1+ read replicas. Document consistency limits (replication lag,
  read-after-write). No failover/HA now; architecture must not block it.
- Docker/config must not require a major rewrite for primary/replica topology.

## 5. Existing features (already shipped — do not regress)

- Task management per course with priority levels (High / Medium / Low).
- Study hour tracking: study session start/stop + duration, per-task
  estimated hours, daily/weekly/monthly breakdowns.
- Interactive charts (Chart.js, replaced by recharts/shadcn in the React UI).
- Social view — see other users' progress and study hours.
- Secure hashed passwords (Werkzeug scrypt); rate limiting on auth endpoints;
  refresh-token rotation + revocation.
- Dark / Light theme per user; full Persian (RTL) + English (LTR) i18n with
  on-the-fly language switch; auto-translate major/course names via
  LibreTranslate.
- Admin panel — user management, majors, courses, system stats.
- PostgreSQL + SQLAlchemy, schema via Alembic migrations; 191 tests; CI
  (ruff + pytest on Python 3.13); Docker + PostgreSQL/Redis compose;
  `scripts/backup.sh` (pg_dump + retention).

## 6. Non-goals (this roadmap)

- Gamification (streaks, achievements) — deferred P3.
- Smart Planner (auto-schedule generation) — deferred P3.
- Mobile native client — not until the web SPA proves the API contract.
- Database high-availability / automatic failover — phase 6 prepares the seam
  but does not implement HA.
