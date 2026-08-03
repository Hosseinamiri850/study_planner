# Study Planner Project Structure

_Last reviewed against the actual `trunk` codebase — see .ai/TODO.md for what's
still open._

## Overview

Study Planner is a Flask-based productivity application designed to help users
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
- Server-rendered Jinja templates
- Bootstrap 5
- Vanilla JavaScript (no build step)

Visualization:
- Chart.js

Translation:
- LibreTranslate (self-hosted or public instance), integrated via `app/integrations/translator.py`

---

# Current Architecture — P0 refactor is DONE

The target architecture described below is no longer aspirational; it's what's
in `trunk` today.

```
app/
  __init__.py     Application factory (create_app). No table creation at startup.
  config.py       Environment-only configuration (.env for local dev).
  extensions.py   db, migrate, csrf (Flask-SQLAlchemy, Flask-Migrate, Flask-WTF CSRFProtect).
  models/
    user.py       User
    course.py     Major, Course
    task.py       Task, StudySession
  routes/
    web.py        Browser routes, session-cookie auth: /, /login, /register, /logout,
                   /dashboard, /user/<username>, /toggle-theme, /set-lang.
    admin.py       Browser routes, session + is_admin: /admin.
    api.py         JSON routes, Bearer-token auth: /api/auth/*, /api/tasks*,
                   /api/statistics/dashboard, /api/translate.
  services/
    seed.py        Explicit reference-data seeding (majors/courses only — see
                   note below, no admin account is created here).
    statistics.py  Read-model helpers for dashboard/admin stats.
  utils/
    auth.py        current_user(), login_required, admin_required,
                   api_auth_required, create_access_token.
    i18n.py        JSON-locale loader + `t()` translation helper + context processor.
    validation.py  Dependency-free input validators.
migrations/
  versions/
    20260723_01_initial_schema.py       Legacy table shapes.
    20260723_02_task_study_sessions.py  Task.status/estimated_hours/course_id,
                                         StudySession table, completion metadata.
  integrations/
    translator.py                      LibreTranslate client (move from repo root — TASK-023 DONE).
tests/             pytest suite, 154 tests: models, services, utils, integrations,
                   api/web/admin routes, CLI commands, and rate limiting.
```

Design principles (still the goal, mostly achieved):

1. Separation of concerns — done: routes/services/models/utils are separate.
2. Single responsibility — mostly done; `web.py`'s `_handle_dashboard_action`
   is a multi-branch dispatcher that's grown past "one responsibility" and is
   a reasonable next target for a small refactor.
3. Explicit dependencies — done; config is env-only, no hidden globals besides
   the shared `db`/`csrf`/`migrate` extension instances (which is the normal
   Flask pattern).
4. Testable components — partially done; API/model/service layers are tested,
   browser routes are not.
5. API readiness — done; `/api/*` exists and is usable by a future SPA/mobile
   client independent of the server-rendered templates.

---

# What's NOT done yet (do not assume otherwise)

- No admin bootstrap mechanism (see TODO TASK-011).
- `StudySession` table exists but nothing writes to or reads from it.
- No rate limiting on auth endpoints.
- No Docker/CI.
- Stats aggregation happens in Python loops, not SQL — fine at current scale.

---

# Database Structure (current, not aspirational)

```
User 1──* Task *──1 Course *──1 Major
Task 1──* StudySession   (schema only — unused, see TODO)
```

Legacy columns retained on `Task` for compatibility during the transition:
`course_key` (string, alongside the new `course_id` FK), `hours` (alongside
`estimated_hours`), `done` (alongside `status`).

Future (not started, low priority — see TODO P3): Category, Achievement,
Notification.
