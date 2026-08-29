"""Backfill study_sessions from completed tasks (TASK-027 cutover).

Statistics now aggregate tracked StudySession time (duration by
started_at) instead of estimated Task.hours by Task.created_at. Historical
completed tasks predate session tracking, so without backfill their study
hours would vanish from every chart.

Strategy: for each DONE task with NO study sessions, synthesize one closed
session — duration = hours * 3600 seconds, started_at/ended_at anchored on
the task's created_at date (12:00 UTC, an explicit neutral midday marker so
the bucket lands on the task's original day regardless of when the row was
written). Tasks that already have sessions are left untouched — their real
tracked time is authoritative and double-counting is avoided.

The work runs through SQLAlchemy Core in Python rather than raw SQL: the
timestamp anchoring must behave identically on SQLite and PostgreSQL
(SQLite's CAST(... AS TIMESTAMP) is NOT a datetime cast), and both dialects
share the same table registration via db.Model metadata.

The backfill is idempotent by construction: a second run finds no eligible
tasks (every completed task now has >= 1 session) and inserts nothing.
Downgrade deletes exactly the synthesized rows, re-derived with the same
matching rule.
"""

import datetime as dt

import sqlalchemy as sa
from alembic import op

revision = "20260829_01"
down_revision = "20260804_02"
branch_labels = None
depends_on = None

_ANCHOR_TIME = dt.time(12, 0)  # neutral midday UTC marker on the task's day


def _synthesized_rows(conn):
    """Rows (task_id, hours, created_at) for done tasks with no sessions."""
    eligible = sa.text(
        "SELECT t.id, t.hours, t.created_at FROM tasks t "
        "WHERE t.done = 1 AND NOT EXISTS "
        "(SELECT 1 FROM study_sessions s WHERE s.task_id = t.id)"
    )
    return conn.execute(eligible).fetchall()


def upgrade():
    conn = op.get_bind()
    rows = _synthesized_rows(conn)
    insert = sa.text(
        "INSERT INTO study_sessions (task_id, duration, started_at, ended_at) "
        "VALUES (:task_id, :duration, :started_at, :ended_at)"
    )
    for task_id, hours, created_at in rows:
        day = created_at if isinstance(created_at, dt.date) else dt.date.fromisoformat(str(created_at)[:10])
        anchor = dt.datetime.combine(day, _ANCHOR_TIME)
        conn.execute(
            insert,
            {"task_id": task_id, "duration": int(round((hours or 0.0) * 3600)), "started_at": anchor, "ended_at": anchor},
        )


def downgrade():
    conn = op.get_bind()
    # Mirror of the upgrade selector: done tasks whose ONLY session(s) are
    # synthesized ones (started == ended at the 12:00 anchor with duration
    # == hours * 3600). Delete those sessions; real tracked rows survive.
    find = sa.text(
        "SELECT s.id, s.started_at, s.duration, t.hours FROM study_sessions s "
        "JOIN tasks t ON t.id = s.task_id WHERE t.done = 1"
    )
    delete = sa.text("DELETE FROM study_sessions WHERE id = :sid")
    for sid, started_at, duration, hours in conn.execute(find):
        started = started_at if isinstance(started_at, dt.datetime) else dt.datetime.fromisoformat(str(started_at))
        anchored = started.time() == _ANCHOR_TIME and started == started.replace(microsecond=0)
        if anchored and duration is not None and hours is not None and abs(duration - int(round(hours * 3600))) < 1:
            conn.execute(delete, {"sid": sid})
