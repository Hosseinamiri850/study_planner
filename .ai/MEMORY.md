# Project Memory

## Project

Name:
Study Planner


## Current Status

_Updated 2026-08-10 after a full code review against `trunk`._

The P0 architectural refactor (application factory, blueprints, models/services
split, Alembic migrations, REST API) is complete and verified in code.
Production hardening phase 1 (admin bootstrap CLI, translator availability
cache, README accuracy, rate limiting, browser-route tests, SQL stats
aggregation, pagination, CI, Docker, structured logging + Sentry, refresh
tokens, backups) is DONE — 191 tests, ruff clean. See `.ai/TODO.md` for the
current prioritized backlog (TASK-025..039 are the next wave),
`.ai/ROADMAP.md` for the phased plan (phases 2–7 cover backend hardening,
deployment + DB init, RBAC, logging/audit, replication readiness, and the
Next.js UI migration), and `PRD.md` for the product requirements + RBAC role
matrix.

Open work (do not assume done): RBAC roles/permissions (TASK-037/038),
independent Logging DB + audit trail (TASK-035/036), idempotent DB
initialization at startup (TASK-033/034), Database Access Layer for future
read-replica readiness (TASK-039), Redis cache layer (TASK-025), stats
correctness (TASK-027), health endpoints (TASK-028), security headers
(TASK-029), CI uplift (TASK-031), Next.js frontend PoC (TASK-032).


## Important Decisions


### Backend

Keep Flask.

Do not migrate to another backend framework.


### Database

Keep PostgreSQL.

Introduce migrations.


### Frontend

Keep current frontend initially.

Prepare backend for future SPA frontend.


---

# Avoid

Do not:

- rewrite everything
- introduce unnecessary frameworks
- create premature abstractions
- break existing user data


---

# Coding Style

Prefer:

- readable code
- explicit naming
- small functions
- clear modules


Avoid:

- giant files
- duplicated logic
- hidden side effects