# Project Memory

## Project

Name:
Study Planner


## Current Status

_Updated 2026-07 after a full code review against `trunk`._

The P0 architectural refactor (application factory, blueprints, models/services
split, Alembic migrations, REST API) is complete and verified in code. The
project is no longer "needs restructuring" — it's "structured, needs
production hardening." See `.ai/TODO.md` for the current prioritized backlog
and `CLAUDE.md` (repo root) for the list of known issues an assistant should
keep in mind before touching this code.

Concretely, before this can hold real users it needs: an admin bootstrap
mechanism (there is currently no way to create the first admin — see TODO
TASK-011), a fix for a blocking network call that runs on every page render
(TODO TASK-012), rate limiting on auth endpoints (TODO TASK-014), and a README
pass to remove stale sections that still describe the pre-refactor behavior
(TODO TASK-013).


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