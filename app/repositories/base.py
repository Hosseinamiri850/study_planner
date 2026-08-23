"""Repository base — owns the session used by all repositories.

The seam for future PostgreSQL read replicas: read-only repository methods use
`read_session()`, write methods use `write_session()`. Today both return the
same `db.session` (the primary). When `DATABASE_REPLICA_URLS` is set, optional
replica sessions are created and reads may target them while writes always go
to the primary.

A replica engine is created lazily from `DATABASE_REPLICA_URLS` (the first URI
is used). It shares the ORM models (`db.Model`). The replica session is
thread-local (scoped_session default) and removed on app-context teardown so
its connection is returned to the pool instead of accumulating per worker.
If the replica engine is not configured, `read_session()` falls back to the
primary `db.session` — the common case in dev and tests today.

Mutate-then-persist flows MUST load their rows through the write session
(`*Repo.get(..., for_write=True)` and friends): instances returned by read
methods are attached to the replica session when one is configured, and
changes made on them would be lost when the primary session commits. With no
replica configured both sessions are the same object, so this is invisible in
dev/tests — which is exactly why the for_write variants exist.
"""

from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from app.extensions import db


def _replica_engine():
    """Return a replica engine for the current app, or None when none is
    configured. Lazily builds one engine per app and caches it on `current_app`.
    """
    urls = current_app.config.get("DATABASE_REPLICA_URLS", "")
    if not urls:
        return None
    engine = current_app.config.get("_replica_engine")
    if engine is None:
        first_url = urls.split(",", 1)[0].strip()
        engine = create_engine(first_url, future=True)
        current_app.config["_replica_engine"] = engine
    return engine


def _teardown_replica_session(_exception):
    """Release the replica session's connection for the ending context."""
    session = current_app.config.get("_replica_session")
    if session is not None:
        session.remove()


def read_session():
    """Session for read-only repository methods.

    Targets a replica session when `DATABASE_REPLICA_URLS` is set; otherwise
    the primary `db.session`. Callers must not commit — read only. Instances
    loaded from this session are attached to it; fetch through the write
    session instead when the row will be modified.
    """
    engine = _replica_engine()
    if engine is None:
        return db.session
    session = current_app.config.get("_replica_session")
    if session is None:
        # Thread-local scope (the scoped_session default); the app-context
        # teardown below removes the current thread's session so its
        # connection is returned to the pool instead of accumulating.
        session = scoped_session(sessionmaker(bind=engine, future=True))
        current_app.config["_replica_session"] = session
        current_app.teardown_appcontext(_teardown_replica_session)
    return session


def write_session():
    """Session for write repository methods. Always the primary `db.session`."""
    return db.session


class Repo:
    """Base repository. Subclasses implement resource-specific queries."""

    @staticmethod
    def _read():
        return read_session()

    @staticmethod
    def _write():
        return write_session()
