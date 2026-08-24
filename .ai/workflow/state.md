# Workflow State

The state file is the shared conversation between Implementer and Reviewer.
The Implementer writes the plan and status; the Reviewer reads it and writes
the verdict. Keep it short — long-form detail goes in `implementation-result.md`
(for the Implementer) and `reviews/latest.md` (for the Reviewer).

## Current state

**Status:** `IMPLEMENTATION_DONE — PENDING_REVIEW`
**Task:** TASK-031 — CI quality uplift
**Implementer:** Claude (implementer role)
**Reviewer:** —
**Started:** 2026-08-24
**Last updated:** 2026-08-24

Branch: `ci/quality-uplift` (off trunk @ 84c95f2). 238 tests pass,
coverage 92.43% vs 85% gate, ruff clean. See `implementation-result.md`.

Open PRs: #17 (TASK-025 Redis cache), #18 (TASK-029 security headers),
both pending review. TASK-027 waits on #17.

Note: TASK-039 was merged to trunk directly (84c95f2) on user instruction.

---

## History

_(Append a new block per task or per status change within a task.)_

### 2026-08-12 — Workflow initialized
- Created `.ai/agents/implementer.md`, `.ai/agents/reviewer.md`.
- Created `.ai/workflow/state.md`, `.ai/workflow/implementation-result.md`.
- Created `.ai/reviews/latest.md`.
- No application code modified. No project task started.

### 2026-08-12 — TASK-039 planned
- Plan written below; `DATABASE_REPLICA_URLS` added to config.

### 2026-08-24 — TASK-039 IMPLEMENTATION_DONE — PENDING_REVIEW
- Repos created: base, task, course, major, user, refresh_token.
- Routes (`api.py`, `web.py`, `admin.py`), services (`statistics.py`,
  `seed.py`), and the create-admin CLI refactored onto repos. Zero direct
  `db.session` / `*.query` left in routes + services.
- Tests: `test_repositories.py` (31) + `test_replication_seam.py` (8).
- Full suite 233 passed, ruff clean.

### 2026-08-24 — Review pass done; findings fixed; re-review requested
- Reviewer found 2 MAJOR + 3 MINOR + 5 NIT. All addressed same day:
  MAJOR seam mutate-after-read (get_for_write variants + replica-mode
  persistence tests); MAJOR legacy course_key drift on edit-with-no-match
  (repo writes submitted key; regression test). MINOR: atomic password
  change restored, replica session teardown, admin relationship reads via
  TaskRepo. NITs: dead code, redundant commit, weak asserts.
- Bonus finding confirmed: the issue_refresh_token commit fixes a pre-existing
  HEAD bug — register/login refresh tokens were never committed and rolled
  back at teardown under Flask-SQLAlchemy 3.x.
- Full suite 238 passed, ruff clean. Status back to PENDING_REVIEW.

## Current plan (TASK-039)

Goal: move all direct `db.session` / `*.query` usage out of routes and services
into a repository/data-access layer; add a config seam
(`DATABASE_REPLICA_URLS`) so a future PostgreSQL Read Replica can be wired
without a rewrite. No replica is implemented — only the seam + a unit test.

Files to add:
- `app/repositories/__init__.py` — re-export repos
- `app/repositories/base.py` — `Repo` base: `session` (read), `write_session`
  (always primary); read/write split seam via `DATABASE_REPLICA_URLS` config
- `app/repositories/task_repo.py` — TaskRepo: list/get/create/update/delete/
  toggle/active_session/start/stop/list_sessions
- `app/repositories/course_repo.py` — CourseRepo: find_by_id/key/major,
  list_all, all_courses_list, create, delete_preserve_tasks
- `app/repositories/major_repo.py` — MajorRepo: list, find_by_key,
  majors_for_template, create, delete
- `app/repositories/user_repo.py` — UserRepo: find_by_username, list_non_admin,
  list_admin, create, delete, update_password
- `app/repositories/session_repo.py` — not needed; sessions are a Task
  relationship. Reuse TaskRepo methods.
- `tests/test_repositories.py` — repo CRUD + list/pagination
- `tests/test_replication_seam.py` — read goes replica-session when configured;
  write always primary; defaults to primary when `DATABASE_REPLICA_URLS` unset

Files to refactor (remove direct `db.session`/`*.query`):
- `app/routes/api.py` — all Task/Course/User lookups + writes
- `app/routes/web.py` — dashboard action, login, register, view_user, theme
- `app/routes/admin.py` — admin panel + `_handle_admin_action` + system stats
- `app/services/statistics.py` — `get_user_stats`, `all_courses_list`,
  `course_stats`, `majors_for_template`
- `app/services/seed.py` — `seed_reference_data` (keep idempotent upsert style)
- `app/models/refresh_token.py` — `revoke_user_refresh_tokens` moves to
  `app/repositories/refresh_token_repo.py` (it owns the revoked-refresh write)
- `app/config.py` — add `DATABASE_REPLICA_URLS` (default "")

Conventions to keep:
- Legacy columns (`Task.course_key`, `Task.hours`, `Task.done`) keep being
  written alongside normalized ones. No silent drops.
- `db.create_all()` stays out of the factory (tests only). Repo layer uses
  `db.session` under the hood.
- Existing tests stay green without behavior change (public route/api surface
  unchanged). New tests cover the repos + seam.

Open question for Reviewer:
- `utils/auth.py::current_user` uses `User.query`. It is cross-cutting auth
  state, not a route or service business query. Plan: leave it direct (auth is
  not the "business logic" TASK-039 targets), OR move to UserRepo for
  consistency. I will leave it direct and flag it as a non-blocking note for
  the Reviewer; the TODO exit criterion targets "routes and services".
