"""Global API for support agents (TASK-040).

Shape mirrors app/routes/site.py. Since TASK-041 (product decision),
support carries the same permission level as site_admin — full
site-level access via /api/site/*, not read-only. What remains
support-specific here:

- Impersonation: a support agent may mint a short-lived access token
  that authenticates AS another user to reproduce their view.
  - The token's lifetime is identical to a normal access token (no
    extension). Impersonation ends when the token expires — there is no
    "end impersonation" endpoint; none is needed because the token is
    stateless and self-expiring.
  - Every such token carries an `impersonator_id` claim. All audit rows
    written while it is in use record both the acting user and the agent
    behind them, and the school/site guards refuse impersonated tokens
    outright (app/utils/school.py, app/utils/site.py).
  - A support agent may never impersonate another support agent or a
    site_admin — even though the two roles now share a permission level,
    the boundary prevents one privileged account from acting under
    another privileged account's identity without clear attribution.
"""

from functools import wraps

from flask import Blueprint, g, jsonify, request

from app.extensions import csrf
from app.models import AuditLog, Class, User
from app.models.user import ROLE_SITE_ADMIN, ROLE_SUPPORT
from app.repositories import InstitutionRepo
from app.services.audit import record as audit_record
from app.utils.auth import _authenticate_api, create_access_token

support_bp = Blueprint("support", __name__, url_prefix="/api/support")

SEARCH_PAGE_DEFAULT = 1

# Roles a support agent may NEVER impersonate: their privileged actions
# must never run under a support-attributable token.
UNIMPERSONATABLE_ROLES = (ROLE_SITE_ADMIN, ROLE_SUPPORT)

USER_PAGE_SIZE_DEFAULT = 20
USER_PAGE_SIZE_MAX = 100

AUDIT_PAGE_SIZE_DEFAULT = 20
AUDIT_PAGE_SIZE_MAX = 100


def support_required(view):
    """Bearer auth + support role. No institution scoping — support is
    global, B2C and B2B alike. Impersonation tokens cannot reach here:
    _authenticate_api exposes the claim, and an impersonated user would
    need role == support to pass the check below, which is unreachable
    because support users are on the UNIMPERSONATABLE list."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user, error = _authenticate_api()
        if error is not None:
            return error
        if getattr(g, "api_impersonator_id", None) is not None:
            return ({"error": "Impersonation tokens cannot access the support console."}, 403)
        if user.role != ROLE_SUPPORT:
            return ({"error": "Support privileges required."}, 403)
        return view(*args, **kwargs)
    return wrapped


def _institution_payload(institution, counts=None):
    payload = {
        "id": institution.id,
        "name": institution.name,
        "type": institution.type,
        "plan_tier": institution.plan_tier,
    }
    if counts is not None:
        payload.update(counts)
    return payload


def _institution_counts(institution_ids):
    if not institution_ids:
        return {}
    counts = {iid: {"students": 0, "teachers": 0, "classes": 0} for iid in institution_ids}
    role_rows = (
        User.query.filter(User.institution_id.in_(institution_ids), User.role.in_(("student", "teacher")))
        .with_entities(User.institution_id, User.role)
        .all()
    )
    for iid, role in role_rows:
        counts[iid]["students" if role == "student" else "teachers"] += 1
    class_rows = (
        Class.query.filter(Class.institution_id.in_(institution_ids))
        .with_entities(Class.institution_id)
        .all()
    )
    for (iid,) in class_rows:
        counts[iid]["classes"] += 1
    return counts


def _user_payload(user):
    return {
        "id": user.id,
        "username": user.username,
        "fullname": user.fullname,
        "role": user.role,
        "institution_id": user.institution_id,
        "class_id": user.class_id,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@support_bp.route("/institutions", methods=["GET"])
@csrf.exempt
@support_required
def list_institutions():
    """All institutions with counts — same shape as the site_admin list,
    read-only."""
    institutions = InstitutionRepo.list_all()
    counts = _institution_counts([i.id for i in institutions])
    return jsonify({
        "institutions": [
            _institution_payload(i, counts.get(i.id, {"students": 0, "teachers": 0, "classes": 0}))
            for i in institutions
        ]
    })


@support_bp.route("/users", methods=["GET"])
@csrf.exempt
@support_required
def search_users():
    """Search users by username or fullname across all tenants + B2C,
    paginated. `query` does a case-insensitive substring match; `role`
    narrows to one role; empty query lists everyone newest-last."""
    query = (request.args.get("query") or "").strip()
    try:
        page = max(1, int(request.args.get("page", SEARCH_PAGE_DEFAULT)))
        per_page = int(request.args.get("per_page", USER_PAGE_SIZE_DEFAULT))
    except ValueError:
        return jsonify({"error": "page and per_page must be integers."}), 400
    per_page = min(max(1, per_page), USER_PAGE_SIZE_MAX)

    base = User.query
    if query:
        base = base.filter((User.username.ilike(f"%{query}%")) | (User.fullname.ilike(f"%{query}%")))
    role = request.args.get("role")
    if role:
        base = base.filter(User.role == role)
    total = base.count()
    users = base.order_by(User.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({
        "users": [_user_payload(u) for u in users],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": max(1, -(-total // per_page)),
    })


@support_bp.route("/audit-log", methods=["GET"])
@csrf.exempt
@support_required
def audit_log():
    """Global audit trail — same filters as the site_admin view."""
    query = AuditLog.query
    raw_institution = request.args.get("institution_id")
    if raw_institution:
        try:
            query = query.filter(AuditLog.institution_id == int(raw_institution))
        except ValueError:
            return jsonify({"error": "institution_id must be an integer."}), 400
    action = request.args.get("action")
    if action:
        query = query.filter(AuditLog.action == action)
    raw_actor = request.args.get("actor_user_id")
    if raw_actor:
        try:
            query = query.filter(AuditLog.actor_user_id == int(raw_actor))
        except ValueError:
            return jsonify({"error": "actor_user_id must be an integer."}), 400
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = int(request.args.get("per_page", AUDIT_PAGE_SIZE_DEFAULT))
    except ValueError:
        return jsonify({"error": "page and per_page must be integers."}), 400
    per_page = min(max(1, per_page), AUDIT_PAGE_SIZE_MAX)
    total = query.count()
    rows = (
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return jsonify({
        "entries": [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "actor_user_id": r.actor_user_id,
                "impersonator_id": r.impersonator_id,
                "action": r.action,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "institution_id": r.institution_id,
                "before": r.before,
                "after": r.after,
            }
            for r in rows
        ],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": max(1, -(-total // per_page)),
    })


@support_bp.route("/impersonate/<int:user_id>", methods=["POST"])
@csrf.exempt
@support_required
def impersonate(user_id):
    """Mint a short-lived access token that authenticates as `user_id`.

    Airtight by construction:
    - target roles support/site_admin are refused up front;
    - the token carries an impersonator_id claim (its TTL is NOT extended);
    - the school/site/support guards reject any token carrying the claim,
      so the impersonated context cannot escalate into admin surfaces even
      if the target user is itself an admin (already refused here) or the
      token is replayed against those routes directly;
    - the impersonation.start audit row is written BEFORE the token is
      returned — the attempt is on record even if the client never uses
      the token.
    """
    agent = g.api_user
    target = User.query.get(user_id)
    if target is None:
        return jsonify({"error": "User not found."}), 404
    if target.role in UNIMPERSONATABLE_ROLES:
        return jsonify({"error": "Support cannot impersonate administrative accounts."}), 403

    audit_record(
        agent,
        "impersonation.start",
        ("user", user_id),
        after={
            "target_username": target.username,
            "target_role": target.role,
            "impersonator_id": agent.id,
        },
    )
    token = create_access_token(target, impersonator_id=agent.id)
    return jsonify({"access_token": token, "user": _user_payload(target)})
