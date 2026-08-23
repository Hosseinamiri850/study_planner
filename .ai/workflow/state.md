# Workflow State

The state file is the shared conversation between Implementer and Reviewer.
The Implementer writes the plan and status; the Reviewer reads it and writes
the verdict. Keep it short — long-form detail goes in `implementation-result.md`
(for the Implementer) and `reviews/latest.md` (for the Reviewer).

## Current state

**Status:** `IMPLEMENTATION_DONE — PENDING_REVIEW`
**Task:** TASK-025 — Redis caching layer before the database
**Implementer:** Claude (implementer role)
**Reviewer:** —
**Started:** 2026-08-24
**Last updated:** 2026-08-24

Branch: `feat/redis-cache-layer` (off trunk @ 84c95f2). 251 tests pass,
ruff clean. See `implementation-result.md`.

Note: TASK-039 was merged to trunk directly (84c95f2) on user instruction;
its review outcome is recorded in the history below.

## Current plan (TASK-025)

Goal: thin Redis cache in front of hot read paths, with explicit
invalidation on writes through the repository layer (which now exists thanks
to TASK-039 — hooks land at the data layer as the TODO requires).
Graceful degradation: Redis down → fall through to DB, never crash.

Files to add:
- `app/utils/caching.py` — `cache_get(key)`, `cache_set(key, value, ttl)`,
  `cache_delete(key)` + `cached(key, ttl)` decorator. JSON-serializes values.
  No-op passthrough when no REDIS_URL configured or redis unreachable.
- `tests/test_caching.py` — hit/miss/invalidation/TTL/Redis-down/fallback,
  plus route-level tests that cached reads are served + invalidated.

Files to modify:
- `app/config.py` — add `REDIS_URL = os.environ.get("REDIS_URL", "")`
  (distinct from RATELIMIT_STORAGE_URI per TODO).
- `app/extensions.py` — shared lazy `cache_client()` bound to REDIS_URL.
- `app/services/statistics.py` — cache `all_courses_list()` (key
  `courses:all`) and `majors_for_template()` (key `majors:template`);
  invalidate on course/major writes via repos.
- `app/integrations/translator.py` — move ad-hoc availability TTL cache onto
  Redis when available (keep in-memory fallback when REDIS_URL unset).
- `app/repositories/{course_repo,major_repo}.py` — invalidate
  `courses:all` / `majors:template` after create/delete writes.
- `docker-compose.yml` — set `REDIS_URL=redis://redis:6379/0` on app service
  (Redis service already shipped since TASK-020).

Per-user statistics payload: NOT cached in this task. It is per-user-keyed
and invalidated on every task write; with the current user count the DB
query is a single grouped SELECT already. Cache it when a real need shows
(avoid premature complexity; note for Reviewer if they disagree).

Tests must run without a live Redis (CI has none): fake client injected via
fixture; Redis-down path exercised by a client whose methods raise.

### 2026-08-24 — TASK-025 IMPLEMENTATION_DONE — PENDING_REVIEW
- `app/utils/caching.py`: cache_get/set/delete + `cached` decorator;
  no-op passthrough without REDIS_URL; graceful degradation on Redis errors.
- Cached read models: courses list + majors template (language-neutral rows,
  rendered per request). Translator availability moves onto Redis when set.
- Invalidation hooks in CourseRepo/MajorRepo writes (+ seeder commit path).
- docker-compose sets REDIS_URL. Tests: test_caching.py (13).
- Full suite 251 passed, ruff clean.

## Current plan (TASK-025)
