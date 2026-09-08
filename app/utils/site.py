"""Guards for global (site_admin) API endpoints (TASK-039).

Unlike the school_admin guard (app/utils/school.py), there is no
institution comparison: a site_admin is global by definition. The only
check is the role — anything else gets a 403 indistinguishable from a
plain auth failure.
"""

from functools import wraps

from app.models.user import ROLE_SITE_ADMIN
from app.utils.auth import _authenticate_api


def site_admin_required(view):
    """Bearer auth + site_admin role. No institution check — global role."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user, error = _authenticate_api()
        if error is not None:
            return error
        if user.role != ROLE_SITE_ADMIN:
            return ({"error": "Site administrator privileges required."}, 403)
        return view(*args, **kwargs)
    return wrapped
