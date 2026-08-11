# Task Index — Study Planner

_Last updated 2026-08-10. Flat index of all tasks with status, phase, and
dependencies. Detail lives in `.ai/TODO.md`; ordering and exit criteria in
`.ai/ROADMAP.md`._

## Status legend

- **DONE** — verified in code.
- **PARTIAL** — some sub-items done, some open (see TODO entry).
- **PLANNED** — designed, not started.
- **OPEN** — not started, no detailed design yet.

## Tasks

| ID | Phase | Status | Title | Depends on |
|----|-------|--------|-------|------------|
| TASK-001 | 1 | DONE | Application Factory Pattern | — |
| TASK-002 | 1 | DONE | Split Routes (web/admin/api blueprints) | — |
| TASK-003 | 1 | DONE | Database Migration (Alembic) | — |
| TASK-004 | 1 | PARTIAL | Security Hardening | — |
| TASK-005 | 1 | DONE | Database Model Improvement (schema) | — |
| TASK-006 | 1 | DONE | REST API Layer | — |
| TASK-007 | 1 | PARTIAL | Testing | — |
| TASK-008 | 1 | PLANNED | Docker Support (superseded by TASK-020) | — |
| TASK-009 | P3 | OPEN | Gamification | TASK-016 |
| TASK-010 | P3 | OPEN | Smart Planner | — |
| TASK-011 | 1 | DONE | Admin account bootstrap (CLI) | — |
| TASK-012 | 1 | DONE | Fix translator_available() per-page | — |
| TASK-013 | 1 | DONE | README accuracy pass | — |
| TASK-014 | 1 | DONE | Rate limiting on auth endpoints | — |
| TASK-015 | 1 | DONE | Test coverage for browser routes | — |
| TASK-016 | 1 | DONE | Wire up StudySession tracking | — |
| TASK-017 | 1 | DONE | Move statistics aggregation into SQL | — |
| TASK-018 | 1 | PARTIAL | Pagination (backend done, UI deferred) | — |
| TASK-019 | 1 | DONE | CI pipeline | — |
| TASK-020 | 1 | DONE | Docker | — |
| TASK-021 | 1 | DONE | Structured logging + error monitoring | — |
| TASK-022 | 1 | DONE | API token lifecycle (refresh tokens) | — |
| TASK-023 | 1 | DONE | translator.py location | — |
| TASK-024 | 1 | DONE | Backups | — |
| TASK-025 | 2 | PLANNED | Redis caching layer | TASK-039 |
| TASK-026 | 2 | PLANNED | REST API gaps for SPA | — |
| TASK-027 | 2 | PLANNED | Stats correctness: StudySession signal | TASK-016 DONE, TASK-025 |
| TASK-028 | 2 | DONE | /healthz + /readyz endpoints | — |
| TASK-029 | 2 | PLANNED | Security headers + cookie hardening | TASK-028 |
| TASK-030 | 3 | PLANNED | Docker migration runner safety | TASK-034 (folded) |
| TASK-031 | 2 | PLANNED | CI quality uplift | — |
| TASK-032 | 7 | PLANNED | Next.js + shadcn/ui frontend, phase 1 (PoC) | P4 + RBAC |
| TASK-033 | 3 | PLANNED | OS-independent Docker hardening | TASK-020 |
| TASK-034 | 3 | PLANNED | Idempotent DB initialization at startup | TASK-033 |
| TASK-035 | 5 | PLANNED | Independent logging DB + structured log routing | TASK-037 |
| TASK-036 | 5 | PLANNED | Audit trail — generic audit log + before/after | TASK-035, TASK-037, TASK-039 |
| TASK-037 | 4 | PLANNED | RBAC model — roles + permissions tables + migration | — |
| TASK-038 | 4 | PLANNED | Permission matrix + API-level guards | TASK-037 |
| TASK-039 | 6 | PLANNED | Database Access Layer + read/write split config | — |

## Phase summary

- **Phase 1** — Foundation. DONE (TASK-001..024).
- **Phase 2** — Backend production hardening. PLANNED (TASK-025..031).
- **Phase 3** — Deployment + idempotent DB initialization. PLANNED
  (TASK-033, TASK-034).
- **Phase 4** — RBAC: roles, permissions, API guards. PLANNED
  (TASK-037, TASK-038).
- **Phase 5** — Logging DB + audit trail. PLANNED (TASK-035, TASK-036).
- **Phase 6** — Replication readiness — DB access layer. PLANNED
  (TASK-039).
- **Phase 7** — Frontend migration to Next.js + shadcn/ui. PLANNED
  (TASK-032 + RBAC dashboards).
- **P3 (deferred)** — Gamification (TASK-009), Smart Planner (TASK-010).
