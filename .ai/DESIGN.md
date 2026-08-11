# System Design — Study Planner

_Last updated 2026-08-10. Architecture as of this roadmap revision. See
`.ai/ROADMAP.md` for the phased plan and `.ai/TODO.md` for task detail._

## Current System (shipped)

A Flask application with a factory pattern, blueprint-separated routes
(web, admin, api), a service layer, and a normalized PostgreSQL schema
managed by Alembic migrations (4 revisions). Structured JSON logging +
optional Sentry. Rate limiting on auth endpoints. Refresh-token rotation +
revocation. Docker (app + PostgreSQL + Redis). 191 tests, CI on Python 3.13.

```
Frontend (Jinja + Bootstrap)      ← production UI today
        │
        │  (future: Next.js SPA talks to /api/* only)
        │
REST API  (/api/*, JSON, Bearer access + refresh tokens)
        │
        │
Service Layer  (statistics, seed, translator)
        │
        │
Database Layer  (SQLAlchemy + Flask-Migrate/Alembic → PostgreSQL)
```

The server-rendered frontend is still the only client in production use — no
SPA or mobile app consumes the API yet.

## Target System (roadmap phases 2–7)

```
Frontend (Next.js + TS + shadcn/ui)   ← mounted under /app/*, parallel to Jinja
        │
REST API  (/api/*, RBAC permission_required("resource:action"))
        │
        │
Service Layer  (business logic; no direct db.session)
        │
        │
Data Access Layer  (repositories; owns db.session; read/write split seam)
   ├──→ Primary PostgreSQL   (writes + reads)
   ├──→ Read Replica(s)       (reads; future, config-driven)   [phase 6 seam]
   └──→ Redis cache          (cache-aside; hot reads)          [phase 2]
Logging DB                   (independent; app + access logs)  [phase 5]
Audit log table             (generic; before/after JSONB)     [phase 5]
```

### Layer responsibilities

- **Frontend.** Next.js App Router, TypeScript, shadcn/ui, Tailwind. RTL
  first-class. Auth: in-memory short-lived access token + httpOnly refresh
  cookie. Role-based UI (Developer/Admin/Manager/Student). Talks to `/api/*`
  only. See `.ai/PLAN_REACT_MIGRATION.md`.
- **REST API.** Every route declares a required permission
  (`permission_required("resource:action")`). JSON + Bearer access token +
  refresh-token rotation. RBAC enforced here (phase 4).
- **Service Layer.** Business logic. Does NOT touch `db.session` directly in
  the target architecture — calls the data access layer.
- **Data Access Layer (phase 6).** Repositories own all `db.session` usage.
  Read methods may target a replica session when `DATABASE_REPLICA_URLS` is
  configured; write methods always target the primary. This is the seam for
  caching (phase 2 cache-aside hooks here) and auditing (phase 5 mutation
  hooks here). With no replica configured, all reads go to the primary — no
  behavior change.
- **Logging DB (phase 5).** Independent connection (`LOG_DATABASE_URL`, falls
  back to main DB in dev). Structured logs routed here as well as stdout.
  Configurable retention/TTL and volume controls.
- **Audit log (phase 5).** Generic `audit_log` table (preferred over one log
  table per business table). Captures before/after JSONB for every mutation
  via data-access-layer hooks. Actor identity from RBAC (phase 4).

---

# Components

## Authentication
Responsible for: users, sessions, permissions (RBAC roles + permissions,
phase 4), refresh-token rotation + revocation, rate limiting.

## Task Management
Responsible for: courses, tasks, completion tracking, task CRUD + pagination.

## Study Tracking
Responsible for: study sessions (start/stop/duration), statistics (target
signal = `StudySession.duration` by `started_at`, phase 2 TASK-027),
productivity metrics. Wired (API + dashboard UI). Stats signal correction
pending.

## Analytics
Responsible for: dashboards, progress, trends, system statistics. Manager
(CRM) + Admin + Developer dashboards in the SPA (phase 7).

## RBAC (target — phase 4)
Roles: Developer (superuser), Admin (system config), Manager (CRM), Student
(self). Permissions: Read/Create/Update/Delete per resource, enforced at the
API layer. See `PRD.md` for the permission matrix.

## Audit (target — phase 5)
Generic `audit_log` table; before/after JSONB; actor + session + IP + request
id context. Mutation hook lives in the data access layer. Manager +
Developer + Admin can read; Student cannot.

## Caching (target — phase 2)
Redis cache-aside for hot reads. Invalidation on writes through the data
access layer. Graceful degradation to DB if Redis is down. See `PRD.md`.

---

# Database structure (current + target additions)

```
User 1──* Task *──1 Course *──1 Major
Task 1──* StudySession

Target additions (phases 4–5):
Role *──* Permission          (RBAC)
User *──* Role                (user_roles)
Role *──* Permission          (role_permissions)
AuditLog                     (generic audit table, phase 5)
RefreshToken                 (exists — jti revocation tracking)
```

Legacy columns retained on `Task` for compatibility during the transition:
`course_key` (alongside `course_id` FK), `hours` (alongside
`estimated_hours`), `done` (alongside `status`). Legacy `User.is_admin`
retained alongside the new RBAC role model until confirmation.

---

# Future Scalability

Architectural seam (phase 6): the data access layer separates business logic
from the DB connection so a PostgreSQL Read Replica can be added later without
a major rewrite. Read/write split is logical (reads may target a replica;
writes always primary). Consistency limits (replication lag, read-after-write)
documented in DESIGN + ROADMAP. No failover/HA now; the architecture does not
block adding it.

Possible future clients (beyond this roadmap): Web SPA (phase 7), mobile
applications, browser extension. Therefore business logic must not depend
directly on templates, and reads/writes must not be hard-bound to a single
connection.
