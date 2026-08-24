from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.config import Config
from app.extensions import limiter
from app.repositories import CourseRepo, MajorRepo, TaskRepo, UserRepo
from app.services.statistics import all_courses_list, course_stats, get_user_stats, majors_for_template
from app.utils.auth import current_user, login_required
from app.utils.i18n import SUPPORTED_LANGS, t
from app.utils.validation import positive_hours, valid_password, valid_priority, valid_username

web_bp = Blueprint("web", __name__)


@web_bp.route("/")
def home():
    """Intentionally redirect-only (TASK-040): the product is the
    authenticated app, so anonymous visitors land on /login and users go
    straight to their dashboard/admin panel. No public landing page by
    design — revisit when the Next.js migration adds public pages."""
    user = current_user()
    if user:
        return redirect(url_for("admin.admin_panel") if user.is_admin else url_for("web.dashboard"))
    return redirect(url_for("web.login"))


@web_bp.route("/set-lang/<lang>")
def set_lang(lang):
    if lang in SUPPORTED_LANGS:
        session["lang"] = lang
    return redirect(request.referrer or url_for("web.home"))


@web_bp.route("/login", methods=["GET", "POST"])
@limiter.limit(Config.RATELIMIT_AUTH, methods=["POST"])
def login():
    if request.method == "POST":
        user = UserRepo.find_by_username(request.form.get("username", "").strip())
        if user and check_password_hash(user.password, request.form.get("password", "")):
            session["username"] = user.username
            return redirect(url_for("admin.admin_panel") if user.is_admin else url_for("web.dashboard"))
        flash(t("auth.invalid_credentials"), "error")
    return render_template("login.html")


@web_bp.route("/register", methods=["GET", "POST"])
@limiter.limit(Config.RATELIMIT_AUTH, methods=["POST"])
def register():
    if request.method == "POST":
        username, password, fullname = (request.form.get(field, "").strip() for field in ("username", "password", "fullname"))
        if not username or not password or not fullname:
            flash(t("auth.fill_all_fields"), "error")
        elif not valid_username(username) or not valid_password(password):
            flash("Username must be 3–80 letters, numbers, or underscores; password must be at least 8 characters.", "error")
        elif UserRepo.find_by_username(username):
            flash(t("auth.username_taken"), "error")
        else:
            UserRepo.create(username=username, password_hash=generate_password_hash(password), fullname=fullname)
            flash(t("auth.register_success"), "success")
            return redirect(url_for("web.login"))
    return render_template("register.html")


@web_bp.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("web.login"))


@web_bp.route("/toggle-theme", methods=["POST"])
@login_required
def toggle_theme():
    user = current_user()
    UserRepo.update_theme(user, "light" if user.theme == "dark" else "dark")
    return jsonify({"theme": user.theme})


@web_bp.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    user = current_user()
    if user.is_admin:
        return redirect(url_for("admin.admin_panel"))
    if request.method == "POST":
        _handle_dashboard_action(user)
        return redirect(url_for("web.dashboard"))
    stats, courses = get_user_stats(user), all_courses_list()
    users = []
    for other_user in UserRepo.list_non_admin():
        other_stats = get_user_stats(other_user)
        users.append({"username": other_user.username, "fullname": other_user.fullname, "total_tasks": other_stats["total_tasks"], "done_tasks": other_stats["total_done"], "today_hours": other_stats["today_hours"], "is_current": other_user.id == user.id})
    return render_template("dashboard.html", current_user=user.username, fullname=user.fullname, courses=courses, course_stats=course_stats(stats["tasks"], courses), all_users=users, theme=user.theme, majors=majors_for_template(), today=str(date.today()), **stats)


def _handle_dashboard_action(user):
    action = request.form.get("action")
    # Mutations follow: load via the write session so updates persist to the
    # primary even when a replica serves reads.
    task = TaskRepo.get_for_write(request.form.get("task_id", type=int)) if action in {"toggle", "delete", "edit", "start_session", "stop_session"} else None
    if action == "new_task" and request.form.get("course_key"):
        hours = positive_hours(request.form.get("task_hours"))
        if hours is None or not valid_priority(request.form.get("priority", "medium")):
            flash("Enter valid task hours (0–24) and priority.", "error")
            return
        course_key = request.form["course_key"]
        course = CourseRepo.find_by_key(course_key)
        TaskRepo.create(
            user_id=user.id,
            course_id=course.id if course else None,
            course_key=course_key,
            title=course.display_name() if course else course_key,
            description=request.form.get("description", "").strip(),
            priority=request.form.get("priority", "medium"),
            hours=hours,
        )
    elif task and task.user_id == user.id:
        if action == "toggle":
            TaskRepo.mark_pending(task) if task.done else TaskRepo.mark_complete(task)
        elif action == "delete":
            TaskRepo.delete(task)
        elif action == "start_session":
            if TaskRepo.active_session(task.id) is None:
                TaskRepo.start_session(task)
            else:
                flash("A session is already running for this task.", "error")
        elif action == "stop_session":
            sess = TaskRepo.active_session(task.id)
            if sess is not None:
                TaskRepo.stop_session(sess)
            else:
                flash("No active session to stop.", "error")
        elif action == "edit":
            course_key = request.form.get("course_key", task.course_key)
            priority = request.form.get("priority", task.priority)
            description = request.form.get("description", "")
            course = CourseRepo.find_by_key(course_key)
            TaskRepo.update_course_link(task, course, course_key=course_key)
            task.title = course.display_name() if course else course_key
            hours = positive_hours(request.form.get("task_hours"))
            TaskRepo.update_fields(task, priority=priority, description=description, estimated_hours=hours if hours is not None else task.estimated_hours)
            TaskRepo.commit()
    elif action == "add_major":
        _create_major(request.form)
    elif action == "add_course":
        _create_course(request.form)
    elif action == "delete_course":
        course = CourseRepo.get(request.form.get("course_id", type=int))
        if course:
            CourseRepo.delete_preserve_tasks(course)


def _create_major(form):
    name_fa, name_en = form.get("name_fa", "").strip(), form.get("name_en", "").strip()
    key = name_en.lower().replace(" ", "_")
    if name_fa and name_en and not MajorRepo.find_by_key(key):
        MajorRepo.create(key=key, name_fa=name_fa, name_en=name_en)


def _create_course(form):
    major = MajorRepo.find_by_key(form.get("major_key"))
    name_fa, name_en = form.get("name_fa", "").strip(), form.get("name_en", "").strip()
    key = name_en.lower().replace(" ", "_")
    if major and name_fa and name_en and not CourseRepo.find_by_key_major(key, major.id):
        CourseRepo.create(key=key, name_fa=name_fa, name_en=name_en, major_id=major.id)


@web_bp.route("/user/<username>")
@login_required
def view_user(username):
    target, viewer = UserRepo.find_by_username(username), current_user()
    if not target or target.is_admin:
        flash(t("admin.unauthorized"), "error")
        return redirect(url_for("web.dashboard"))
    stats, courses = get_user_stats(target), all_courses_list()
    return render_template("view_user.html", viewed_user=target.username, fullname=target.fullname, courses=courses, course_stats=course_stats(stats["tasks"], courses), is_own_profile=target.id == viewer.id, theme=viewer.theme, today=str(date.today()), **stats)
