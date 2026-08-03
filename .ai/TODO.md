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

### TASK-011 — Admin account bootstrap
There is currently **no way to create an admin user**: `seed-reference-data`
deliberately creates none (correct call — don't reverse it), and no CLI
command or promote-route exists to replace it. `README.md` claims an "audited
deployment/admin process" that doesn't actually exist in code.
Fix: add a `flask --app app create-admin <username>` CLI command (prompts
for password, hashes it, sets `is_admin=True`), document it, and update the
README sections that still describe the old `admin`/`admin` auto-seed.

### TASK-012 — Fix `translator_available()` on every page render
`inject_i18n` (a global `context_processor`, runs on every request) calls
`translator_available()`, which does a live blocking HTTP GET to
LibreTranslate with a timeout. If LibreTranslate is down or unset, every page
load pays that latency. Fix: cache the result with a short TTL (e.g. 30–60s)
or check it asynchronously from the frontend instead of blocking the render.

### TASK-013 — README accuracy pass
The architecture note at the top of `README.md` is accurate; the Persian and
English "Quick Start" sections further down still describe the old
auto-create-tables / auto-seed-`admin`/`admin` behavior. Also: README claims
bcrypt, code uses Werkzeug's default hasher — fix the doc or switch the
implementation, don't leave the mismatch. Rewrite Quick Start to match the
current migration-based flow, including the new `create-admin` command from
TASK-011.

## P1 — needed before real users / before scaling past a handful of people

### TASK-014 — Rate limiting on auth endpoints
`/login`, `/register`, `/api/auth/login`, `/api/auth/register` have no
throttling. Add Flask-Limiter (or equivalent) before any public deployment.

### TASK-015 — Test coverage for browser routes
Add `tests/test_routes_web.py` and `tests/test_routes_admin.py` covering
login/register/logout, dashboard task CRUD, theme toggle, language switch,
and the admin panel actions (delete user, change password, add/delete
major/course). This is the actual product surface today; it's currently the
least-tested part of the app.

### TASK-016 — Decide the fate of StudySession
Either wire up real start/stop session tracking (so "hours studied" reflects
actual logged sessions instead of a one-shot `estimated_hours` field on task
creation/completion), or stop extending a table nothing uses. This decision
also blocks TASK-009 (Gamification/streaks) from being built on real data.

### TASK-017 — Move statistics aggregation into SQL
`services/statistics.py` and `routes/admin.py` compute week/month hours by
looping over all of a user's or the system's tasks in Python for every day in
a range. Fine today; won't scale past a small user base, and the admin panel's
system-wide loop (`Task.query.filter_by(done=True).all()` then scanning 30
days in Python) is the worst offender. Replace with grouped SQL queries
(`func.sum`, `group_by(func.date(...))`).

### TASK-018 — Pagination
No pagination on the admin user list, the dashboard "other users" leaderboard,
or `/api/tasks`. Add it before the user count or task count grows past what
fits on one page.

### TASK-019 — CI pipeline
No `.github/workflows` exist. Add one that runs `pytest` and a linter
(ruff/flake8) on every PR — the repo's own PR-based workflow (2 open PRs at
last check) has no automated gate today.

## P2 — production hygiene

### TASK-020 — Docker (see TASK-008, same item, re-prioritized)
Dockerfile + docker-compose (app + Postgres) so local dev and prod match, and
new-contributor setup doesn't depend on manually installing/configuring
PostgreSQL.

### TASK-021 — Structured logging + error monitoring
Currently only `logging.warning`/`.error` calls in `translator.py`. Add
request-scoped structured logging and an error tracker (e.g. Sentry) so
production failures are visible without SSH-ing into the server.

### TASK-022 — API token lifecycle
Access tokens are stateless signed tokens with no revocation. Acceptable for
a v1, but there's no way to force-logout a compromised session or invalidate
tokens on password change. Needs a token-blacklist or a move to short-lived
tokens + refresh tokens before the API has real external clients.

### TASK-023 — `translator.py` location
Move `translator.py` under `app/` (e.g. `app/integrations/translator.py`) for
consistency with the rest of the P0 refactor, and add test coverage — it
currently has none.

### TASK-024 — Backups
No documented backup strategy for the PostgreSQL database. Needs one before
any deployment holds real user data.

---

# P3 — Low (unchanged from before, now includes)

## TASK-009 — Gamification (see above, blocked on TASK-016)
## TASK-010 — Smart Planner (see above)
