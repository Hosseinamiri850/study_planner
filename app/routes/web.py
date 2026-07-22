from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import Course, Major, Task, User
from app.services.statistics import all_courses_list, course_stats, get_user_stats, majors_for_template
from app.utils.auth import current_user, login_required
from app.utils.i18n import SUPPORTED_LANGS, t


web_bp = Blueprint("web", __name__)


@web_bp.route("/")
def home():
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
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username", "").strip()).first()
        if user and check_password_hash(user.password, request.form.get("password", "")):
            session["username"] = user.username
            return redirect(url_for("admin.admin_panel") if user.is_admin else url_for("web.dashboard"))
        flash(t("auth.invalid_credentials"), "error")
    return render_template("login.html")


@web_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username, password, fullname = (request.form.get(field, "").strip() for field in ("username", "password", "fullname"))
        if not username or not password or not fullname:
            flash(t("auth.fill_all_fields"), "error")
        elif User.query.filter_by(username=username).first():
            flash(t("auth.username_taken"), "error")
        else:
            db.session.add(User(username=username, password=generate_password_hash(password), fullname=fullname))
            db.session.commit()
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
    user.theme = "light" if user.theme == "dark" else "dark"
    db.session.commit()
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
    for other_user in User.query.filter_by(is_admin=False).all():
        other_stats = get_user_stats(other_user)
        users.append({"username": other_user.username, "fullname": other_user.fullname, "total_tasks": other_stats["total_tasks"], "done_tasks": other_stats["total_done"], "today_hours": other_stats["today_hours"], "is_current": other_user.id == user.id})
    return render_template("dashboard.html", current_user=user.username, fullname=user.fullname, courses=courses, course_stats=course_stats(stats["tasks"], courses), all_users=users, theme=user.theme, majors=majors_for_template(), today=str(date.today()), **stats)


def _handle_dashboard_action(user):
    action = request.form.get("action")
    task = db.session.get(Task, request.form.get("task_id", type=int)) if action in {"toggle", "delete", "edit"} else None
    if action == "new_task" and request.form.get("course_key"):
        try:
            hours = float(request.form.get("task_hours", "0"))
        except ValueError:
            hours = 0.0
        db.session.add(Task(user_id=user.id, course_key=request.form["course_key"], description=request.form.get("description", "").strip(), priority=request.form.get("priority", "medium"), hours=hours))
    elif task and task.user_id == user.id:
        if action == "toggle": task.done = not task.done
        elif action == "delete": db.session.delete(task)
        elif action == "edit":
            task.course_key, task.priority, task.description = request.form.get("course_key", task.course_key), request.form.get("priority", task.priority), request.form.get("description", "")
            try: task.hours = float(request.form.get("task_hours", "0"))
            except ValueError: pass
    elif action == "add_major":
        _create_major(request.form)
    elif action == "add_course":
        _create_course(request.form)
    elif action == "delete_course":
        course = db.session.get(Course, request.form.get("course_id", type=int))
        if course: db.session.delete(course)
    db.session.commit()


def _create_major(form):
    name_fa, name_en = form.get("name_fa", "").strip(), form.get("name_en", "").strip()
    key = name_en.lower().replace(" ", "_")
    if name_fa and name_en and not Major.query.filter_by(key=key).first(): db.session.add(Major(key=key, name_fa=name_fa, name_en=name_en))


def _create_course(form):
    major, name_fa, name_en = Major.query.filter_by(key=form.get("major_key")).first(), form.get("name_fa", "").strip(), form.get("name_en", "").strip()
    key = name_en.lower().replace(" ", "_")
    if major and name_fa and name_en and not Course.query.filter_by(key=key, major_id=major.id).first(): db.session.add(Course(key=key, name_fa=name_fa, name_en=name_en, major_id=major.id))


@web_bp.route("/user/<username>")
@login_required
def view_user(username):
    target, viewer = User.query.filter_by(username=username).first(), current_user()
    if not target or target.is_admin:
        flash(t("admin.unauthorized"), "error")
        return redirect(url_for("web.dashboard"))
    stats, courses = get_user_stats(target), all_courses_list()
    return render_template("view_user.html", viewed_user=target.username, fullname=target.fullname, courses=courses, course_stats=course_stats(stats["tasks"], courses), is_own_profile=target.id == viewer.id, theme=viewer.theme, today=str(date.today()), **stats)
