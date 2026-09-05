"""Application-level audit trail (TASK-035).

`record()` appends one AuditLog row per mutation. Design rules:

- **Never break the mutation.** Auditing is observability, not a write
  dependency: any failure inside record() is logged and swallowed so the
  user's operation still succeeds. Call it AFTER the mutation's commit.
- **Actor may be None** for system actions (seed, future background jobs).
- **Institution is denormalized from the actor** at write time, so tenant
  filtering needs no join. B2C users (no institution) record NULL.
- `before`/`after` accept plain dicts (JSON-serializable values only);
  pass None when a snapshot does not apply.
- target is a `(target_type, target_id)` pair, e.g. `("task", 42)`.
"""

import logging

from flask import has_app_context

from app.extensions import db
from app.models import AuditLog

logger = logging.getLogger(__name__)


def record(actor, action, target, before=None, after=None):
    """Append an audit row for one mutation. Fire-and-forget.

    actor: User instance or None (system). institution_id is taken from
    actor.institution_id when present.
    action: dotted string, e.g. "task.delete", "user.role_change".
    target: (target_type, target_id) — target_id may be None.
    before/after: JSON-serializable dicts or None.

    Returns the AuditLog row, or None when recording failed (the failure
    is logged; the caller's mutation is unaffected).
    """
    if not has_app_context():
        logger.warning("audit.record called outside app context; dropping audit event %s", action)
        return None
    try:
        target_type, target_id = target
        row = AuditLog(
            actor_user_id=getattr(actor, "id", None),
            action=action,
            target_type=str(target_type),
            target_id=target_id,
            before=before,
            after=after,
            institution_id=getattr(actor, "institution_id", None),
        )
        db.session.add(row)
        db.session.commit()
        return row
    except Exception:
        # Audit must never take down the mutation it observes. Roll back so
        # a failed audit insert does not poison the session for the caller.
        db.session.rollback()
        logger.exception("audit.record failed for action=%s", action)
        return None
