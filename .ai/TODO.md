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

## TASK-007 — Testing — PARTIALLY DONE
94 pytest tests covering models, services, utils, API routes. Zero coverage
of `web.py`/`admin.py` — the actual browser UI. See new TASK-015.

## TASK-008 — Docker Support — NOT STARTED
No `Dockerfile` or `docker-compose.yml` in the repo yet.

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

### TASK-016 — Decide the fate of StudySession
Either wire up real start/stop session tracking (so "hours studied" reflects
actual logged sessions instead of a one-shot `estimated_hours` field on task
creation/completion), or stop extending a table nothing uses. This decision
also blocks TASK-009 (Gamification/streaks) from being built on real data.

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
and `.ai/PLAN_REACT_MIGRATION.md` for the frontend migration design.

## P4 — Backend production hardening (priority 1)

### TASK-025 — Redis caching layer before the database
Add a Redis cache between read paths and PostgreSQL so hot queries (course list,
major list, statistics dashboard, translator availability) stop hitting the DB
on every request. `docker-compose.yml` already ships a Redis service; wire it
up as a cache. Use a thin wrapper (no heavy framework) with TTLs and explicit
invalidation keys on writes. Requirements: `redis>=5.0` (async optional later).
Tasks:
- Add `app/extensions.py` a shared `cache` client bound to `REDIS_URL`.
- Add `app/utils/caching.py` with `cached(key, ttl)` decorator + `invalidate(key)`.
- Cache `all_courses_list()`, `majors_for_template()`, `is_available_cached()`
  (move the ad-hoc TTL cache onto Redis), and the per-user statistics payload.
- Invalidate on admin major/course create/delete and on task writes.
- Tests: cache miss/hit, invalidation, and TTL expiry.

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
Move statistics from `Task.created_at` + `Task.hours` to `StudySession.started_at`
+ `StudySession.duration`. Now that sessions are wired (TASK-016), the Python
`sum(task.hours)` loops measure the wrong date and double-count. Replace with
SQL aggregation over `study_sessions` joined to the user's tasks:
`COALESCE(SUM(study_sessions.duration), 0)` grouped by date. Update
`services/statistics.py`, `routes/admin.py`, `/api/statistics/dashboard`, and
the dashboard/admin templates to read from the new numbers. Keep a fallback
to legacy `Task.hours` while backfilling, if needed, behind a config flag.
Decide on backfill: existing rows have `duration` but no `started_at` session
rows, so either keep legacy fallback for pre-cutover data or accept a one-time
reset of historical hours.

### TASK-028 — Health/readiness endpoints
Add `GET /healthz` (liveness, no DB check, always 200 if process is up) and
`GET /readyz` (readiness, runs `SELECT 1` against PostgreSQL, 503 on failure).
Both exempt from auth and CSRF. Needed for container orchestrators and
load balancers behind the Docker deployment.

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

### TASK-031 — CI quality uplift
- Expand matrix to Python 3.12 AND 3.13 (pyproject targets 3.12; CI only runs
  3.13 today).
- Add `pytest --cov` + a minimum coverage gate (start low, raise over time).
- Add `ruff format --check` step if formatting is adopted.
- Run the suite with SQLite (current) AND PostgreSQL service container so
  migration/tz behavior is exercised against the real DB.

## P5 — UI/UX migration (priority 2, after P4)

### TASK-032 — Next.js + shadcn/ui frontend, phase 1 (proof of concept)
Introduce a `frontend/` directory with a Next.js 15 (App Router) client using
TypeScript, Tailwind CSS, and shadcn/ui. Phase 1 scope: a working dashboard
route that lists tasks from `/api/tasks` and can create/toggle/delete one.
This proves the API contract, auth flow, RTL/i18n, and shadcn setup before
migrating everything. Do NOT remove the Jinja templates yet — both UIs run
in parallel behind a route prefix during the migration. See
`.ai/PLAN_REACT_MIGRATION.md` for the full phased design.
