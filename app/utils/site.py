"""Guards for global (site_admin) API endpoints (TASK-039).

Unlike the school_admin guard (app/utils/school.py), there is no
institution comparison: a site_admin is global by definition. The only
check is the role — anything else gets a 403 indistinguishable from a
plain auth failure.

TASK-041 (product decision): `support` carries the same permission level
as `site_admin` — both roles pass SITE_LEVEL_ROLES guards. The role
values remain distinct in the database for reporting.

Impersonation boundary (TASK-040): a token minted by
/api/support/impersonate must NEVER reach privileged surfaces — even when
the impersonated user is themselves a school_admin/site_admin. Both
guards therefore also reject tokens carrying an impersonator_id claim.
"""

from functools import wraps

from flask import g

from app.models.user import ROLE_SITE_ADMIN, ROLE_SUPPORT
from app.utils.auth import _authenticate_api

# Roles with full site-admin permission level (TASK-041): support was
# elevated to site_admin parity by explicit product decision. The values
# stay distinct in the DB — only the guard widened, not the role model.
SITE_LEVEL_ROLES = (ROLE_SITE_ADMIN, ROLE_SUPPORT)

IMPERSONATION_FORBIDDEN = (
    {"error": "Impersonation tokens cannot access administrative surfaces."},
    403,
)


def _impersonating():
    return getattr(g, "api_impersonator_id", None) is not None


def site_admin_required(view):
    """Bearer auth + site-level role (site_admin or support — TASK-041
    parity). No institution check — global role.

    Rejects impersonation tokens outright: a support session acting AS a
    site_admin must not be able to wield site_admin powers."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user, error = _authenticate_api()
        if error is not None:
            return error
        if _impersonating():
            return IMPERSONATION_FORBIDDEN
        if user.role not in SITE_LEVEL_ROLES:
            return ({"error": "Site administrator privileges required."}, 403)
        return view(*args, **kwargs)
    return wrapped
