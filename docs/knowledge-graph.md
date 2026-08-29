# Study Planner — Knowledge Graph

Generated 2026-08-24 from `trunk` @ 688d987. Layers read top → bottom:
request entry points (routes) → business logic (services) → data access
(repositories) → ORM models → PostgreSQL. Cross-cutting concerns on the
right. Tests mirror the layer they cover.

## System architecture

```mermaid
flowchart TB
    subgraph Clients["Clients"]
        Browser["Browser<br/>(session cookie + CSRF)"]
        SPA["Future SPA / mobile<br/>(Bearer access token,<br/>refresh rotation)"]
        Orchestrator["Orchestrator / LB<br/>(health probes)"]
    end

    subgraph Flask["Flask app — create_app()"]
        direction TB

        subgraph Routes["Routes (blueprints)"]
            WEB["web_bp — routes/web.py<br/>login/register/dashboard/theme/view_user"]
            ADMIN["admin_bp — routes/admin.py<br/>admin panel, user+course mgmt, system stats"]
            API["api_bp — routes/api.py<br/>/api/auth/*, /api/tasks CRUD,<br/>study sessions, statistics, translate"]
            HEALTH["app-level: /healthz /readyz"]
            CLI["CLI: create-admin,<br/>seed-reference-data"]
        end

        subgraph Services["Services"]
            STATS["services/statistics.py<br/>get_user_stats, course_stats,<br/>all_courses_list (cached),<br/>majors_for_template (cached)"]
            SEED["services/seed.py<br/>idempotent reference-data upserts"]
        end

        subgraph Repos["Repositories (TASK-039 data-access layer)"]
            BASE["repositories/base.py<br/>read_session / write_session seam<br/>replica engine via DATABASE_REPLICA_URLS"]
            TASKREPO["TaskRepo<br/>tasks + study_sessions CRUD,<br/>pagination, hours-by-day SQL agg"]
            COURSEREPO["CourseRepo<br/>incl. delete_preserve_tasks<br/>(nulls course_id, keeps legacy key)<br/>+ cache invalidation"]
            MAJORREPO["MajorRepo<br/>incl. majors_for_template shape<br/>add_flush for seeder<br/>+ cache invalidation"]
            USERREPO["UserRepo<br/>find/create/delete/password/theme"]
            RTREPO["RefreshTokenRepo<br/>find_by_jti, issue,<br/>revoke_all_for_user"]
        end

        subgraph Models["SQLAlchemy models"]
            USER["User"]
            TASK["Task (+ StudySession)<br/>legacy cols: hours/done/course_key<br/>normalized: status/estimated_hours/course_id"]
            MAJOR["Major 1─* Course"]
            RT["RefreshToken<br/>jti-tracked, revocable, 30d"]
        end

        subgraph Utils["Cross-cutting utils"]
            AUTHU["utils/auth.py<br/>current_user, login/admin_required,<br/>access token sign/verify (15 min),<br/>refresh rotate (30 day jti)"]
            CACHEU["utils/caching.py (TASK-025)<br/>cache_get/set/delete, cached()<br/>no REDIS_URL = passthrough<br/>Redis-down = graceful degrade"]
            I18N["utils/i18n.py<br/>t(), inject_i18n context proc<br/>fa/en locales, RTL/LTR"]
            LOGU["utils/logging.py<br/>JSON formatter, Sentry init"]
            VAL["utils/validation.py<br/>username/password/priority/hours"]
        end

        EXT["extensions.py: db, migrate, csrf, limiter<br/>config.py: env-only config<br/>(SECRET_KEY, DB, replicas, REDIS_URL,<br/>cookie flags, CSP keys, Sentry)"]
    end

    subgraph Infra["Infrastructure"]
        PG[("PostgreSQL 16<br/>primary — all writes;<br/>reads when no replica set")]
        REPLICA[("Optional read replica<br/>(seam only today)")]
        REDIS[("Redis<br/>data cache db0<br/>rate-limit storage db1")]
        LT["LibreTranslate<br/>(optional translation)"]
    end

    Browser -->|"HTML forms"| WEB & ADMIN
    Browser -->|"fetch JSON"| API
    SPA -->|"Bearer"| API
    Orchestrator --> HEALTH

    WEB --> AUTHU & STATS
    ADMIN --> AUTHU & STATS & RTREPO
    API --> AUTHU
    CLI --> USERREPO & SEED

    STATS --> TASKREPO & COURSEREPO & MAJORREPO & CACHEU
    SEED --> MAJORREPO & COURSEREPO
    WEB & ADMIN & API --> TASKREPO & COURSEREPO & MAJORREPO & USERREPO & RTREPO
    AUTHU --> RTREPO & USERREPO

    TASKREPO & COURSEREPO & MAJORREPO & USERREPO & RTREPO --> BASE
    BASE -->|"write always"| PG
    BASE -.->|"reads when configured"| REPLICA
    CACHEU --> REDIS
    API -->|"translate"| LT
    I18N --> WEB & ADMIN
    LOGU --> Flask
```

## Data model + ownership rules

```mermaid
erDiagram
    User ||--o{ Task : owns
    User ||--o{ RefreshToken : "has sessions"
    Major ||--o{ Course : groups
    Course ||--o{ Task : "normalizes (course_id)"
    Task ||--o{ StudySession : "time tracking"

    User {
        int id PK
        string username UK "3-80 chars"
        string password "werkzeug scrypt hash"
        bool is_admin "legacy; RBAC in TASK-037"
        string theme "dark|light"
        date created_at
    }
    Major {
        int id PK
        string key UK
        string name_fa
        string name_en
    }
    Course {
        int id PK
        string key "legacy join key"
        string name_fa
        string name_en
        int major_id FK
    }
    Task {
        int id PK
        int user_id FK
        int course_id FK "nullable after course delete"
        string course_key "legacy, survives course delete"
        string title
        bool done "legacy"
        float hours "legacy, mirrors estimated_hours"
        string status "pending|completed"
        float estimated_hours
        date created_at "current stats signal (TASK-027 will move)"
        datetime completed_at
    }
    StudySession {
        int id PK
        int task_id FK "CASCADE"
        int duration "seconds, NULL while open"
        datetime started_at
        datetime ended_at
    }
    RefreshToken {
        int id PK
        int user_id FK "CASCADE"
        string jti UK "revocation handle"
        datetime expires_at "30 days"
        bool revoked
    }
```

**Legacy-column rule** (CLAUDE.md): `hours`↔`estimated_hours` and
`course_key` stay written together until an explicit migration drops them.
Course deletion nulls `course_id` but keeps `course_key` on task rows.

## Auth flows

```mermaid
flowchart LR
    subgraph BrowserAuth["Browser auth"]
        L1[login form] -->|"check_password_hash"| S1[(session cookie<br/>username, HttpOnly,<br/>SameSite=Lax, Secure opt-in)]
        S1 -->|"current_user()"| GU["@login_required / @admin_required"]
    end
    subgraph APIAuth["API auth"]
        L2[/api/auth/login or register/] --> AT["access token:<br/>URLSafeTimedSerializer, 15 min"]
        L2 --> RTI["refresh token:<br/>signed jti, 30 days, row in refresh_tokens"]
        AT -->|"Authorization: Bearer"| GU2["@api_auth_required"]
        RTI -->|"/api/auth/rotate"| ROT["revoke old jti,<br/>issue new pair (one tx)"]
        PWC["admin password change"] -->|"revoke_all_for_user"| RTI
    end
    RL["Flask-Limiter 5/min<br/>on all four auth endpoints"]:::sec
    classDef sec fill:#fee,stroke:#c33
```

## Caching + invalidation map (TASK-025)

```mermaid
flowchart LR
    subgraph Reads["Cached reads (TTL 300s safety net)"]
        C1["courses:all"] --- F1["_courses_rows_cached()<br/>language-neutral rows"]
        C2["majors:template"] --- F2["_majors_rows_cached()"]
        C3["translator:available"] --- F3["is_available_cached()<br/>60s polling TTL"]
    end
    subgraph Writes["Writers that invalidate"]
        W1["CourseRepo.create / delete_preserve_tasks"]
        W2["MajorRepo.create / delete / commit(seeder)"]
    end
    W1 -->|"delete both keys"| C1 & C2
    W2 -->|"delete both keys"| C1 & C2
    NAMES["Names rendered per request<br/>(display_name is session-scoped —<br/>never cached)"]:::note
    classDef note fill:#ffe,stroke:#a80
```

## CI pipeline

```mermaid
flowchart LR
    PUSH[push/PR to trunk] --> M1["lint-and-test matrix<br/>py3.12 + py3.13:<br/>ruff check + pytest --cov<br/>gate fail_under=85"]
    PUSH --> PGJ["test-postgresql<br/>postgres:16 service container<br/>TEST_DATABASE_URL seam<br/>NullPool + dispose teardown<br/>pytest-timeout 60s tripwire"]
    PUSH --> DK["docker-build-boot<br/>build image -> compose up --wait<br/>(init migrates + seeds first)<br/>probe /healthz /readyz<br/>re-run init = idempotency proof"]
```

## Deployment topology (compose)

```mermaid
flowchart LR
    INIT["init (one-shot)<br/>flask db upgrade + seed-reference-data<br/>exit 0 required"] --> APP["app (non-root, healthcheck /healthz)<br/>gunicorn wsgi:app, 4 workers"]
    DB[("db postgres:16-alpine<br/>digest-pinned")] --> INIT
    RD[("redis:7-alpine digest-pinned")] --> APP
    APP --> DB
    APP --> RD
```

## Layer dependency rules (enforced by convention)

1. **Routes never touch** `db.session` / `Model.query` — repositories only.
   Exception: `utils/auth.py` auth-state lookups (documented).
2. **Writes go through repos** → invalidation hooks live at the data layer,
   so routes cannot forget to bust caches.
3. **Mutate-after-read**: anything you will modify must load via
   `*Repo.get_for_write(...)` — reads may come from a replica session.
4. **Cache stores language-neutral rows**; names render per request.
5. **No auto table creation** outside tests (`db.create_all()` is
   test-fixture only); schema changes only via Alembic migrations.

## Test coverage map (259 tests)

| Test file | Covers |
|---|---|
| test_repositories.py | All five repos, CRUD + pagination + aggregation |
| test_replication_seam.py | Read/write split wiring, mutate-under-replica persistence |
| test_caching.py | Hit/miss/invalidation/TTL, dead-Redis degradation |
| test_routes_api.py | Full `/api/*` contract incl. refresh rotation |
| test_routes_web.py / admin.py | Browser flows incl. RBAC boundary (is_admin) |
| test_security_headers.py | Headers, CSP contents, cookie flags |
| test_rate_limiting.py | 5/min throttle behavior |
| test_cli.py | create-admin + seeding |
| test_health.py, test_logging.py | Probes, JSON logs, Sentry init |
| test_models/services/utils.py | Domain logic |

## Open roadmap (what the graph will grow)

- **TASK-027**: stats signal `Task.hours@created_at` → `StudySession.duration@started_at`
  (decision parked: backfill vs reset)
- **TASK-037/038**: RBAC roles/permissions replacing `is_admin`
- **TASK-035/036**: logging DB + audit trail hooking repos
- **TASK-026**: `/api/me`, `/api/courses`, logout endpoints
- **TASK-032**: Next.js/shadcn frontend consuming the same API
