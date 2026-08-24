# Development Roadmap

Reviewed against actual `trunk` code. Items marked DONE are verified in the
codebase, not just assumed from an earlier plan.

---

# P0 — Critical (originally planned) — DONE

## TASK-001 — Application Factory Pattern — DONE
`app/__init__.py` has `create_app()`. `app.py` is now just a thin dev entry point.

## TASK-002 — Split Routes — DONE
`app/routes/web.py`, `admin.py`, `api.py` — three blueprints, registered in
`create_app()`.

## TASK-003 — Database Migration — DONE
Flask-Migrate + Alembic wired up (`migrations/`), two revisions applied.
Automatic table creation on startup has been removed (verified — no
`db.create_all()` in the request/startup path).

---

# P1 — High (originally planned)

## TASK-004 — Security Hardening — PARTIALLY DONE
Done:
- `SECRET_KEY` required, app refuses to start without it (verified in
  `app/__init__.py`).
- CSRF protection global via Flask-WTF, JSON API explicitly exempted per-route.
- Passwords hashed (Werkzeug `generate_password_hash`/`check_password_hash`).

Not done (see new P0 section below — these are now the actual blockers):
- Default `admin`/`admin` account was removed, but nothing replaced it — see
  TASK-011.
- No rate limiting on any auth endpoint.
- No input length/size limits at the request level (relies on column limits
  raising DB errors, not clean 400s).

## TASK-005 — Database Model Improvement — DONE (schema), NOT WIRED UP
`StudySession` table exists (migration `20260723_02`), `Task.status`,
`estimated_hours`, `course_id`, completion metadata all added. But: nothing in
`routes/` or `services/` creates or reads a `StudySession` row. See TASK-012.

## TASK-006 — REST API Layer — DONE
`app/routes/api.py`: register/login (returns Bearer token), CRUD on tasks,
dashboard statistics, translate. Tested in `tests/test_routes_api.py`.

---

# P2 — Medium (originally planned)

## TASK-007 — Testing — DONE (progressively expanded)
191 pytest tests covering models, services, utils, API routes, browser routes
(web.py + admin.py), integrations, CLI commands, rate limiting, refresh-token
rotation, and Sentry init. Browser-route coverage was closed by TASK-015.

## TASK-008 — Docker Support — superseded by TASK-020 (DONE)
Originally tracked "no Dockerfile/compose"; TASK-020 shipped `Dockerfile` +
`docker-compose.yml` (app + PostgreSQL 16 + Redis). Kept for traceability.

---

# P3 — Low (originally planned, unchanged)

## TASK-009 — Gamification
Streaks, achievements. Not started. Depends on TASK-012 (StudySession) for
anything time-based.

## TASK-010 — Smart Planner
Automatic schedule generation. Not started.

---

# New items found during code review (2026-07) — prioritize these before P3

## P0 — blocks a real first deploy

### TASK-011 — Admin account bootstrap — DONE
`flask --app app create-admin <username>` CLI command added (prompts for
password, hashes it, `is_admin=True`). `--promote` flag grants admin role
to an existing user. `seed-reference-data` still creates no admin (correct).
README updated to document the command. Tested in `tests/test_cli.py`.

### TASK-012 — Fix `translator_available()` on every page render — DONE
`inject_i18n` context processor now calls `is_available_cached()` (60s TTL)
instead of the blocking `is_available()`. `/api/translator-status` still
uses the live check. `reset_availability_cache()` provided for tests.

### TASK-013 — README accuracy pass — DONE
README Quick Start (Persian + English) describes the migration-based flow,
`create-admin` command, and the intentional absence of auto-table-creation
and `admin`/`admin` seed. The bcrypt claim is removed — code uses Werkzeug's
default hasher (scrypt).

## P1 — needed before real users / before scaling past a handful of people

### TASK-014 — Rate limiting on auth endpoints — DONE
`/login`, `/register`, `/api/auth/login`, `/api/auth/register` are throttled
at 5/min per IP via Flask-Limiter (`app/extensions.py`, initialized in
`create_app`). Storage: Redis when `RATELIMIT_STORAGE_URI` is set, in-memory
otherwise. Tests in `tests/test_rate_limiting.py`.

### TASK-015 — Test coverage for browser routes — DONE
`tests/test_routes_web.py` covers login/register/logout, dashboard task
CRUD, theme toggle, language switch, and view_user. `tests/test_routes_admin.py`
covers admin access control, user deletion, password change, major/course
CRUD, and the delete_course task-preservation behavior. This is the actual
product surface today; it's now as well-tested as the rest of the app.

### TASK-016 — Wire up StudySession tracking — DONE
`StudySession` model has `start_session` / `stop` / `active_session` /
`duration` (task.py). API endpoints exist: `POST /api/tasks/<id>/sessions`
(start, 409 if already open), `POST .../sessions/<sid>/stop` (idempotent),
`GET .../sessions` (list). Dashboard server-rendered UI start/stop confirmed.
The remaining gap is stats correctness — statistics still aggregate
`Task.hours` by `Task.created_at`, not `StudySession.duration` by
`started_at` — that is TASK-027.

### TASK-017 — Move statistics aggregation into SQL — DONE
`services/statistics.py` and `routes/admin.py` now sum hours-by-day via a
single grouped SQL query (`group_by(Task.created_at)` + `func.sum(Task.hours)`)
instead of loading every task into Python and scanning 30 days. Result shape
is unchanged; the admin panel's system-wide loop (the worst offender) no
longer materializes the full completed-task rowset. The underlying date signal
is still `created_at` (see TASK-016) — switching to `completed_at`/`StudySession`
timestamps is a separate correctness decision deferred with the session-tracking
work.

### TASK-018 — Pagination — BACKEND DONE (UI DEFERRED)
`/api/tasks` GET honors `?page` and `?per_page` (both required together;
per_page clamped to 1–100). Flask-SQLAlchemy `paginate()` emits LIMIT/OFFSET
at the SQL layer — no full materialisation. Legacy `{tasks}` shape preserved
when neither param is present. Browser UI pagination (admin user list,
dashboard leaderboard) deferred — needs a UI decision.

### TASK-019 — CI pipeline — DONE
`.github/workflows/ci.yml` runs `ruff check` + `pytest -q` on Python 3.13
for pushes to master/production-hardening and PRs to master. ruff config
lives in `pyproject.toml` (selects F/E/W/I/UP, ignores E501/E701/BLE001/DTZ
to match house style). Dev deps in `requirements-dev.txt`.

## P2 — production hygiene

### TASK-020 — Docker — DONE
`Dockerfile` (python:3.13-slim, runs `flask db upgrade` then gunicorn on the
app factory) and `docker-compose.yml` (app + PostgreSQL 16 + Redis, so
RATELIMIT_STORAGE_URI can use Redis out of the box). `.dockerignore` keeps
`.env`, caches, and `.git` out of the image. See README for `docker compose
up` usage.

### TASK-021 — Structured logging + error monitoring — DONE
`app/utils/logging.py` adds a one-line-per-record JSON formatter (stdlib
only, no new deps) and `configure_logging` is called from `create_app`.
JSON output in production, human text when DEBUG or TESTING. Idempotent
under re-create (tests). Sentry integration added via `init_sentry`:
optional dependency (`sentry-sdk[flask]`), no-op when `SENTRY_DSN` unset or
SDK not installed. Call once from `create_app` after `configure_logging`.
Three tests cover no-DSN, DSN-without-SDK (warns), DSN-with-mock-SDK (init).

### TASK-022 — API token lifecycle — DONE
Access tokens stay stateless signed tokens (15 min TTL). Refresh tokens
added: 30-day TTL, jti tracked in `refresh_tokens` table, rotation on
`/api/auth/refresh` (old token revoked, new pair issued), revocation on
admin password-change via `revoke_user_refresh_tokens`. Migration
`20260804_02_refresh_tokens` adds the table. Seven tests cover login/
register return refresh, refresh issues new pair, rotation revokes old
token, missing/garbage rejected, revoked-after-password-change rejected.

### TASK-023 — `translator.py` location — DONE
Moved to `app/integrations/translator.py`. All importers updated
(api.py, utils/i18n.py, tests). .dockerignore updated. STRUCTURE.md,
CLI docs, and README references point to the new path.

### TASK-024 — Backups — DONE
`scripts/backup.sh` dumps the PostgreSQL DB to a timestamped file and prunes
dumps older than `BACKUP_RETENTION_DAYS` (default 14). Reads `DATABASE_URL`
or individual `PG*` vars; gzips by default; safe for cron. README documents
usage + cron example. No secrets in the script — connection details come from
env. Restore verification is still the operator's responsibility (documented).

---

# P3 — Low (unchanged from before, now includes)

## TASK-009 — Gamification (see above, blocked on TASK-016)
## TASK-010 — Smart Planner (see above)

---

# Planned — production hardening, phase 2 + UI migration

The items below are the next wave. They are ordered: backend/production first,
then the React/Next.js UI migration. See `.ai/ROADMAP.md` for the phased plan
and `.ai/PLAN_REACT_MIGRATION.md` for the frontend migration design. New
pillars (deployment + DB init, RBAC, logging + audit, replication readiness)
are added as phases 3–6 below.

## P4 — Backend production hardening (priority 1, roadmap phase 2)

### TASK-025 — Redis caching layer before the database
Add a Redis cache between read paths and PostgreSQL so hot queries (course list,
major list, statistics dashboard, translator availability) stop hitting the DB
on every request. `docker-compose.yml` already ships a Redis service; wire it
up as a cache. Use a thin wrapper (no heavy framework) with TTLs and explicit
invalidation keys on writes. Requirements: `redis>=5.0` (async optional later).
**Dependency: now blocked on TASK-039 (DB access layer) so invalidation hooks
sit at the data layer, not scattered across routes.** Tasks:
- Add `REDIS_URL` to `app/config.py` (distinct from `RATELIMIT_STORAGE_URI`).
- Add `app/extensions.py` a shared `cache` client bound to `REDIS_URL`.
- Add `app/utils/caching.py` with `cached(key, ttl)` decorator + `invalidate(key)`.
- Cache `all_courses_list()`, `majors_for_template()`, `is_available_cached()`
  (move the ad-hoc TTL cache onto Redis), and the per-user statistics payload.
- Invalidate on admin major/course create/delete and on task writes (through
  the data access layer).
- Graceful degradation: if Redis is down, fall through to the DB, never crash.
- Tests: cache miss/hit, invalidation, TTL expiry, and Redis-down passthrough.

### TASK-026 — REST API gaps for an SPA client
The `/api/*` surface is usable today but missing endpoints a React/Next.js
client needs. Add:
- `GET /api/me` — current user profile (id, username, fullname, theme, is_admin).
- `PUT /api/me` — update profile (fullname, theme; password change with current
  password verification).
- `GET /api/courses`, `GET /api/majors` — read-only list endpoints (admin needs
  write variants: `POST/PUT/DELETE /api/courses`, `/api/majors` guarded by
  `is_admin`).
- `POST /api/auth/logout` — revoke the presented refresh token (single-session
  logout; `revoke_user_refresh_tokens` is the logout-everywhere hammer).
- Pagination on list endpoints beyond tasks (courses, sessions) where useful.
- Tests for every new route, mirroring `TestAuthAPI` / `TestTasksAPI`.

### TASK-027 — Stats correctness: StudySession as the hours signal
Now that sessions are wired (TASK-016 DONE), move statistics from
`Task.created_at` + `Task.hours` to `StudySession.started_at` +
`StudySession.duration`. The current `sum(task.hours)` aggregation measures
the wrong date and double-counts. Replace with SQL aggregation over
`study_sessions` joined to the user's tasks:
`COALESCE(SUM(study_sessions.duration), 0)` grouped by date. Update
`services/statistics.py`, `routes/admin.py`, `/api/statistics/dashboard`, and
the dashboard/admin templates to read from the new numbers. Keep a fallback
to legacy `Task.hours` while backfilling, if needed, behind a config flag.
Decide on backfill: existing rows have `duration` but no `started_at` session
rows, so either keep legacy fallback for pre-cutover data or accept a one-time
reset of historical hours. **Lands after TASK-025 so the new stats path is
cached from day one; invalidate on session stop.**

### TASK-028 — Health/readiness endpoints — DONE
Add `GET /healthz` (liveness, no DB check, always 200 if process is up) and
`GET /readyz` (readiness, runs `SELECT 1` against PostgreSQL, 503 on failure).
Both exempt from auth and CSRF. Needed for container orchestrators and
load balancers behind the Docker deployment.

Done: app-level routes in `app/__init__.py` (`@csrf.exempt`, no auth);
`/healthz` 200 `{"status":"ok"}`, `/readyz` `SELECT 1` -> 200
`{"status":"ok","db":"ready"}` / 503 `{"status":"error","db":"unavailable"}`.
`tests/test_health.py` (3 tests). Full suite 194 pass, ruff clean.

### TASK-029 — Security headers + cookie hardening
Explicit security headers (`Strict-Transport-Security`, `Content-Security-Policy`,
`X-Content-Type-Options`, `Referrer-Policy`) via an `after_request` hook or
`flask-talisman`. Lock the session cookie: `SESSION_COOKIE_SECURE=True`,
`SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE=Lax` in production
config. Set a sane `PERMANENT_SESSION_LIFETIME`. CSP must allow Bootstrap,
Chart.js, and the inline scripts the templates currently use — start permissive
and tighten after the UI migration.

### TASK-030 — Docker migration runner safety
The Dockerfile runs `flask db upgrade` before gunicorn. Under multiple replicas
this races. Options: (a) a one-shot init container that runs migrations and
exits before app containers start, (b) a distributed lock around the upgrade
on boot. Document the chosen approach in README + STRUCTURE.md. Low risk at
current single-replica deploy, but must be decided before scaling.
**Superseded by TASK-034 (idempotent DB initialization at startup) — fold this
scope into TASK-034; keep this entry for traceability.**

### TASK-031 — CI quality uplift — DONE
Matrix expanded to Python 3.12 + 3.13 (fail-fast off). `pytest --cov` with
an 85% floor (measured 92.43% at landing; ratchet up over time). New
`test-postgresql` job runs the suite against a postgres:16 service
container via `TEST_DATABASE_URL` (env seam added to TestConfig). `ruff
format --check` intentionally skipped — no formatter adopted yet. Bonus
bug fix bundled: CI triggers watched `master` while the default branch is
`trunk`, so CI had not run since 2026-08-04; triggers now include `trunk`.

## P5 — UI/UX migration (priority 3, roadmap phase 7, after P4 + new phases)

### TASK-032 — Next.js + shadcn/ui frontend, phase 1 (proof of concept)
Introduce a `frontend/` directory with a Next.js 15 (App Router) client using
TypeScript, Tailwind CSS, and shadcn/ui. Phase 1 scope: a working dashboard
route that lists tasks from `/api/tasks` and can create/toggle/delete one.
This proves the API contract, auth flow, RTL/i18n, and shadcn setup before
migrating everything. Do NOT remove the Jinja templates yet — both UIs run
in parallel behind a route prefix during the migration. **RBAC role dashboards
(Developer/Admin/Manager/Student) are added in migration phase 3 — see
`.ai/PLAN_REACT_MIGRATION.md`.**

---

# P6 — Deployment + idempotent DB initialization (roadmap phase 3, priority 1)

## TASK-033 — OS-independent Docker hardening
Depends on: TASK-020 DONE.
- Confirm `Dockerfile` + `docker-compose.yml` run unchanged on Linux, macOS,
  Windows (Docker Desktop). No host-path assumptions that break cross-OS.
- Pin image digests for reproducible builds; run as a non-root user inside the
  container.
- Healthcheck wired to `/healthz` (TASK-028); compose `depends_on: condition:
  service_healthy` for postgres + redis before the app starts.
- Env-var driven config (no secrets in images); `.env.example` documents every
  var. Optional separate compose files for dev vs prod overrides.
- Tests: a CI job that builds the image and runs `docker compose up` against a
  throwaway postgres to confirm boot.

## TASK-034 — Idempotent DB initialization at startup
Depends on: TASK-033. Supersedes TASK-030 (fold its scope in).
- On boot: (1) connect to `DATABASE_URL`; (2) if the database does not exist,
  create it via a bootstrap connection to the `postgres` db +
  `CREATE DATABASE`; (3) run `flask db upgrade`; (4) run `seed-reference-data`
  idempotently.
- Seeding must be idempotent: `seed_reference_data()` upserts by `key` today —
  extend the guarantee to all base data and document which data is seed vs.
  user-created. Never re-create or duplicate user data. Specify default/seed
  data set (reference majors/courses; no admin account — keep security call).
- Under multiple replicas, migrations + seeding must not race: a one-shot
  init container (compose `init` service running migrations + seed, exiting
  before app containers start) OR a distributed advisory lock around the
  upgrade. Choose one; document in README + STRUCTURE.md.
- Re-run safety: a second `docker compose up` changes nothing (migrations are
  no-op, seeding upserts, no duplicate rows).

---

# P7 — RBAC: roles, permissions, API guards (roadmap phase 4, priority 1)

## TASK-037 — RBAC model — roles + permissions tables + migration
Depends on: —.
- New tables: `roles`, `permissions`, `role_permissions` (M:N), `user_roles`
  (M:N). A simpler `users.role` enum + `permissions` bitmask is acceptable if
  the matrix is small — decide during design, but the model must allow adding
  a new role or permission without a rewrite.
- Four roles: **Developer** (superuser — infra + all data, bypasses checks),
  **Admin** (system administrator — system config, users, majors/courses,
  system stats), **Manager** (CRM — view student status, dashboards, reports,
  logs, student data management; no system config), **Student** (lowest — own
  tasks CRUD, study sessions / time tracking, own results only).
- Migration preserves existing access: users with `is_admin=True` become
  `Admin`; all others become `Student`. Backfill in the migration; keep legacy
  `is_admin` column until confirmation (project convention).
- Permission granularity: Read / Create / Update / Delete per resource
  (users, majors, courses, tasks, study_sessions, statistics, logs, system).

## TASK-038 — Permission matrix + API-level guards
Depends on: TASK-037.
- Replace `admin_required` with `permission_required("resource:action")`.
  Existing admin routes map to `users:read`, `users:update`, `majors:*`,
  `courses:*`, `system:read`.
- Every `/api/*` route declares its required permission(s).
- Admin vs Manager distinction: Admin owns system config + roles; Manager owns
  CRM (student status, reports, logs, student data) but cannot alter system
  config or roles.
- Extensibility: adding a role = insert `roles` + `role_permissions`; adding a
  permission = insert `permissions` + attach to roles. No guard-decorator code
  change unless a new resource type appears.
- Tests: each role × resource × action (allow + deny).

---

# P8 — Logging DB + audit trail (roadmap phase 5, priority 2)

## TASK-035 — Independent logging database + structured log routing
Depends on: TASK-037 (actor identity for log records).
- A second database (or separate schema) for application + access logs,
  distinct from the business DB. Connection via `LOG_DATABASE_URL` (falls
  back to the main DB if unset, so dev stays single-DB).
- Structured logs (TASK-021 JSON formatter) write to this DB as well as stdout.
  Retention policy: configurable TTL, prune old log rows. Volume controls:
  log采样 for high-frequency events, cap row size.

## TASK-036 — Audit trail — generic audit log + before/after capture
Depends on: TASK-035, TASK-037, TASK-039 (hook mutations in the data layer).
- Generic `audit_log` table (preferred over one per business table). Columns:
  `id`, `actor_user_id`, `actor_role`, `session_id`, `request_id`, `user_ip`,
  `action` (e.g. `task.update`), `resource_type`, `resource_id`, `before`
  (JSONB), `after` (JSONB), `status` (success/failed), `error`, `created_at`,
  `user_agent`. Specify which extra columns a production-ready system needs.
- Capture before/after for update; full snapshot for create/delete.
- Hook mutations in the data access layer (TASK-039) so every write emits an
  audit record — not scattered through routes.
- Manager role can read audit logs (CRM visibility); Student cannot.

---

# P9 — Replication readiness — DB access layer (roadmap phase 6, priority 2)

## TASK-039 — Database Access Layer + read/write split config
Depends on — (architectural; lands before TASK-025 cache + TASK-036 audit so
both hook at the data layer).
- Introduce a repository / data-access layer between services/routes and
  SQLAlchemy. Routes/services call repositories (`TaskRepo.list(...)`,
  `TaskRepo.create(...)`) which own `db.session` usage. All direct
  `Task.query` / `db.session` usage in routes and services is removed.
- Connection config supports independent primary + replica URIs:
  `DATABASE_URL` (primary, read+write) and optional `DATABASE_REPLICA_URLS`
  (comma-separated read replicas). With no replica configured, all reads go
  to the primary.
- Logical read/write split at the data-access layer: read methods may target a
  replica session, write methods always target the primary. Business logic is
  not bound to a specific connection.
- Document consistency limits: replication lag, read-after-write expectations
  (route read-after-write to the primary, or accept eventual consistency).
- No failover / HA now; architecture must not block adding it later.
- Docker/config must not require a major rewrite for primary/replica topology.
- Demonstrated with a unit test even though no replica exists yet.

---

# P10 — UI issues found during automated screenshot review (2026-08-24)

Found by the `project-showcase` skill (Playwright capture of the running app,
desktop 1440x900 + mobile 390x844). Evidence: `docs/screenshots/*.png`
manifest warnings. Fix and re-capture to verify.

## TASK-040 — No public landing page; `/` redirects to `/login`
- Anonymous visit to `/` redirects straight to `/login` — there is no
  public-facing landing/home page describing the product.
- Decide: either a real marketing landing page (product name, features, CTA
  to register/login), or keep the redirect but document it as intentional.
- If a landing page is added: it must be i18n-aware (fa/en via `t()`), work
  in both RTL/LTR, and link to `/register` and `/login`.
- Affects README screenshots too — currently every anonymous capture shows
  the login form, which undersells the project.

## TASK-041 — Horizontal overflow on Persian (RTL) pages at mobile width
- Manifest flagged `horizontal overflow detected` on `/login` and `/` (fa
  locale) at 390px viewport; the English pages did not flag.
- Likely culprit(s): a fixed-width element or long unbreakable string in
  `templates/login.html` / `templates/base.html` under RTL direction.
- Reproduce with browser devtools at 390x844, fa locale; find the offending
  element (check fixed widths, `min-width`, long words without
  `overflow-wrap`).
- Acceptance: zero horizontal scroll at 390px in both fa and en locales;
  verify by re-running the screenshot manifest (`project-showcase` skill) or
  a small Playwright check asserting
  `document.documentElement.scrollWidth <= window.innerWidth`.

## TASK-042 — Remove/reset demo user from local dev DB before any shared capture
- During the screenshot session a `demo` user (password `Demo1234!`) was
  created in the local dev database for authenticated captures.
- Before publishing screenshots anywhere or sharing the dev DB dump, delete
  it or rotate the password:
  `DELETE FROM users WHERE username = 'demo';`
- Longer term: consider seeding an explicit throwaway user via the
  idempotent seeding work (TASK-034) instead of ad-hoc inserts.
