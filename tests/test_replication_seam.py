"""Tests for the read/write split seam (TASK-039).

The seam is config-driven: with `DATABASE_REPLICA_URLS` unset, reads fall
through to the primary `db.session`; when it is set, reads may target a
replica session while writes always go to primary. This file validates the
wiring without requiring a live replica host — it uses a second in-memory
SQLite engine as the "replica" and confirms:

- `read_session()` returns the primary session when no replica is configured.
- `read_session()` returns a distinct session bound to the replica engine
  when `DATABASE_REPLICA_URLS` points at it.
- `write_session()` is always the primary, regardless of config.
- A write through TaskRepo lands on the primary even when a replica is wired.
- Reading with no replica hits the primary, so a row written via TaskRepo is
  immediately visible to a subsequent read.
"""

import pytest

from app.extensions import db
from app.models import Task
from app.repositories import TaskRepo
from app.repositories.base import _replica_engine, read_session, write_session


class TestSeamDefaults:
    def test_read_session_is_primary_when_no_replica(self, app):
        # TestConfig does not set DATABASE_REPLICA_URLS, so reads fall back.
        assert read_session() is db.session

    def test_write_session_is_always_primary(self, app):
        assert write_session() is db.session


@pytest.fixture
def replica_app():
    """A second app instance that names a replica in config. The same
    in-memory SQLite primary is used; the replica URI is a second in-memory
    SQLite engine created on demand by the seam."""
    from app import create_app

    class ReplicaConfig:
        SECRET_KEY = "test-secret-key"
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        DEBUG = False
        TESTING = True
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False
        DATABASE_REPLICA_URLS = "sqlite:///:memory:"

    app = create_app(ReplicaConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


class TestSeamWithReplica:
    def test_replica_engine_built_from_config(self, replica_app):
        engine = _replica_engine()
        assert engine is not None
        # Cached on the app config for the lifetime of this context.
        assert replica_app.config["_replica_engine"] is engine

    def test_no_replica_engine_when_unset(self, app):
        assert _replica_engine() is None

    def test_read_session_distinct_from_primary_when_replica(self, replica_app):
        rs = read_session()
        assert rs is not db.session
        assert rs is replica_app.config["_replica_session"]  # cached scoped_session.

    def test_write_session_still_primary_with_replica(self, replica_app):
        assert write_session() is db.session

    def test_write_lands_on_primary(self, replica_app, create_user, create_course):
        # Build a task through the repo (write path -> primary).
        user, course = create_user(), create_course()
        task = TaskRepo.create(
            user_id=user.id,
            course_id=course.id,
            course_key=course.key,
            title="seam-write",
            description="",
            priority="medium",
            hours=1.0,
        )
        # The primary session sees the committed row immediately.
        assert db.session.get(Task, task.id) is not None

    def test_read_modify_write_persists_under_replica(self, replica_app, create_user, create_course):
        """The seam's core hazard: instances from read_session() belong to the
        replica when one is configured, so mutating them and committing the
        PRIMARY session silently drops the UPDATE. get_for_write() exists to
        prevent exactly this — prove it does."""
        user, course = create_user(), create_course()
        task = TaskRepo.create(
            user_id=user.id,
            course_id=course.id,
            course_key=course.key,
            title="before",
            description="",
            priority="low",
            hours=1.0,
        )
        loaded = TaskRepo.get_for_write(task.id)
        assert loaded is not None
        TaskRepo.update_fields(loaded, title="after", priority="high")
        TaskRepo.commit()
        fresh = db.session.get(Task, task.id)
        assert fresh.title == "after"
        assert fresh.priority == "high"

    def test_stop_session_persists_under_replica(self, replica_app, create_user, create_task):
        user = create_user()
        task = create_task(user=user)
        opened = TaskRepo.start_session(task)
        assert opened.id is not None
        closed = TaskRepo.get_session_for_write(opened.id)
        TaskRepo.stop_session(closed)
        assert db.session.get(Task, task.id) is not None  # sanity: primary live
        from app.models import StudySession

        row = db.session.get(StudySession, opened.id)
        assert row.ended_at is not None

    def test_read_after_write_on_primary_without_replica(self, app, create_user, create_course):
        # The common dev/test path: no replica, so a write is immediately
        # visible to the next read. Guards against a regression where reads
        # are mistakenly routed away from the primary when no replica exists.
        user, course = create_user(), create_course()
        TaskRepo.create(
            user_id=user.id,
            course_id=course.id,
            course_key=course.key,
            title="rd-after-wr",
            description="",
            priority="medium",
            hours=1.0,
        )
        assert len(TaskRepo.list_for_user(user.id)) == 1
