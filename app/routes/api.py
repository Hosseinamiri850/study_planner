from flask import Blueprint, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from app.config import Config
from app.extensions import csrf, limiter
from app.integrations.translator import auto_translate
from app.integrations.translator import is_available as translator_available
from app.repositories import CourseRepo, TaskRepo, UserRepo
from app.services.statistics import all_courses_list, course_stats, get_user_stats
from app.utils.auth import (
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
