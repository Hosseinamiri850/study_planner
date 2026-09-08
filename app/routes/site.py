"""Global (cross-institution) API for site administrators (TASK-039).

Mirrors app/routes/school.py in shape and security posture, with the
opposite scope: no institution filtering anywhere — the site_admin role
is global by definition. The guard (app/utils/site.py) admits only
role == site_admin; a school_admin gets 403 on every endpoint here.

`POST /institutions` is the one-request "create tenant + first admin"
flow that `create-admin --promote` does from the CLI. The created user's
role is hardcoded to school_admin inside the handler — the caller cannot
escalate.
"""

from flask import Blueprint, g, jsonify, request
from werkzeug.security import generate_password_hash

from app.extensions import csrf
from app.models import AuditLog, Class, User
from app.models.user import ROLE_SCHOOL_ADMIN
from app.repositories import InstitutionRepo
from app.repositories.user_repo import UserRepo
from app.services.audit import record as audit_record
from app.utils.site import site_admin_required
from app.utils.validation import valid_password, valid_username

site_bp = Blueprint("site", __name__, url_prefix="/api/site")

INSTITUTION_NAME_MAX = 150
PLAN_TIER_MAX = 30
VALID_PLAN_TIERS = ("free", "pro", "enterprise")

AUDIT_PAGE_SIZE_DEFAULT = 20
AUDIT_PAGE_SIZE_MAX = 100


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
    """{institution_id: {"students": n, "teachers": n, "classes": n}} in
    three grouped queries — no per-row round trips."""
    if not institution_ids:
        return {}
    counts = {
        iid: {"students": 0, "teachers": 0, "classes": 0}
        for iid in institution_ids
    }
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


def _audit_row_payload(row):
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "actor_user_id": row.actor_user_id,
        "action": row.action,
        "target_type": row.target_type,
        "target_id": row.target_id,
        "institution_id": row.institution_id,
        "before": row.before,
        "after": row.after,
    }


@site_bp.route("/institutions", methods=["GET"])
@csrf.exempt
@site_admin_required
def list_institutions():
    """All institutions with student/teacher/class counts."""
    institutions = InstitutionRepo.list_all()
    counts = _institution_counts([i.id for i in institutions])
    return jsonify({
        "institutions": [
            _institution_payload(i, counts.get(i.id, {"students": 0, "teachers": 0, "classes": 0}))
            for i in institutions
        ]
    })


@site_bp.route("/institutions", methods=["POST"])
@csrf.exempt
@site_admin_required
def create_institution():
    """Create an institution AND its first school_admin in one request.

    The created user's role is hardcoded to school_admin — the request
    body cannot name any other role, so this endpoint cannot mint
    site_admins. Password is stored hashed and never echoed.
    """
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    inst_type = str(data.get("type", "")).strip() or "school"
    plan_tier = str(data.get("plan_tier", "")).strip() or "free"
    admin_username = str(data.get("admin_username", "")).strip()
    admin_password = str(data.get("admin_password", "") or "")
    admin_fullname = str(data.get("admin_fullname", "")).strip() or admin_username

    if not name or len(name) > INSTITUTION_NAME_MAX:
        return jsonify({"error": "name must be 1-150 characters."}), 400
    if inst_type not in ("school", "university", "academy"):
        return jsonify({"error": "type must be one of: school, university, academy."}), 400
    if plan_tier not in VALID_PLAN_TIERS:
        return jsonify({"error": f"plan_tier must be one of: {', '.join(VALID_PLAN_TIERS)}."}), 400
    if not valid_username(admin_username):
        return jsonify({"error": "admin_username must be 3-80 letters, numbers, or underscores."}), 400
    if not valid_password(admin_password):
        return jsonify({"error": "admin_password must be at least 8 characters."}), 400
    if UserRepo.find_by_username(admin_username) is not None:
        return jsonify({"error": "Username already exists."}), 409

    institution = InstitutionRepo.create(name=name, type=inst_type, plan_tier=plan_tier)
    admin = User(
        username=admin_username,
        password=generate_password_hash(admin_password),
        fullname=admin_fullname,
        role=ROLE_SCHOOL_ADMIN,
        institution_id=institution.id,
    )
    UserRepo._write().add(admin)
    UserRepo.commit()

    audit_record(
        g.api_user,
        "institution.create",
        ("institution", institution.id),
        after=_institution_payload(institution),
    )
    return jsonify({
        "institution": _institution_payload(institution),
        "admin": {"id": admin.id, "username": admin.username, "fullname": admin.fullname, "role": admin.role},
    }), 201


@site_bp.route("/institutions/<int:institution_id>", methods=["PUT"])
@csrf.exempt
@site_admin_required
def update_institution(institution_id):
    """Update plan_tier only (name/type changes are out of scope this pass)."""
    institution = InstitutionRepo.get_for_write(institution_id)
    if institution is None:
        return jsonify({"error": "Institution not found."}), 404
    data = request.get_json(silent=True) or {}
    if "plan_tier" not in data:
        return jsonify({"error": "plan_tier is required."}), 400
    plan_tier = str(data.get("plan_tier", "")).strip()
    if plan_tier not in VALID_PLAN_TIERS:
        return jsonify({"error": f"plan_tier must be one of: {', '.join(VALID_PLAN_TIERS)}."}), 400
    before = _institution_payload(institution)
    institution.plan_tier = plan_tier
    InstitutionRepo.commit()
    audit_record(
        g.api_user,
        "institution.plan_change",
        ("institution", institution_id),
        before=before,
        after=_institution_payload(institution),
    )
    return jsonify({"institution": _institution_payload(institution)})


@site_bp.route("/audit-log", methods=["GET"])
@csrf.exempt
@site_admin_required
def audit_log():
    """Paginated global audit trail. Filters: institution_id, action,
    actor_user_id — all optional and combinable, newest first."""
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
        "entries": [_audit_row_payload(r) for r in rows],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": max(1, -(-total // per_page)),
    })
