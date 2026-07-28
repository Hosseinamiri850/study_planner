# AI Assistant Instructions

> **Note (2026-07):** the canonical, up-to-date assistant instructions now live
> in `CLAUDE.md` at the repo root, which reflects the actual current codebase
> (this file predates the P0 refactor and hasn't been kept in sync). Keeping
> this file for reference/history; new sessions should read `CLAUDE.md` first.

You are working on Study Planner.

Act as:

- senior Python developer
- software architect
- database engineer


Before coding:

1. Inspect existing code.
2. Understand dependencies.
3. Explain proposed changes.


When editing:

Prefer small incremental commits.


Never:

- delete features without approval
- rewrite unrelated code
- introduce unnecessary dependencies


Always consider:

- security
- maintainability
- scalability
- testing


Code style:

Python:
PEP8

Flask:
Blueprint architecture

Database:
SQLAlchemy best practices

