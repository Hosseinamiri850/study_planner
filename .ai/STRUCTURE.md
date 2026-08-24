# Study Planner Project Structure

_Last reviewed 2026-08-10 against the actual codebase. See `.ai/TODO.md` for
what's still open and `.ai/ROADMAP.md` for the phased plan._

## Overview

Study Planner is a Flask-based productivity application that helps users
manage courses, tasks, and study progress.

Current stack:

Backend:
- Python 3.10+
- Flask 3.0
- SQLAlchemy 2.0 (via Flask-SQLAlchemy)
- Alembic (via Flask-Migrate)

Database:
- PostgreSQL 14+

Frontend:
- Server-rendered Jinja templates (production UI today)
- Bootstrap 5
- Vanilla JavaScript (no build step)
- _Target: Next.js 15 + TypeScript + Tailwind + shadcn/ui — see
  `.ai/PLAN_REACT_MIGRATION.md`_

Visualization:
- Chart.js (replaced by recharts/shadcn in the React UI)

Translation:
- LibreTranslate (self-hosted or public instance), integrated via
  `app/integrations/translator.py`

i18n:
- Custom JSON locale system (`locales/fa.json`, `locales/en.json`), RTL/LTR

Deployment:
- Docker (app + PostgreSQL 16 + Redis), `docker-compose.yml`
- Gunicorn in prod; `scripts/backup.sh` for pg_dump + retention

---

## Current Architecture — P0 refactor is DONE

The target architecture described below is what's in `trunk` today.

```
app/
  __init__.py     Application factory (create_app). No table creation at startup.
  config.py       Environment-only configuration (.env for local dev).
  extensions.py   db, migrate, csrf, limiter (Flask-SQLAlchemy, Flask-Migrate,
                  Flask-WTF CSRFProtect, Flask-Limiter).
  models/
    user.py       User
    course.py     Major, Course
    task.py       Task, StudySession
  routes/
    web.py        Browser routes, session-cookie auth: /, /login, /register,
                  /logout, /dashboard, /user/<username>, /toggle-theme,
                  /set-lang.
    admin.py       Browser routes, session + is_admin: /admin.
    api.py         JSON routes, Bearer-token auth: /api/auth/*, /api/tasks*,
                   /api/tasks/<id>/sessions*, /api/statistics/dashboard,
                   /api/translate, /api/translator-status.
  services/
    seed.py        Explicit reference-data seeding (majors/courses only — no
                   admin account created here).
    statistics.py  Read-model helpers for dashboard/admin stats.
  utils/
    auth.py        current_user(), login_required, admin_required,
                   api_auth_required, create_access_token,
                   issue_refresh_token, rotate_refresh_token.
    i18n.py        JSON-locale loader + `t()` translation helper + context
                   processor.
    validation.py  Dependency-free input validators.
    logging.py     JsonFormatter + configure_logging + init_sentry (no-op
                   without SENTRY_DSN).
  integrations/
    translator.py   LibreTranslate client (translate, auto-translate,
                    availability cache).
migrations/
  versions/
    20260723_01_initial_schema.py         Legacy table shapes.
    20260723_02_task_study_sessions.py    Task.status/estimated_hours/course_id,
                                           StudySession table, completion
                                           metadata.
    20260804_01_session_duration_nullable Session.duration nullable.
    20260804_02_refresh_tokens.py         RefreshToken table (jti revocation).
tests/             pytest suite: 191 tests — models, services, utils,
                   integrations, api/web/admin routes, CLI commands, rate
                   limiting, refresh-token rotation, Sentry init.
locales/           fa.json, en.json — source of truth for UI strings.
templates/         Jinja templates (dashboard.html 1039 lines, admin.html 598).
scripts/           backup.sh — pg_dump + gzip + retention prune.
Dockerfile, docker-compose.yml, .dockerignore  — app + Postgres + Redis compose.
.github/workflows/ci.yml  — ruff check + pytest on Python 3.13.
```

Design principles (still the goal, mostly achieved):

1. Separation of concerns — done: routes/services/models/utils are separate.
2. Single responsibility — mostly done; `web.py`'s `_handle_dashboard_action`
   is a multi-branch dispatcher that's grown past "one responsibility" and is
   a reasonable next target for a small refactor.
3. Explicit dependencies — done; config is env-only, no hidden globals besides
   the shared `db`/`csrf`/`migrate`/`limiter` extension instances (normal
   Flask pattern).
4. Testable components — done: API, model, service, and browser-route
   layers all tested (TASK-015).
5. API readiness — done; `/api/*` exists and is usable by a future SPA/mobile
   client independent of the server-rendered templates.

---

# What's NOT done yet (do not assume otherwise)

- **No RBAC.** Single `User.is_admin: bool` only. No Manager / Student /
  Developer roles, no permission tables, no fine-grained matrix. See
  TASK-037/038 (roadmap phase 4).
- **No audit trail.** Structured JSON logs exist (TASK-021) but no
  independent Logging DB and no before/after change history. See
  TASK-035/036 (phase 5).
- ~~**No DB initialization at startup.**~~ DONE (TASK-033/034): compose runs
  a one-shot `init` service (`flask db upgrade` + `seed-reference-data`,
  idempotent) that must complete before `app` starts; DB creation is handled
  by `POSTGRES_DB`. Plain `docker run` still migrates in the entrypoint CMD.
  Images are digest-pinned; the container runs as non-root `appuser`;
  healthcheck hits `/healthz`.
- ~~**No Database Access Layer separation.**~~ DONE (TASK-039): all
  route/service reads+writes go through `app/repositories/*`; read/write
  split seam via `DATABASE_REPLICA_URLS` (unset today — everything on the
  primary).
- **Stats still measure the wrong signal.** `StudySession` is wired (API +
  dashboard UI, TASK-016 DONE) but `services/statistics.py` still aggregates
  `Task.hours` by `Task.created_at`, not `StudySession.duration` by
  `started_at`. See TASK-027.
- ~~**Redis cache layer not wired.**~~ DONE (TASK-025, PR #17 pending at
  this writing): `REDIS_URL` enables the data cache over hot read models;
  unset = passthrough to the DB. Rate-limit storage remains separate via
  `RATELIMIT_STORAGE_URI`.
- ~~**Security headers + cookie hardening**~~ DONE (TASK-029, PR #18):
  HSTS/CSP/nosniff/Referrer-Policy on every response; cookie HttpOnly +
  SameSite=Lax always, Secure env-gated.
- **Health endpoints** done (TASK-028).
- **Frontend migration** not started. See `.ai/PLAN_REACT_MIGRATION.md`.

---

# Database Structure (current)

```
User 1──* Task *──1 Course *──1 Major
Task 1──* StudySession   (wired — API start/stop, dashboard UI)
User 1──* RefreshToken   (jti revocation tracking)
```

Legacy columns retained on `Task` for compatibility during the transition:
`course_key` (string, alongside the new `course_id` FK), `hours` (alongside
`estimated_hours`), `done` (alongside `status`). Legacy `User.is_admin`
remains alongside the target RBAC role model until confirmation.

Target additions (roadmap phases 4–5):

```
Role *──* Permission          (RBAC)
User *──* Role                (user_roles)
Role *──* Permission          (role_permissions)
AuditLog                     (generic audit table)
```

Future (not started, low priority — see TODO P3): Category, Achievement,
Notification.

---

# Target architecture (roadmap phases 2–7)

See `.ai/ROADMAP.md` for ordering and `.ai/DESIGN.md` for the full target
system diagram. Summary:

- **Phase 2** — backend production hardening: Redis cache, REST API gaps,
  stats signal correction, health endpoints, security headers, Docker
  migration safety, CI uplift.
- **Phase 3** — OS-independent Docker + idempotent DB initialization at
  startup.
- **Phase 4** — RBAC roles + permissions + API guards (Developer / Admin /
  Manager / Student).
- **Phase 5** — independent Logging DB + generic audit trail (before/after
  JSONB).
- **Phase 6** — Database Access Layer + read/write split seam for future
  PostgreSQL Read Replica.
- **Phase 7** — frontend migration to Next.js + shadcn/ui with role-specific
  dashboards.
