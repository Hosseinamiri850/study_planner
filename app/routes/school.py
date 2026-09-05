"""Institution-scoped API for school administrators (TASK-038).

Every endpoint filters by the actor's institution_id and returns 403 when
a resource's institution differs — the cross-institution rule lives in
`_reject_foreign` and is applied to every path-parameter resource. Reads
list only rows sharing the actor's institution_id.

No list-anything-without-institution endpoint exists by design: a
school_admin cannot enumerate users of other institutions (the UsersRepo
lookups here go through institution-filtered queries, not bare ids).
"""

from flask import Blueprint, g, jsonify, request

from app.extensions import csrf
from app.models import User
from app.models.user import ROLE_STUDENT, ROLE_TEACHER
from app.repositories import ClassRepo
from app.repositories.user_repo import UserRepo
from app.services.audit import record as audit_record
from app.utils.school import _reject_foreign, school_admin_required

school_bp = Blueprint("school", __name__, url_prefix="/api/school")

CLASS_NAME_MAX = 150
GRADE_LEVEL_MAX = 30


def _user_payload(user):
    return {"id": user.id, "username": user.username, "fullname": user.fullname, "role": user.role, "class_id": user.class_id}


def _class_payload(klass):
    return {"id": klass.id, "institution_id": klass.institution_id, "name": klass.name, "grade_level": klass.grade_level}


def _users_of_institution(institution_id, roles):
    return (
        User.query.filter(User.institution_id == institution_id, User.role.in_(roles))
        .order_by(User.fullname, User.id)
        .all()
    )


@school_bp.route("/overview", methods=["GET"])
@csrf.exempt
@school_admin_required
def overview():
    """Students, teachers, and classes of the actor's institution."""
    institution_id = g.api_user.institution_id
    students = _users_of_institution(institution_id, (ROLE_STUDENT,))
    teachers = _users_of_institution(institution_id, (ROLE_TEACHER,))
    classes = ClassRepo.list_for_institution(institution_id)
    return jsonify({
        "institution_id": institution_id,
        "students": [_user_payload(u) for u in students],
        "teachers": [_user_payload(u) for u in teachers],
        "classes": [_class_payload(c) for c in classes],
    })


@school_bp.route("/users", methods=["GET"])
@csrf.exempt
@school_admin_required
def list_users():
    """Students + teachers of my institution, optionally by role."""
    institution_id = g.api_user.institution_id
    role = request.args.get("role")
    if role == "student":
        users = _users_of_institution(institution_id, (ROLE_STUDENT,))
    elif role == "teacher":
        users = _users_of_institution(institution_id, (ROLE_TEACHER,))
    else:
        users = _users_of_institution(institution_id, (ROLE_STUDENT, ROLE_TEACHER))
    return jsonify({"users": [_user_payload(u) for u in users]})


@school_bp.route("/classes", methods=["GET"])
@csrf.exempt
@school_admin_required
def list_classes():
    """Classes of my institution."""
    classes = ClassRepo.list_for_institution(g.api_user.institution_id)
    return jsonify({"classes": [_class_payload(c) for c in classes]})


@school_bp.route("/classes", methods=["POST"])
@csrf.exempt
@school_admin_required
def create_class():
    """Create a class inside my institution."""
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    grade_level = str(data.get("grade_level", "")).strip() or None
    if not name:
        return jsonify({"error": "name is required."}), 400
    if len(name) > CLASS_NAME_MAX or (grade_level and len(grade_level) > GRADE_LEVEL_MAX):
        return jsonify({"error": "name or grade_level exceeds its length limit."}), 400
    klass = ClassRepo.create(institution_id=g.api_user.institution_id, name=name, grade_level=grade_level)
    audit_record(g.api_user, "class.create", ("class", klass.id), after=_class_payload(klass))
    return jsonify({"class": _class_payload(klass)}), 201


@school_bp.route("/classes/<int:class_id>", methods=["PUT"])
@csrf.exempt
@school_admin_required
def update_class(class_id):
    """Rename/re-grade a class — 403 when it belongs to another institution."""
    klass = ClassRepo.get_for_write(class_id)
    if klass is None:
        return jsonify({"error": "Class not found."}), 404
    forbidden = _reject_foreign(klass.institution_id, g.api_user.institution_id)
    if forbidden is not None:
        return forbidden
    data = request.get_json(silent=True) or {}
    before = _class_payload(klass)
    fields = {}
    if "name" in data:
        name = str(data["name"]).strip()
        if not name or len(name) > CLASS_NAME_MAX:
            return jsonify({"error": "name must be 1-150 characters."}), 400
        fields["name"] = name
    if "grade_level" in data:
        grade_level = str(data["grade_level"]).strip()
        if grade_level and len(grade_level) > GRADE_LEVEL_MAX:
            return jsonify({"error": "grade_level must be at most 30 characters."}), 400
        fields["grade_level"] = grade_level or None
    ClassRepo.update_fields(klass, **fields)
    ClassRepo.commit()
    audit_record(g.api_user, "class.update", ("class", class_id), before=before, after=_class_payload(klass))
    return jsonify({"class": _class_payload(klass)})


@school_bp.route("/users/<int:user_id>", methods=["PUT"])
@csrf.exempt
@school_admin_required
def assign_class(user_id):
    """Assign one of my institution's students/teachers to a class of mine.

    class_id=null clears the assignment. 403 when the target user or the
    class belongs to another institution — the user's existence in another
    institution is not revealed by the response either way.
    """
    actor = g.api_user
    target = UserRepo.get_for_write(user_id)
    if target is None:
        return jsonify({"error": "User not found."}), 404
    if target.institution_id != actor.institution_id or target.role not in (ROLE_STUDENT, ROLE_TEACHER):
        return jsonify({"error": "This resource belongs to another institution."}), 403
    data = request.get_json(silent=True) or {}
    if "class_id" not in data:
        return jsonify({"error": "class_id is required (null to clear)."}), 400
    raw_class_id = data.get("class_id")
    if raw_class_id is not None:
        try:
            class_id = int(raw_class_id)
        except (TypeError, ValueError):
            return jsonify({"error": "class_id must be an integer or null."}), 400
        klass = ClassRepo.get(class_id)
        if klass is None:
            return jsonify({"error": "Class not found."}), 404
        forbidden = _reject_foreign(klass.institution_id, actor.institution_id)
        if forbidden is not None:
            return forbidden
    else:
        class_id = None
    before = _user_payload(target)
    target.class_id = class_id
    UserRepo.commit()
    audit_record(
        actor,
        "user.class_assign",
        ("user", user_id),
        before=before,
        after={**before, "class_id": class_id},
    )
    return jsonify({"user": _user_payload(target)})
