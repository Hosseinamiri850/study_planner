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
from alembic.migration import MigrationContext
from alembic.operations import Operations

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


# --- 20260906_01: User.role + institution_id replacing is_admin ---

_ROLES_MIGRATION_PATH = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "20260906_01_user_roles_institution.py"


def _load_roles_migration():
    spec = importlib.util.spec_from_file_location("user_roles_migration", _ROLES_MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def roles_migration(app):
    """Load the roles migration and bind its `op` proxy to the test DB.

    The 20260829_01 fixture only patches op.get_bind() — enough there since
    that migration runs raw SQL. This one calls op.add_column/drop_column,
    which need a real Operations proxy. A dedicated AUTOCOMMIT connection is
    used (not db.session.connection()): test fixtures commit in between,
    which would release/close a session connection under NullPool mid-test,
    and the session's own connection must be able to see the migration's
    DDL immediately afterwards."""
    module = _load_roles_migration()
    conn = db.engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    ctx = MigrationContext.configure(conn)
    module.op = Operations(ctx)
    yield module
    conn.close()


def _reshape_to_pre_roles_schema():
    """Reshape the freshly created schema back to the pre-migration state:
    drop role/institution_id, restore the legacy is_admin boolean. Must run
    AFTER seeding users (the ORM INSERT references the new columns) and
    BEFORE the migration — conftest uses db.create_all(), so the migration
    under test runs against the exact state production rows are in."""
    db.session.execute(db.text("DROP INDEX IF EXISTS ix_users_role"))
    db.session.execute(db.text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))
    # Carry the admin bit over from role BEFORE dropping it, mirroring what
    # a real pre-migration database holds in its is_admin column.
    db.session.execute(db.text("UPDATE users SET is_admin = 1 WHERE role = 'site_admin'"))
    db.session.execute(db.text("ALTER TABLE users DROP COLUMN role"))
    db.session.execute(db.text("ALTER TABLE users DROP COLUMN institution_id"))
    db.session.commit()


def test_roles_backfill_admin_true_becomes_site_admin(roles_migration, create_user):
    create_user(username="boss", is_admin=True)
    _reshape_to_pre_roles_schema()
    roles_migration.upgrade()
    role = db.session.execute(db.text("SELECT role FROM users WHERE username='boss'")).scalar()
    assert role == "site_admin"


def test_roles_backfill_admin_false_becomes_student(roles_migration, create_user):
    create_user(username="pleb")
    _reshape_to_pre_roles_schema()
    roles_migration.upgrade()
    role = db.session.execute(db.text("SELECT role FROM users WHERE username='pleb'")).scalar()
    assert role == "student"


def test_roles_backfill_mixed_population_no_loss(roles_migration, create_user):
    create_user(username="admin_a", is_admin=True)
    create_user(username="plain")
    create_user(username="plain2")
    _reshape_to_pre_roles_schema()
    roles_migration.upgrade()
    rows = db.session.execute(db.text("SELECT username, role, institution_id FROM users")).fetchall()
    by_name = {r[0]: r for r in rows}
    assert len(rows) == 3
    assert by_name["admin_a"][1] == "site_admin"
    assert by_name["plain"][1] == "student"
    assert by_name["plain2"][1] == "student"
    # institution_id arrives nullable and untouched by the backfill.
    assert all(r[2] is None for r in rows)


def test_roles_downgrade_restores_is_admin(roles_migration, create_user):
    create_user(username="down_admin", is_admin=True)
    create_user(username="down_plain")
    _reshape_to_pre_roles_schema()
    roles_migration.upgrade()
    roles_migration.downgrade()
    rows = db.session.execute(db.text("SELECT username, is_admin FROM users")).fetchall()
    by_name = {r[0]: r[1] for r in rows}
    assert by_name["down_admin"] in (True, 1)
    assert by_name["down_plain"] in (False, 0)
