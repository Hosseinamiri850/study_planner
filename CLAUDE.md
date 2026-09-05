# CLAUDE.md

Instructions for Claude (and Claude Code) when working in this repository.
This file supersedes `.ai/GPT.md`, which was written for a different assistant
and is now out of date — see `.ai/STRUCTURE.md` for why.

## What this project is

Study Planner — a Flask + PostgreSQL backend with a Next.js 15 (App Router) +
TypeScript + Tailwind v4 SPA as the primary client, plus a legacy server-rendered
Jinja/Bootstrap UI still in `templates/`. A JSON REST API under `/api/*` backs both
and is the contract for any future mobile client. See `README.md` for the product
feature list, `.ai/STRUCTURE.md` for the technical architecture, and
`docs/redesign/` for the frontend design system (the source of truth for UI work).

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
                   306 tests covering models/, services/, utils/, integrations/,
                   api.py, web.py, admin.py, CLI commands, rate limiting,
                   caching, repositories, refresh-token rotation, and Sentry init.
templates/        Legacy Jinja/Bootstrap UI — still functional, being phased out
                   by the Next.js SPA. Don't add new features here.
```

### Frontend (Next.js SPA — the primary client)

```
frontend/         Next.js 15 (App Router) + TypeScript + Tailwind v4 + shadcn-style
                  Radix primitives. Design system: docs/redesign/ (read before UI work).
  app/            Routes: / (redirect), /login, /register, /app (dashboard),
                  /app/profile, /app/admin, /app/forbidden, not-found.
                  API route handlers under app/api/* own the httpOnly refresh cookie.
  components/     ui.tsx (token-skinned primitives), app-shell, user-menu,
                  lang-switch, logomark, running-session-bar, course-progress-list,
                  stats-cards (StatsStrip + recharts), tasks-panel, toast,
                  confirm-dialog + task-form-dialog (Radix Dialog/AlertDialog).
  lib/            api.ts (typed client mirroring the Flask contract), auth-context
                  (in-memory access token + silent refresh), theme/lang contexts,
                  format.ts, validation.ts, errors.ts. i18n loads locales/*.json
                  synced from the backend's canonical files by scripts/sync-locales.mjs
                  (predev/prebuild) — never edit frontend/locales directly.
  public/fonts/   Self-hosted OFL: Vazirmatn variable (fa+latin body), Space Grotesk
                  variable (display/numerals). Licenses included.
```

Frontend rules (docs/redesign/04-design-system.md is authoritative):

- **Design tokens, not raw colors.** Surfaces/text/accent/status come from the
  semantic tokens in `frontend/app/globals.css` (`bg-surface-1`, `text-text-primary`,
  `border-border-subtle`, `rounded-control`, ...). Never hardcode slate/indigo/etc.
- **RTL safety is lint-enforced (error).** Physical horizontal Tailwind properties
  (`pl-/pr-/ml-/mr-/left-/right-/text-left/text-right`) are banned in app code —
  use logical properties (`ps-/pe-/ms-/me-/start-/end-/text-start/text-end`).
  Persian text never gets letter-spacing (use the `tracking-label` guard class).
- **Radix for behavior, tokens for skin.** Dialogs/menus use Radix (Dialog,
  AlertDialog, DropdownMenu) — never hand-rolled portals. All visual classes come
  from the token layer; don't reintroduce default shadcn styling.
- **Persian-first typography.** Vazirmatn for body, Space Grotesk `.font-display`
  with `tnum` for stat values and the live timer. Don't swap the font stack.
- Auth model (do not change): access token in memory only (React state, 15-min TTL);
  refresh token is an httpOnly cookie owned by the Next route handlers under
  `app/api/auth/*` — JavaScript never touches it. `middleware.ts` route-gating is
  UX routing, not a security boundary.
- Dev workflow: `npm run dev --prefix frontend` (proxies `/api/*` to Flask on
  127.0.0.1:5000 via the `/api/proxy/*` catch-all). **Never run `next build` while
  the dev server is up on Windows** — it corrupts the shared `.next` dir (ENOENT
  on `_buildManifest.js.tmp.*`); stop the dev server, build, restart.

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
  never hardcoded in templates, Python, or the SPA. Keep both files' keys in sync
  (frontend reads them via `frontend/lib/i18n` — run `npm run predev --prefix frontend`
  to re-sync after editing the canonical files).
- Run `pytest` before considering any backend change done (306 tests, all passing).
  For frontend changes, run `npm run typecheck --prefix frontend`,
  `npm run lint --prefix frontend`, and `next build` (with the dev server stopped) —
  and visually verify in the browser; see `docs/redesign/08-visual-qa.md` for the
  standard regression flows (register/login, task CRUD, session start/stop/reload
  restore, fa⇄EN dir flip, dark/light, mobile 375px).

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
- Don't add new features to the legacy Jinja templates (`templates/`) — the
  Next.js SPA is the product client now; anything user-facing goes through the
  API + SPA.
- Don't bypass or restyle over the design tokens / Radix primitives (no raw
  hex colors, no hand-rolled dialogs, no physical positioning properties).

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
