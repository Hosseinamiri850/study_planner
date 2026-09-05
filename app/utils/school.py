"""Guards for institution-scoped (school_admin) API endpoints (TASK-038).

The tenancy rule is a single comparison, applied twice per request:
1. The actor must BE a school_admin of some institution.
2. Every resource the actor touches must carry the SAME institution_id.

Cross-institution access is a 403 — indistinguishable from a plain role
failure, so the response does not confirm resource existence.
"""

from functools import wraps

from app.models.user import ROLE_SCHOOL_ADMIN
from app.utils.auth import _authenticate_api


def _load_school_admin():
    """Resolve the Bearer token and apply the school_admin guard.

    Returns (user, None) on success, or (None, (body, status)) on failure.
    """
    user, error = _authenticate_api()
    if error is not None:
        return None, error
    if user.role != ROLE_SCHOOL_ADMIN or user.institution_id is None:
        return None, ({"error": "School administrator privileges required."}, 403)
    return user, None


def _reject_foreign(target_institution_id, actor_institution_id):
    if target_institution_id != actor_institution_id:
        return {"error": "This resource belongs to another institution."}, 403
    return None


def school_admin_required(view):
    """Bearer auth + school_admin role + an institution to administer."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user, error = _load_school_admin()
        if error is not None:
            return error
        return view(*args, **kwargs)
    return wrapped
