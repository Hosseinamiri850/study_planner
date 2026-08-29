"""Backfill migration semantics (TASK-027, revision 20260829_01).

Runs the actual Alembic migration functions against the test DB (SQLite in
dev, PostgreSQL in CI) via a scratch alembic config. The conftest app uses
`db.create_all()`, so the migration under test is driven directly: its
upgrade()/downgrade() are plain functions over the current schema, and the
pre-migration state (completed task with no sessions) is exactly the state
the backfill targets — no need to replay the whole chain.
"""

import importlib.util
from datetime import date
from pathlib import Path

import pytest

from app.extensions import db

_MIGRATION_PATH = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "20260829_01_backfill_sessions.py"


def _load_migration():
    spec = importlib.util.spec_from_file_location("backfill_migration", _MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def migration():
    """Load the migration module and bind its op.get_bind() to the test DB."""
    module = _load_migration()
    original = module.op.get_bind
    module.op.get_bind = lambda: db.session.connection()
    yield module
    module.op.get_bind = original


def test_backfill_synthesizes_session_for_done_task(migration, create_user, create_course, create_task):
    user = create_user()
    course = create_course()
    create_task(user=user, course=course, hours=2.0, done=True, status="completed", created_at=date(2026, 1, 15))
    migration.upgrade()
    sessions = db.session.execute(db.text("SELECT task_id, duration, started_at, ended_at FROM study_sessions")).fetchall()
    assert len(sessions) == 1
    task_id, duration, started, ended = sessions[0]
    assert duration == 7200
    assert str(started).startswith("2026-01-15 12:00")
    assert str(ended).startswith("2026-01-15 12:00")


def test_backfill_skips_pending_and_task_with_sessions(migration, create_user, create_course, create_task, create_study_session):
    user = create_user()
    course = create_course()
    create_task(user=user, course=course, hours=1.0, done=False)
    already = create_task(user=user, course=course, hours=2.0, done=True)
    create_study_session(task=already, duration=600, started_at=None, ended_at=None)  # real tracked row
    migration.upgrade()
    rows = db.session.execute(db.text("SELECT task_id, duration FROM study_sessions")).fetchall()
    # Only the pre-existing tracked session; nothing synthesized.
    assert len(rows) == 1
    assert rows[0][0] == already.id and rows[0][1] == 600


def test_backfill_idempotent(migration, create_user, create_course, create_task):
    user = create_user()
    course = create_course()
    create_task(user=user, course=course, hours=1.5, done=True, status="completed")
    migration.upgrade()
    first = db.session.execute(db.text("SELECT COUNT(*) FROM study_sessions")).scalar()
    migration.upgrade()
    second = db.session.execute(db.text("SELECT COUNT(*) FROM study_sessions")).scalar()
    assert first == second == 1


def test_downgrade_removes_synthesized_only(migration, create_user, create_course, create_task, create_study_session):
    user = create_user()
    course = create_course()
    # A real tracked session on a pending task must survive the downgrade.
    survivor_task = create_task(user=user, course=course, hours=1.0, done=False)
    create_study_session(task=survivor_task, duration=900)
    # A backfill-shaped session on a done task must be removed.
    create_task(user=user, course=course, hours=2.0, done=True, status="completed")
    migration.upgrade()
    assert db.session.execute(db.text("SELECT COUNT(*) FROM study_sessions")).scalar() == 2
    migration.downgrade()
    remaining = db.session.execute(db.text("SELECT task_id FROM study_sessions")).fetchall()
    assert [r[0] for r in remaining] == [survivor_task.id]
