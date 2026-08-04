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
