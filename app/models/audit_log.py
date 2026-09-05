from datetime import UTC, datetime

from app.extensions import db


def _utcnow():
    """Naive UTC — same convention as task.py/refresh_token.py (all naive
    DateTime columns; psycopg converts aware values to server-local wall
    clock, corrupting them on non-UTC hosts)."""
    return datetime.now(UTC).replace(tzinfo=None)


class AuditLog(db.Model):
    """Before/after change history for instrumented mutations (TASK-035).

    Append-only: no update/delete paths exist and none should be added.
    `actor_user_id` is nullable for system actions (seeder, migrations,
    future background jobs). `institution_id` is denormalized from the
    actor at write time so tenant-scoped queries don't need joins.
    """

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer, nullable=True)
    before = db.Column(db.JSON, nullable=True)
    after = db.Column(db.JSON, nullable=True)
    institution_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False, index=True)
    actor = db.relationship("User")
