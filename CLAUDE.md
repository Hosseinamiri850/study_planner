# CLAUDE.md

Instructions for Claude (and Claude Code) when working in this repository.
This file supersedes `.ai/GPT.md`, which was written for a different assistant
and is now out of date — see `.ai/STRUCTURE.md` for why.

## What this project is

Study Planner — a Flask + PostgreSQL web app that helps students track courses,
tasks, and study hours, with full Persian (RTL) / English (LTR) i18n. Server-rendered
Bootstrap frontend today; a JSON REST API exists under `/api/*` to support a future
SPA or mobile client. See `README.md` for the product feature list and `.ai/STRUCTURE.md`
for the technical architecture.

Current stage: **past the P0 foundation refactor, not yet production-hardened.**
Read `.ai/TODO.md` before starting any task — it's the live backlog, ordered by priority.

## Architecture (already in place — do not re-litigate)

```
app/
  __init__.py     Application factory (create_app). Registers blueprints,
                   extensions, the i18n context processor, and the
                   `seed-reference-data` CLI command.
  config.py       Config loaded ONLY from environment variables (.env for local dev).
  extensions.py   Shared Flask extension instances: db, migrate, csrf.
  models/         SQLAlchemy entities: User, Major, Course, Task, StudySession.
  routes/         Blueprints: web (browser, session auth), admin (browser, session
                   auth + is_admin), api (JSON, Bearer token auth).
  services/       Business/read logic: seed.py (explicit, never auto-run), statistics.py.
  utils/          auth.py (decorators + token helpers), i18n.py, validation.py.
migrations/       Alembic. Two revisions so far: 20260723_01 (initial), 20260723_02
                   (Task.status/estimated_hours/course_id + StudySession table).
translator.py     LibreTranslate integration. Lives at repo root, NOT under app/ —
                   this is a known inconsistency, see .ai/TODO.md TASK-011.
tests/            pytest, in-memory SQLite. Good fixture coverage in conftest.py.
```

Two parallel auth systems exist by design and must both keep working:
- **Browser**: Flask session cookie (`session["username"]`), CSRF-protected forms
  (`Flask-WTF` CSRFProtect is global; JSON API mutation routes use `@csrf.exempt`
  because they authenticate with a Bearer token instead).
- **API**: stateless signed token via `itsdangerous.URLSafeTimedSerializer`
  (`create_access_token` / `api_auth_required` in `app/utils/auth.py`), valid 24h.
  There is currently **no revocation** — see known issues below before building
  anything that assumes tokens can be invalidated (logout-everywhere, password-change
  invalidation, etc.).

## Working conventions

- Prefer small, incremental changes over rewrites. This codebase is intentionally
  compact (~950 lines of Python) and terse — match the existing style rather than
  expanding it into a framework-heavy shape.
- Before editing: read the file and its direct callers. `app/routes/web.py` and
  `app/routes/admin.py` both import `_create_major`/`_create_course` from `web.py` —
  don't duplicate that logic when touching either file.
- Database changes always go through Alembic: `flask --app app db migrate -m "..."`
  then review the generated file by hand (autogenerate misses some cases) before
  `flask --app app db upgrade`. Never add `db.create_all()` back into the app
  factory or request path — that was deliberately removed.
- Keep legacy columns (`Task.course_key`, `Task.hours`, `Task.done`) working
  alongside the newer normalized ones (`course_id`, `estimated_hours`, `status`)
  until there's an explicit decision + migration to drop them. Don't silently
  stop writing to one side.
- New backend behavior that a mobile/SPA client would need goes in `app/routes/api.py`
  with a matching test in `tests/test_routes_api.py`. Don't let the browser routes
  and the API drift into different feature sets without a reason.
- i18n: user-facing strings go in `locales/fa.json` / `locales/en.json` via `t("key.path")`,
  never hardcoded in templates or Python. Keep both files' keys in sync.
- Run `pytest` before considering any change done. Current suite: 72 tests, all
  passing, but it only covers `models/`, `services/`, `utils/`, and `api.py` —
  **`web.py` and `admin.py` (the actual browser UI, i.e. 100% of real users today)
  have zero test coverage.** Adding tests there is high-value, low-risk work.

## Known issues to keep in mind (see .ai/TODO.md for the prioritized version)

1. **No way to create an admin account.** `seed-reference-data` deliberately creates
   none (correct security call), but nothing replaced it — no CLI command, no promote
   route. This blocks first-run setup. Don't "fix" it by re-adding a default
   `admin`/`admin` seed.
2. **`translator_available()` runs on every single page render** (it's called from
   `inject_i18n`, which is a global `context_processor`) and makes a live HTTP
   request to LibreTranslate with a blocking timeout. If LibreTranslate is
   unset/unreachable, every page load pays that latency. Needs caching or an
   async/deferred check, not a per-request network call.
3. **`StudySession` is dead schema.** The model and migration exist; nothing in
   `routes/` or `services/` ever creates, reads, or updates one. Either wire up
   real session tracking (start/stop timer → duration) or don't keep extending
   a table nothing uses.
4. Stats in `services/statistics.py` and `routes/admin.py` compute week/month
   hours by looping over all of a user's tasks in Python for every day in range
   (`O(days × tasks)`), using `Task.created_at` (not `completed_at` or actual
   `StudySession` timestamps) as the "when were these hours logged" signal. Works
   fine at current scale; will not scale, and is arguably measuring the wrong date.
5. `README.md` has stale/contradictory sections — the architecture note at the top
   is accurate, but the Persian and English quick-start sections further down
   still describe the old "auto-creates tables, auto-seeds `admin`/`admin`" behavior
   that was intentionally removed. Fix docs, don't fix code to match old docs.
6. No rate limiting on `/login`, `/register`, `/api/auth/login`, `/api/auth/register`.
7. README says passwords are hashed with bcrypt; the code uses Werkzeug's default
   hasher (`generate_password_hash`/`check_password_hash`, not bcrypt). Harmless
   in practice, but fix the doc claim or actually switch to bcrypt — don't leave
   the mismatch.

## Never (per project decisions in .ai/MEMORY.md)

- Don't migrate off Flask or PostgreSQL.
- Don't reintroduce automatic table creation on app startup.
- Don't rewrite the whole app "while you're in there" — scope changes to the task.
- Don't add a frontend framework/SPA rewrite unprompted; the backend is being
  prepared for one, but the server-rendered UI is still the product today.
