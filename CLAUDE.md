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
  integrations/   translator.py — LibreTranslate integration (translate, auto-translate,
                   availability cache).
  utils/          auth.py (decorators + token helpers), i18n.py, validation.py.
migrations/       Alembic. Two revisions so far: 20260723_01 (initial), 20260723_02
                   (Task.status/estimated_hours/course_id + StudySession table).
tests/            pytest, in-memory SQLite. Good fixture coverage in conftest.py.
                   191 tests covering models/, services/, utils/, integrations/,
                   api.py, web.py, admin.py, CLI commands, rate limiting,
                   refresh-token rotation, and Sentry init.
```

Two parallel auth systems exist by design and must both keep working:
- **Browser**: Flask session cookie (`session["username"]`), CSRF-protected forms
  (`Flask-WTF` CSRFProtect is global; JSON API mutation routes use `@csrf.exempt`
  because they authenticate with a Bearer token instead).
- **API**: stateless signed access token via `itsdangerous.URLSafeTimedSerializer`
  (`create_access_token` / `api_auth_required` in `app/utils/auth.py`), valid 15
  min, plus a **revocable refresh token** (30 days, jti in the `refresh_tokens`
  table, rotated on `/api/auth/refresh`, revoked on admin password-change via
  `revoke_user_refresh_tokens`)..

## Working conventions

- **Comments must be in English.** No Persian/Farsi comments in code. Existing
  Persian comments should be translated to English when touched. User-facing
  strings still go through i18n (`locales/{fa,en}.json`); this rule is about
  code/docstring comments only.
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
- Run `pytest` before considering any change done. Current suite: 94 tests, all
  passing, but it only covers `models/`, `services/`, `utils/`, and `api.py` —
  **`web.py` and `admin.py` (the actual browser UI, i.e. 100% of real users today)
  have zero test coverage.** Adding tests there is high-value, low-risk work.

## Known issues to keep in mind (see .ai/TODO.md for the prioritized version)

1. **No RBAC.** Only `User.is_admin: bool`. No Manager/Student/Developer roles, no permission tables, no fine-grained API-level read/create/update/delete permission matrix. See `.ai/ROADMAP.md` phase 4 (TASK-037/038) and `PRD.md` for the role/permission matrix.
2. **No audit trail.** Structured JSON logs exist (TASK-021) but no independent Logging DB and no before/after change history on core tables. See TASK-035/036 (phase 5).
3. **No DB initialization at startup.** Docker entrypoint runs `flask db upgrade` but does not create the DB if missing and does not run idempotent seeding on boot. Re-run not guaranteed safe under multiple replicas. See TASK-033/034 (phase 3), which supersedes the older TASK-030 migration-runner-safety note.
4. Stats in `services/statistics.py` and `routes/admin.py` compute week/month hours via SQL aggregation over `Task.hours` grouped by `Task.created_at` (TASK-017 DONE) — but the *signal is wrong*: `StudySession` is now wired (TASK-016 DONE), so stats should aggregate `StudySession.duration` by `started_at`. See TASK-027.
5. `README.md` historically had stale/contradictory sections — the Quick Start (Persian + English) was reconciled to the migration-based flow in TASK-013, and the API table + structure blocks were updated to the 15-min access + 30-day refresh-token flow. Ongoing doc edits must stay consistent with `PRD.md`, `.ai/ROADMAP.md`, `.ai/DESIGN.md`, and `.ai/TODO.md`.
6. ~~No rate limiting on `/login`, `/register`, `/api/auth/login`, `/api/auth/register`.~~ DONE — Flask-Limiter throttles all auth endpoints at 5/min (TASK-014).
7. ~~README says passwords are hashed with bcrypt; the code uses Werkzeug's default hasher.~~ DONE — the bcrypt claim was removed in TASK-013; code uses Werkzeug `generate_password_hash`/`check_password_hash` (scrypt). Items marked with strikethrough are kept for history; do not re-litigate.

## Never (per project decisions in .ai/MEMORY.md)

- Don't migrate off Flask or PostgreSQL.
- Don't reintroduce automatic table creation on app startup.
- Don't rewrite the whole app "while you're in there" — scope changes to the task.
- Don't add a frontend framework/SPA rewrite unprompted; the backend is being
  prepared for one, but the server-rendered UI is still the product today.
