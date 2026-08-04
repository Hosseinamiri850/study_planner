from collections import defaultdict
from datetime import date, timedelta

from flask import Blueprint, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import Course, Major, Task, User
from app.models.refresh_token import revoke_user_refresh_tokens
from app.routes.web import _create_course, _create_major
from app.services.statistics import majors_for_template
from app.utils.auth import admin_required
from app.utils.validation import valid_password

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin", methods=["GET", "POST"])
@admin_required
def admin_panel():
    if request.method == "POST":
        _handle_admin_action()
        return redirect(url_for("admin.admin_panel"))

    users = User.query.filter_by(is_admin=False).all()
    today, week_start = date.today(), date.today() - timedelta(days=7)
    users_stats = []
    for user in users:
        tasks = user.tasks.all()
        completed = [task for task in tasks if task.done]
        users_stats.append({"username": user.username, "fullname": user.fullname, "total_tasks": len(tasks), "done_tasks": len(completed), "today_hours": sum(task.hours for task in completed if task.created_at == today), "week_hours": sum(task.hours for task in completed if task.created_at >= week_start), "total_hours": sum(task.hours for task in completed), "created_at": str(user.created_at)})
    completed_tasks = Task.query.filter_by(done=True).all()
    # Single pass over completed tasks: sum hours by completed-day.
    hours_by_day = defaultdict(float)
    for task in completed_tasks:
        if task.created_at is not None:
            hours_by_day[task.created_at] += task.hours or 0
    system_week_hours, system_month_hours = {}, {}
    for offset in range(30):
        day = today - timedelta(days=offset)
        hours = hours_by_day[day]
        if offset < 7: system_week_hours[str(day)] = hours
        if hours: system_month_hours[str(day)] = hours
    admin_user = User.query.filter_by(is_admin=True).first()
    return render_template("admin.html", total_users=len(users), total_tasks_all=sum(user.tasks.count() for user in users), total_done_all=sum(user.tasks.filter_by(done=True).count() for user in users), users_stats=users_stats, majors=majors_for_template(), theme=admin_user.theme if admin_user else "dark", system_week_hours=system_week_hours, system_month_hours=system_month_hours)


def _handle_admin_action():
    action = request.form.get("action")
    if action == "delete_user":
        user = User.query.filter_by(username=request.form.get("username")).first()
        if user and not user.is_admin: db.session.delete(user)
    elif action == "change_password":
        user, password = User.query.filter_by(username=request.form.get("username")).first(), request.form.get("new_password", "").strip()
        if user and valid_password(password):
            user.password = generate_password_hash(password)
            # Invalidate any outstanding API refresh tokens: the password
            # changed, so any prior session is no longer trustworthy.
            revoke_user_refresh_tokens(user.id)
    elif action == "add_major": _create_major(request.form)
    elif action == "delete_major":
        major = db.session.get(Major, request.form.get("major_id", type=int))
        if major and major.key != "computer_science": db.session.delete(major)
    elif action == "add_course": _create_course(request.form)
    elif action == "delete_course":
        course = db.session.get(Course, request.form.get("course_id", type=int))
        if course:
            # Preserve historical tasks when an administrator removes a course.
            Task.query.filter_by(course_id=course.id).update({"course_id": None})
            db.session.delete(course)
    db.session.commit()
