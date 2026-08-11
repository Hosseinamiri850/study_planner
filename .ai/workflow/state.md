# Workflow State

This file is the shared conversation between the Implementer and the Reviewer.
Both roles update it. The user reads it to see where a task stands.

Update this file at every transition. Never delete history — append a new
block. The latest block is the current state.

## Status legend

- `IDLE` — no task assigned.
- `PLANNING` — Implementer reading the task and sketching an approach.
- `IN_PROGRESS` — Implementer editing code.
- `IMPLEMENTATION_DONE — PENDING_REVIEW` — Implementer finished; Reviewer should pick up.
- `UNDER_REVIEW` — Reviewer verifying.
- `APPROVED — READY_TO_MERGE` — Reviewer approved; waiting on user to merge.
- `REVISIONS_REQUESTED` — Reviewer rejected with reasons; back to Implementer.
- `ESCALATED` — Roles blocked on a judgment call; user decides.

---

## Current state

**Status:** `IDLE`
**Task:** —
**Implementer:** —
**Reviewer:** —
**Started:** —
**Last updated:** 2026-08-12

No task active. Workflow files are initialized and ready. When the user assigns
a task, the Implementer creates a new block below with status `PLANNING`.

---

## History

_(Append a new block per task or per status change within a task. Keep blocks
short — detail lives in `implementation-result.md` and `reviews/latest.md`.)_

### 2026-08-12 — Workflow initialized
- Created `.ai/agents/implementer.md`, `.ai/agents/reviewer.md`.
- Created `.ai/workflow/state.md`, `.ai/workflow/implementation-result.md`.
- Created `.ai/reviews/latest.md`.
- No application code modified. No project task started.

---

## How to use this file

When starting a task, the Implementer appends a new block:

```
### <date> — TASK-xxx
**Status:** PLANNING
**Implementer:** <name>
**Reviewer:** <name>
**Plan:** (2–5 bullets, what you will touch and why)
```

Then update the **Current state** block above to match.

Transitions append a one-line entry under the task block:

```
- <date> IN_PROGRESS — implementing <thing>
- <date> IMPLEMENTATION_DONE — PENDING_REVIEW — see implementation-result.md
- <date> UNDER_REVIEW — Reviewer started
- <date> APPROVED — READY_TO_MERGE
```

Or, on rejection:

```
- <date> REVISIONS_REQUESTED — <one-line reason>, see reviews/latest.md
```

On rejection, the Implementer opens a `## Implementer response` sub-block with
what was changed and why. The Reviewer re-verifies and updates the status again.

On escalation, either role opens an `## Escalation to user` sub-block with both
positions stated briefly.
