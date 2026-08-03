from flask import Blueprint, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from app.config import Config
from app.extensions import csrf, db, limiter
from app.integrations.translator import auto_translate
from app.integrations.translator import is_available as translator_available
from app.models import Course, Task, User
from app.services.statistics import all_courses_list, course_stats, get_user_stats
from app.utils.auth import api_auth_required, create_access_token, login_required
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
    course = db.session.get(Course, course_id) if course_id is not None else Course.query.filter_by(key=course_key).first()
    return course


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
    if User.query.filter_by(username=username).first():
        return _error("Username is already in use.", 409)
    user = User(username=username, password=generate_password_hash(password), fullname=fullname)
    db.session.add(user)
    db.session.commit()
    return jsonify({"user": {"id": user.id, "username": user.username, "fullname": user.fullname}, "access_token": create_access_token(user)}), 201


@api_bp.route("/auth/login", methods=["POST"])
@csrf.exempt
@limiter.limit(Config.RATELIMIT_AUTH)
def login():
    data = request.get_json(silent=True) or {}
    user = User.query.filter_by(username=str(data.get("username", "")).strip()).first()
    if not user or not check_password_hash(user.password, str(data.get("password", ""))):
        return _error("Invalid username or password.", 401)
    return jsonify({"user": {"id": user.id, "username": user.username, "fullname": user.fullname}, "access_token": create_access_token(user)})


@api_bp.route("/tasks", methods=["GET"])
@api_auth_required
def list_tasks():
    tasks = Task.query.filter_by(user_id=g.api_user.id).order_by(Task.created_at.desc(), Task.id.desc()).all()
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
    task = Task(user_id=g.api_user.id, course_id=course.id, course_key=course.key, title=str(data.get("title", "")).strip() or course.display_name(), description=str(data.get("description", "")).strip(), priority=priority, hours=hours, estimated_hours=hours)
    db.session.add(task)
    db.session.commit()
    return jsonify({"task": _task_payload(task)}), 201


@api_bp.route("/tasks/<int:task_id>", methods=["PUT"])
@csrf.exempt
@api_auth_required
def update_task(task_id):
    task = db.session.get(Task, task_id)
    if not task or task.user_id != g.api_user.id:
        return _error("Task not found.", 404)
    data = request.get_json(silent=True) or {}
    course = _resolve_course(data, task)
    if ("course_id" in data or "course_key" in data) and not course:
        return _error("Course not found.")
    if course:
        task.course, task.course_id, task.course_key = course, course.id, course.key
    if "title" in data: task.title = str(data["title"]).strip() or course.display_name()
    if "description" in data: task.description = str(data["description"]).strip()
    if "priority" in data:
        if not valid_priority(data["priority"]): return _error("Invalid priority.")
        task.priority = data["priority"]
    if "estimated_hours" in data:
        hours = positive_hours(data["estimated_hours"])
        if hours is None: return _error("estimated_hours must be between 0 and 24.")
        task.estimated_hours = task.hours = hours
    if "status" in data:
        if data["status"] == "completed": task.mark_complete()
        elif data["status"] == "pending": task.mark_pending()
        else: return _error("status must be pending or completed.")
    db.session.commit()
    return jsonify({"task": _task_payload(task)})


@api_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
@csrf.exempt
@api_auth_required
def delete_task(task_id):
    task = db.session.get(Task, task_id)
    if not task or task.user_id != g.api_user.id:
        return _error("Task not found.", 404)
    db.session.delete(task)
    db.session.commit()
    return "", 204


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
