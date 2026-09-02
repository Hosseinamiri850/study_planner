# Study Planner

A bilingual (Persian/English) study planner for students: track courses, manage tasks, time your study sessions, and watch your hours accumulate across daily, weekly, and monthly views. Flask + PostgreSQL on the backend, a Next.js single-page frontend in front of it, both wrapped in full RTL/LTR i18n and dark/light theming.

| Dashboard (fa) | Login | Mobile |
| --- | --- | --- |
| ![Dashboard](docs/screenshots/dashboard-user-desktop.png) | ![Login](docs/screenshots/login-desktop.png) | ![Mobile](docs/screenshots/login-mobile.png) |

## Features

- **Task management per course** — create, edit, complete, and delete study tasks with priority levels (high / medium / low) and estimated hours.
- **Study sessions with a live timer** — start a session on any task; the timer survives page reloads (the running session is part of the task payload).
- **Statistics from real session data** — today/week/month study hours aggregated from `StudySession` records, plus per-course progress and interactive weekly/monthly charts.
- **Social view** — see other users' task counts and study hours for friendly comparison.
- **Admin panel** — manage majors and courses (the course catalog), with separate admin detection and API-side authorization.
- **Profile management** — update your display name and theme, change your password (which revokes all refresh tokens).
- **Full Persian ↔ English i18n** — RTL/LTR layout switching, language persisted per user, auto-translation of new major/course names via LibreTranslate (optional).
- **Dark/light theme** — saved per user in the database; guests get a localStorage fallback.

## Architecture

```text
┌────────────────────────┐         ┌─────────────────────────────┐
│  Next.js 15 (App      │  same-  │  Flask 3 API + app factory  │
│  Router, TypeScript,  │─ origin │  ├─ routes/    web · admin  │
│  Tailwind CSS v4)     │  proxy  │  │              api (JSON)   │
│  frontend/            │────────▶│  ├─ repositories/ (read/    │
│  - typed API client   │  fetch  │  │                 write seam)│
│  - httpOnly refresh   │         │  ├─ services/  statistics,  │
│    cookie (sp_refresh)│         │  │                 seed      │
│  - fa/en RTL UI       │         │  ├─ models/    SQLAlchemy   │
└────────────────────────┘         │  └─ migrations/ Alembic     │
                                   └──────────┬──────────────────┘
                                              │
                                   PostgreSQL 16 + Redis 7
```

- **Backend** (`app/`): Flask application factory with `web` (server-rendered browser routes, session + CSRF), `admin` (admin browser routes), and `api` blueprints (JSON REST, bearer-token auth). Data access is centralized in the **repository layer** (`app/repositories/`) behind a read/write session seam so a read replica can be enabled via config without touching route code.
- **Frontend** (`frontend/`): Next.js 15 App Router + TypeScript + Tailwind CSS. The browser never talks to Flask directly: Next route handlers under `app/api/**` proxy to Flask, attach/detach the httpOnly refresh-token cookie, and hand the short-lived access token to the client in memory only. This means **no CORS is needed** in development or production, and the 30-day refresh token is never readable by client JavaScript.
- **Auth model**: stateless signed access tokens (15 min, `itsdangerous` serializer) + revocable rotating refresh tokens (30 days, `jti`-tracked in the `refresh_tokens` table). Password change revokes every outstanding refresh token. Login, register, and refresh endpoints are rate-limited (5/min per IP) via Flask-Limiter.
- **Caching**: optional Redis layer (TASK-025) caches course/major read models with explicit invalidation on writes; graceful in-memory fallback when `REDIS_URL` is unset.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12+ · Flask 3.1 · SQLAlchemy 2 · Alembic |
| Frontend | Next.js 15 (App Router) · React 19 · TypeScript · Tailwind CSS 4 |
| Database | PostgreSQL 16 (SQLite for the test suite) |
| Cache / rate-limit store | Redis 7 (optional) |
| Auth | Bearer access tokens (15 min) + rotating refresh tokens (30 d) |
| i18n | Custom JSON locale files (`locales/fa.json`, `locales/en.json`) |
| Testing | pytest (306 tests, in-memory SQLite) + Playwright for docs captures |
| CI | GitHub Actions: lint, tests (3.12/3.13), PostgreSQL job, coverage gate, frontend build, Docker build/boot |
| Production server | Gunicorn (`wsgi.py`) behind Docker |
| Optional translation | LibreTranslate (self-hosted or public) |

## Requirements

- Python 3.12+
- Node.js 20+ and npm 11
- PostgreSQL 14+ (or use Docker, which brings its own)
- Redis 7 (optional — caching and shared rate-limit storage degrade gracefully without it)
- Git

## Quick Start (manual)

### 1. Clone and install

```bash
git clone https://github.com/Hosseinamiri850/study_planner.git
cd study_planner
pip install -r requirements.txt
```

### 2. Create the database

```bash
# psql or pgAdmin
CREATE DATABASE study_planner;
```

### 3. Configure environment

```bash
cp .env.example .env
```

Set at minimum (`.env` must never be committed):

```bash
SECRET_KEY=a-long-random-secret-string
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/study_planner
```

Optional but recommended in production:

```bash
# Cache + shared rate-limit storage (in-memory fallback otherwise)
REDIS_URL=redis://localhost:6379/0
RATELIMIT_STORAGE_URI=redis://localhost:6379/1

# Session cookies over TLS (behind an HTTPS proxy)
SESSION_COOKIE_SECURE=true

# Optional error monitoring
SENTRY_DSN=

# Optional auto-translation of major/course names
LIBRETRANSLATE_URL=http://localhost:5001
```

The full list of variables the backend reads is documented in [.env.example](.env.example).

### 4. Migrate and seed

```bash
flask --app app db upgrade          # create/update tables via Alembic
flask --app app seed-reference-data # optional: bundled majors + 13 CS courses
flask --app app create-admin <username>  # prompts for a password (hidden), hashes it
```

The app deliberately creates **no default admin account** and never auto-creates tables at startup — schema changes only happen through Alembic migrations, and admins only via the `create-admin` command (or `--promote` for an existing user).

### 5. Run the backend

```bash
python app.py
# or, production-style:
gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
```

Flask serves the API on port 5000 by default in dev.

### 6. Run the frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # optional: API_BASE_URL defaults to http://127.0.0.1:5000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Register a normal user or sign in as the admin you created.

## Quick Start (Docker)

Docker Compose brings up PostgreSQL, Redis, a one-shot **init** container (migrations + idempotent reference-data seeding), and the Flask app:

```bash
docker compose up --build --wait
```

- The `init` service runs `flask db upgrade` + `seed-reference-data` exactly once, exits, and only then does the `app` service start (`service_completed_successfully` dependency).
- Images are digest-pinned; the app container runs as a non-root user, serves via gunicorn on port **5000**, and answers `/healthz` (liveness) and `/readyz` (DB check) probes.

Create an admin inside the running container:

```bash
docker compose exec app flask --app app create-admin <username>
```

> The Compose stack starts the **backend** on port 5000. Run the Next.js frontend separately (step 6 above) — its `API_BASE_URL` default already points at `http://127.0.0.1:5000`.

## Database backups

`scripts/backup.sh` dumps the configured PostgreSQL database to a timestamped file and prunes dumps older than `BACKUP_RETENTION_DAYS` (default 14). Safe to run repeatedly; designed for cron.

```bash
# One-off (reads DATABASE_URL or PG* env vars):
DATABASE_URL=postgresql://user:pass@localhost:5432/study_planner \
  BACKUP_DIR=/var/backups/study_planner \
  ./scripts/backup.sh

# Cron — daily 03:17, 14-day retention:
17 3 * * * DATABASE_URL=... BACKUP_DIR=/var/backups/study_planner \
  /path/to/study_planner/scripts/backup.sh >> /var/log/study_planner_backup.log 2>&1
```

Set `GZIP=0` to skip gzip. Verify restores on a throwaway database before relying on this in production.

## Testing / linting / build

Backend (from the repo root):

```bash
pytest                       # 306 tests, in-memory SQLite
pytest --cov=app --cov-report=term-missing   # coverage (CI gates at 85%)
ruff check app/ tests/       # lint
```

Frontend (from `frontend/`):

```bash
npm run lint       # eslint
npm run typecheck  # tsc --noEmit
npm run build      # production build (13 routes)
```

CI (`.github/workflows/ci.yml`) runs lint + tests on Python 3.12/3.13, a PostgreSQL-backed test job, the coverage gate, the frontend typecheck/build, and a Docker build-and-boot job with health checks.

## Authentication model

Two parallel systems, both intentional:

- **Browser (server-rendered admin routes)**: Flask session cookie, CSRF-protected forms.
- **SPA (Next.js frontend + JSON API)**: the SPA holds a 15-minute access token **in memory only**; the 30-day refresh token lives in an `HttpOnly; SameSite=Lax` cookie managed by Next route handlers, and is **stripped from every JSON response body**. On app load the frontend transparently refreshes via `POST /api/auth/refresh` (which rotates the token). `POST /api/auth/logout` revokes the presented refresh token and is idempotent.

The API never trusts the browser session, and the SPA never touches the session cookie — each system stands alone.

## REST API overview

All protected endpoints expect `Authorization: Bearer <access_token>`. Errors are consistently shaped `{"error": "message"}` with appropriate status codes. When the access token expires, use the refresh pair instead of re-logging-in.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/auth/register` | Create a user; returns access token (refresh token → cookie via proxy) |
| POST | `/api/auth/login` | Sign in; same token shape |
| POST | `/api/auth/refresh` | Rotate refresh token; new access + refresh pair |
| POST | `/api/auth/logout` | Revoke the presented refresh token (idempotent, 204) |
| GET | `/api/me` | Current user (id, username, fullname, is_admin, theme) |
| PUT | `/api/me` | Update fullname / theme; password change revokes refresh tokens |
| GET / POST | `/api/tasks` | List (paginated, includes `open_session_id`) / create tasks |
| PUT / DELETE | `/api/tasks/:id` | Update / delete one owned task (404 for others') |
| POST | `/api/tasks/:id/sessions` | Start a study session (409 if one is already open) |
| POST | `/api/tasks/:id/sessions/:sid/stop` | Stop an open session |
| GET | `/api/tasks/:id/sessions` | Sessions for a task |
| GET | `/api/statistics/dashboard` | Aggregated stats from real session data |
| GET | `/api/courses` · `/api/majors` | Catalog reads (authenticated) |
| POST / PUT / DELETE | `/api/courses…`, `/api/majors…` | Admin-only catalog CRUD |
| POST | `/api/translate` | Auto-translate a name (optional LibreTranslate) |
| GET | `/healthz` · `/readyz` | Liveness / readiness probes |

## Admin functionality

Admins get the `/app/admin` screen in the SPA: create, rename, and delete majors and courses, with confirmation dialogs on destructive actions. Admin state comes from `is_admin` on `/api/me` and is used **only for UI gating** — every admin mutation is re-authorized server-side (`403` for non-admins), and catalog reads are available to all authenticated users. The server-rendered `/admin` blueprint remains for direct browser use.

## Project structure

```text
study_planner/
├── app/                    # Flask package
│   ├── __init__.py         # create_app factory + CLI commands
│   ├── config.py           # env-backed configuration
│   ├── extensions.py       # db, migrate, csrf, limiter
│   ├── models/             # User, Major, Course, Task, StudySession
│   ├── repositories/       # data access behind read/write session seam
│   ├── routes/             # web, admin, api blueprints
│   ├── services/           # statistics, seed
│   ├── integrations/       # LibreTranslate client
│   └── utils/              # auth, caching, i18n, logging, validation
├── frontend/               # Next.js 15 SPA (App Router, TypeScript, Tailwind)
│   ├── app/                # routes: /, /login, /register, /app, /app/admin, /app/profile
│   ├── app/api/            # route handlers proxying Flask (+ cookie handling)
│   ├── components/         # shared UI
│   ├── lib/                # typed API client, contexts (auth, lang, theme)
│   └── locales/            # synced copies of locales/{fa,en}.json
├── locales/                # fa.json / en.json — single source of truth for UI strings
├── migrations/             # Alembic revisions
├── templates/              # server-rendered admin/browser pages
├── tests/                  # pytest suite
├── scripts/backup.sh       # PostgreSQL backup with retention
├── docker-compose.yml      # db + redis + init + app
├── Dockerfile              # digest-pinned, non-root, healthchecked
└── docs/
    ├── user-guide.md       # end-user documentation
    ├── knowledge-graph.md  # architecture diagrams
    └── screenshots/        # real UI captures used in this README
```

## Internationalization

User-facing strings live in `locales/fa.json` and `locales/en.json` (keys synced; `frontend/locales/` is a generated copy). Language switching happens without losing page state; RTL is applied automatically for Persian. To add a language: copy `locales/en.json` → `locales/xx.json`, translate, and add `"xx"` to `SUPPORTED_LANGS` in `app/utils/i18n.py`.

## Known limitations / post-v1 items

- **No RBAC** — authorization is the single `User.is_admin` flag; no fine-grained roles or permission tables (TASK-037/038, planned post-v1).
- **No audit trail database** — structured JSON logs exist, but no independent audit log of before/after changes on core tables (TASK-035/036, post-v1).
- **Legacy columns retained** — `Task.course_key` / `hours` / `done` are kept alongside the normalized `course_id` / `estimated_hours` / `status` for pre-migration data compatibility, until an explicit decision + migration drops them.
- **LibreTranslate is optional** — without it, auto-translation is disabled and both language fields must be filled manually; the app works fully either way.
- **Docker Compose runs the backend only** — the Next.js frontend is deployed separately (see Quick Start).

## Contributing

Pull requests are welcome. For major changes, please open an issue first. Working conventions live in [CLAUDE.md](CLAUDE.md).

## License

MIT © [Hossein Amiri](https://github.com/Hosseinamiri850)
