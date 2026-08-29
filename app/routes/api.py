from flask import Blueprint, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from app.config import Config
from app.extensions import csrf, limiter
from app.integrations.translator import auto_translate
from app.integrations.translator import is_available as translator_available
from app.repositories import CourseRepo, MajorRepo, TaskRepo, UserRepo
from app.repositories.refresh_token_repo import RefreshTokenRepo
from app.services.statistics import all_courses_list, course_stats, get_user_stats
from app.utils.auth import (
    api_admin_required,
    api_auth_required,
    create_access_token,
    issue_refresh_token,
    login_required,
    rotate_refresh_token,
)
from app.utils.validation import positive_hours, valid_password, valid_priority, valid_username

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _error(message, status=400):
    return jsonify({"error": message}), status


def _task_payload(task):
    return {
        "id": task.id,
        "course_id": task.course_id,
        "course_key": task.course_key,
        "title": task.title or task.display_title(),
        "description": task.description or "",
        "priority": task.priority,
        "status": task.status,
        "estimated_hours": task.estimated_hours,
        "created_at": task.created_at.isoformat(),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


def _resolve_course(data, existing=None):
    course_id = data.get("course_id")
    course_key = data.get("course_key")
    if course_id is None and course_key is None:
        return existing.course if existing else None
    if course_id is not None:
        return CourseRepo.get(course_id)
    return CourseRepo.find_by_key(course_key)


@api_bp.route("/auth/register", methods=["POST"])
@csrf.exempt
@limiter.limit(Config.RATELIMIT_AUTH)
def register():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    fullname = str(data.get("fullname", "")).strip()
    if not fullname or not valid_username(username) or not valid_password(password):
        return _error("Username must be 3–80 letters, numbers, or underscores; password must be at least 8 characters.")
    if UserRepo.find_by_username(username):
        return _error("Username is already in use.", 409)
    user = UserRepo.create(
        username=username,
        password_hash=generate_password_hash(password),
        fullname=fullname,
    )
    return jsonify({"user": {"id": user.id, "username": user.username, "fullname": user.fullname}, "access_token": create_access_token(user), "refresh_token": issue_refresh_token(user)}), 201


@api_bp.route("/auth/login", methods=["POST"])
@csrf.exempt
@limiter.limit(Config.RATELIMIT_AUTH)
def login():
    data = request.get_json(silent=True) or {}
    user = UserRepo.find_by_username(str(data.get("username", "")).strip())
    if not user or not check_password_hash(user.password, str(data.get("password", ""))):
        return _error("Invalid username or password.", 401)
    return jsonify({"user": {"id": user.id, "username": user.username, "fullname": user.fullname}, "access_token": create_access_token(user), "refresh_token": issue_refresh_token(user)})


@api_bp.route("/auth/refresh", methods=["POST"])
@csrf.exempt
@limiter.limit(Config.RATELIMIT_AUTH)
def refresh():
    """Exchange a valid refresh token for a fresh access + refresh pair.

    Rotation: the presented refresh token is revoked; the response contains
    a new refresh token. Clients must replace their stored refresh token.
    """
    data = request.get_json(silent=True) or {}
    signed = str(data.get("refresh_token", "")).strip()
    if not signed:
        return _error("refresh_token is required.", 400)
    user, access, refresh_tok = rotate_refresh_token(signed)
    if user is None:
        return _error("Invalid or expired refresh token.", 401)
    # rotate_refresh_token -> issue_refresh_token already committed (revocation
    # + new row land in that single transaction); no extra commit needed.
    return jsonify({"access_token": access, "refresh_token": refresh_tok})


@api_bp.route("/auth/logout", methods=["POST"])
@csrf.exempt
@api_auth_required
def logout():
    """Revoke the presented refresh token (single-session logout).

    Requires a valid access token AND the matching refresh token — access
    tokens are stateless (15 min), so revoking the refresh token ends the
    token family: the client cannot mint further access tokens after the
    current one expires. Pass the refresh token as JSON `refresh_token`.
    Idempotent: revoking an already-revoked/unknown token still returns 204
    (no information leak, logout succeeds either way).
    """
    data = request.get_json(silent=True) or {}
    signed = str(data.get("refresh_token", "")).strip()
    if signed:
        RefreshTokenRepo.revoke_presented(g.api_user.id, signed)
    return "", 204


@api_bp.route("/me", methods=["GET"])
@api_auth_required
def me():
    """Current user profile from the Bearer access token."""
    user = g.api_user
    return jsonify({"user": {"id": user.id, "username": user.username, "fullname": user.fullname, "is_admin": user.is_admin, "theme": user.theme, "created_at": user.created_at.isoformat()}})


@api_bp.route("/me", methods=["PUT"])
@csrf.exempt
@api_auth_required
def update_me():
    """Update the current user's profile.

    `fullname` and `theme` are direct updates. Password change requires the
    current password (`current_password`) plus the new `password` (min 8
    chars); changing the password revokes every outstanding refresh token.
    """
    user = UserRepo.get_for_write(g.api_user.id)
    if user is None:
        return _error("User not found.", 401)
    data = request.get_json(silent=True) or {}

    if "fullname" in data:
        fullname = str(data["fullname"]).strip()
        if not fullname or len(fullname) > 150:
            return _error("fullname must be 1-150 characters.")
        user.fullname = fullname

    if "theme" in data:
        theme = str(data["theme"])
        if theme not in {"dark", "light"}:
            return _error("theme must be dark or light.")
        user.theme = theme

    if "password" in data:
        current_password = str(data.get("current_password", ""))
        new_password = str(data["password"])
        if not check_password_hash(user.password, current_password):
            return _error("Current password is incorrect.", 403)
        if not valid_password(new_password):
            return _error("Password must be at least 8 characters.")
        user.password = generate_password_hash(new_password)
        # The password changed: every outstanding refresh token is no longer
        # trustworthy, revoke them (the presented access token stays valid
        # until its 15-minute TTL — stateless by design).
        RefreshTokenRepo.revoke_all_for_user(user.id)

    UserRepo.commit()
    return jsonify({"user": {"id": user.id, "username": user.username, "fullname": user.fullname, "is_admin": user.is_admin, "theme": user.theme, "created_at": user.created_at.isoformat()}})


def _course_payload(course):
    return {"id": course.id, "key": course.key, "name_fa": course.name_fa, "name_en": course.name_en, "major_id": course.major_id}


def _major_payload(major):
    return {"id": major.id, "key": major.key, "name_fa": major.name_fa, "name_en": major.name_en, "courses": [_course_payload(c) for c in MajorRepo.list_courses_for_major(major.id)]}


@api_bp.route("/courses", methods=["GET"])
@api_auth_required
def list_courses():
    """All reference courses (read-only for any authenticated client).
    Language-neutral: both fa/en names are returned; the client renders one."""
    return jsonify({"courses": [_course_payload(c) for c in CourseRepo.list_all()]})


@api_bp.route("/majors", methods=["GET"])
@api_auth_required
def list_majors():
    """Major/course tree (read-only for any authenticated client).
    Language-neutral: both fa/en names are returned."""
    return jsonify({"majors": [_major_payload(m) for m in MajorRepo.list_all()]})


@api_bp.route("/courses", methods=["POST"])
@csrf.exempt
@api_admin_required
def create_course_api():
    data = request.get_json(silent=True) or {}
    name_fa = str(data.get("name_fa", "")).strip()
    name_en = str(data.get("name_en", "")).strip()
    raw_major_id = data.get("major_id")
    try:
        major = MajorRepo.get(int(raw_major_id)) if raw_major_id is not None else None
    except (TypeError, ValueError):
        major = None
    if not name_fa or not name_en or major is None:
        return _error("name_fa, name_en, and a valid major_id are required.")
    key = str(data.get("key") or name_en.lower().replace(" ", "_")).strip()
    if not key:
        return _error("key must not be empty.")
    if CourseRepo.find_by_key_major(key, major.id):
        return _error("A course with this key already exists for the major.", 409)
    course = CourseRepo.create(key=key, name_fa=name_fa, name_en=name_en, major_id=major.id)
    return jsonify({"course": _course_payload(course)}), 201


@api_bp.route("/courses/<int:course_id>", methods=["PUT"])
@csrf.exempt
@api_admin_required
def update_course_api(course_id):
    course = CourseRepo.get_for_write(course_id)
    if course is None:
        return _error("Course not found.", 404)
    data = request.get_json(silent=True) or {}
    if "name_fa" in data:
        name_fa = str(data["name_fa"]).strip()
        if not name_fa:
            return _error("name_fa must not be empty.")
        course.name_fa = name_fa
    if "name_en" in data:
        name_en = str(data["name_en"]).strip()
        if not name_en:
            return _error("name_en must not be empty.")
        course.name_en = name_en
    CourseRepo.commit()
    return jsonify({"course": _course_payload(course)})


@api_bp.route("/courses/<int:course_id>", methods=["DELETE"])
@csrf.exempt
@api_admin_required
def delete_course_api(course_id):
    """Archive-style delete: task rows survive with their legacy course_key
    (CourseRepo.delete_preserve_tasks). Matches the dashboard delete flow."""
    if CourseRepo.delete_preserve_tasks(course_id):
        return "", 204
    return _error("Course not found.", 404)


@api_bp.route("/majors", methods=["POST"])
@csrf.exempt
@api_admin_required
def create_major_api():
    data = request.get_json(silent=True) or {}
    name_fa = str(data.get("name_fa", "")).strip()
    name_en = str(data.get("name_en", "")).strip()
    if not name_fa or not name_en:
        return _error("name_fa and name_en are required.")
    key = str(data.get("key") or name_en.lower().replace(" ", "_")).strip()
    if not key:
        return _error("key must not be empty.")
    if MajorRepo.find_by_key(key):
        return _error("A major with this key already exists.", 409)
    major = MajorRepo.create(key=key, name_fa=name_fa, name_en=name_en)
    return jsonify({"major": _major_payload(major)}), 201


@api_bp.route("/majors/<int:major_id>", methods=["PUT"])
@csrf.exempt
@api_admin_required
def update_major_api(major_id):
    major = MajorRepo.get_for_write(major_id)
    if major is None:
        return _error("Major not found.", 404)
    data = request.get_json(silent=True) or {}
    if "name_fa" in data:
        name_fa = str(data["name_fa"]).strip()
        if not name_fa:
            return _error("name_fa must not be empty.")
        major.name_fa = name_fa
    if "name_en" in data:
        name_en = str(data["name_en"]).strip()
        if not name_en:
            return _error("name_en must not be empty.")
        major.name_en = name_en
    MajorRepo.commit()
    return jsonify({"major": _major_payload(major)})


@api_bp.route("/majors/<int:major_id>", methods=["DELETE"])
@csrf.exempt
@api_admin_required
def delete_major_api(major_id):
    """Protected key `computer_science` stays undeletable — matches the
    dashboard admin flow's guard."""
    major = MajorRepo.get(major_id)
    if major is None:
        return _error("Major not found.", 404)
    if major.key == "computer_science":
        return _error("The default major cannot be deleted.", 409)
    if MajorRepo.delete(major_id):
        return "", 204
    return _error("Major not found.", 404)


@api_bp.route("/tasks", methods=["GET"])
@api_auth_required
def list_tasks():
    page = request.args.get("page", type=int)
    per_page = request.args.get("per_page", type=int)
    # If either pagination param is set, both must be set; otherwise fall back
    # to the legacy "return everything" shape for backward compatibility.
    has_page = request.args.get("page") is not None
    has_per_page = request.args.get("per_page") is not None
    if has_page != has_per_page:
        return _error("page and per_page must be provided together.")
    if has_page and has_per_page:
        if page < 1:
            return _error("page must be >= 1.")
        if per_page < 1:
            return _error("per_page must be >= 1.")
        per_page = min(per_page, 100)
        # Flask-SQLAlchemy paginate() emits LIMIT/OFFSET at the SQL layer,
        # so we never materialise the whole rowset into memory.
        pagination = TaskRepo.list_for_user(g.api_user.id, page=page, per_page=per_page)
        return jsonify({"tasks": [_task_payload(task) for task in pagination.items], "page": pagination.page, "per_page": pagination.per_page, "total": pagination.total, "pages": pagination.pages})
    tasks = TaskRepo.list_for_user(g.api_user.id)
    return jsonify({"tasks": [_task_payload(task) for task in tasks]})


@api_bp.route("/tasks", methods=["POST"])
@csrf.exempt
@api_auth_required
def create_task():
    data = request.get_json(silent=True) or {}
    course = _resolve_course(data)
    hours = positive_hours(data.get("estimated_hours", 0))
    priority = data.get("priority", "medium")
    if not course:
        return _error("A valid course_id or course_key is required.")
    if hours is None or not valid_priority(priority):
        return _error("estimated_hours must be between 0 and 24 and priority must be low, medium, or high.")
    task = TaskRepo.create(
        user_id=g.api_user.id,
        course_id=course.id,
        course_key=course.key,
        title=str(data.get("title", "")).strip() or course.display_name(),
        description=str(data.get("description", "")).strip(),
        priority=priority,
        hours=hours,
    )
    return jsonify({"task": _task_payload(task)}), 201


@api_bp.route("/tasks/<int:task_id>", methods=["PUT"])
@csrf.exempt
@api_auth_required
def update_task(task_id):
    task = TaskRepo.get_for_write(task_id)
    if not task or task.user_id != g.api_user.id:
        return _error("Task not found.", 404)
    data = request.get_json(silent=True) or {}
    course = _resolve_course(data, task)
    if ("course_id" in data or "course_key" in data) and not course:
        return _error("Course not found.")
    fields = {}
    if course:
        TaskRepo.update_course_link(task, course)
    if "title" in data:
        fields["title"] = str(data["title"]).strip() or course.display_name()
    if "description" in data:
        fields["description"] = str(data["description"]).strip()
    if "priority" in data:
        if not valid_priority(data["priority"]):
            return _error("Invalid priority.")
        fields["priority"] = data["priority"]
    if "estimated_hours" in data:
        hours = positive_hours(data["estimated_hours"])
        if hours is None:
            return _error("estimated_hours must be between 0 and 24.")
        fields["estimated_hours"] = hours
    if "status" in data:
        if data["status"] == "completed":
            task.mark_complete()
        elif data["status"] == "pending":
            task.mark_pending()
        else:
            return _error("status must be pending or completed.")
    TaskRepo.update_fields(task, **fields)
    TaskRepo.commit()
    return jsonify({"task": _task_payload(task)})


@api_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
@csrf.exempt
@api_auth_required
def delete_task(task_id):
    task = TaskRepo.get_for_write(task_id)
    if not task or task.user_id != g.api_user.id:
        return _error("Task not found.", 404)
    TaskRepo.delete(task)
    return "", 204


def _session_payload(session):
    return {
        "id": session.id,
        "task_id": session.task_id,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "duration": session.duration,
        "is_open": session.is_open,
    }


@api_bp.route("/tasks/<int:task_id>/sessions", methods=["POST"])
@csrf.exempt
@api_auth_required
def start_session(task_id):
    """Open a new study session for a task owned by the caller.

    Returns 409 if there is already an open session for that task — clients
    must stop the existing one before starting another.
    """
    task = TaskRepo.get_for_write(task_id)
    if not task or task.user_id != g.api_user.id:
        return _error("Task not found.", 404)
    if TaskRepo.active_session(task.id) is not None:
        return _error("A session is already open for this task.", 409)
    session = TaskRepo.start_session(task)
    return jsonify({"session": _session_payload(session)}), 201


@api_bp.route("/tasks/<int:task_id>/sessions/<int:session_id>/stop", methods=["POST"])
@csrf.exempt
@api_auth_required
def stop_session(task_id, session_id):
    """Close an open study session owned by the caller. Idempotent: stopping
    an already-closed session returns 200 with the persisted duration.
    """
    task = TaskRepo.get_for_write(task_id)
    if not task or task.user_id != g.api_user.id:
        return _error("Task not found.", 404)
    session = TaskRepo.get_session_for_write(session_id)
    if not session or session.task_id != task_id:
        return _error("Session not found.", 404)
    if session.is_open:
        TaskRepo.stop_session(session)
    return jsonify({"session": _session_payload(session)})


@api_bp.route("/tasks/<int:task_id>/sessions", methods=["GET"])
@api_auth_required
def list_sessions(task_id):
    task = TaskRepo.get(task_id)
    if not task or task.user_id != g.api_user.id:
        return _error("Task not found.", 404)
    sessions = TaskRepo.list_sessions_for_task(task.id)
    return jsonify({"sessions": [_session_payload(s) for s in sessions]})


@api_bp.route("/statistics/dashboard", methods=["GET"])
@api_auth_required
def dashboard_statistics():
    stats = get_user_stats(g.api_user)
    courses = all_courses_list()
    return jsonify({
        "total_tasks": stats["total_tasks"],
        "total_done": stats["total_done"],
        "today_hours": stats["today_hours"],
        "week_hours": stats["week_hours"],
        "total_week_hours": stats["total_week_hours"],
        "month_hours": stats["month_hours"],
        "total_month_hours": stats["total_month_hours"],
        "courses": course_stats(stats["tasks"], courses),
    })


@api_bp.route("/translate", methods=["POST"])
@csrf.exempt
@login_required
def translate():
    text = (request.get_json(silent=True) or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "Text must not be empty."}), 400
    return jsonify(auto_translate(text))


@api_bp.route("/translator-status")
def translator_status():
    return jsonify({"available": translator_available()})
