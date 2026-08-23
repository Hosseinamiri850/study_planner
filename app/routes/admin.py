from collections import defaultdict
from datetime import date, timedelta

from flask import Blueprint, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from app.repositories import CourseRepo, MajorRepo, TaskRepo, UserRepo
from app.repositories.refresh_token_repo import RefreshTokenRepo
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

    users = UserRepo.list_non_admin()
    today, week_start = date.today(), date.today() - timedelta(days=7)
    users_stats = []
    for user in users:
        tasks = TaskRepo.list_for_user_raw(user.id)
        completed = [task for task in tasks if task.done]
        users_stats.append({"username": user.username, "fullname": user.fullname, "total_tasks": len(tasks), "done_tasks": len(completed), "today_hours": sum(task.hours for task in completed if task.created_at == today), "week_hours": sum(task.hours for task in completed if task.created_at >= week_start), "total_hours": sum(task.hours for task in completed), "created_at": str(user.created_at)})
    # System-wide hours-by-day via a single grouped SQL query instead of
    # loading every completed task and scanning 30 days in Python.
    rows = (
        TaskRepo.system_sum_hours_by_day()
    )
    hours_by_day = defaultdict(float)
    for row in rows:
        if row.day is not None:
            hours_by_day[row.day] += row.hours or 0
    system_week_hours, system_month_hours = {}, {}
    for offset in range(30):
        day = today - timedelta(days=offset)
        hours = hours_by_day[day]
        if offset < 7: system_week_hours[str(day)] = hours
        if hours: system_month_hours[str(day)] = hours
    admin_user = UserRepo.first_admin()
    return render_template(
        "admin.html",
        total_users=len(users),
        total_tasks_all=sum(TaskRepo.count_total_for_user(user.id) for user in users),
        total_done_all=sum(TaskRepo.count_done_for_user(user.id) for user in users),
        users_stats=users_stats,
        majors=majors_for_template(),
        theme=admin_user.theme if admin_user else "dark",
        system_week_hours=system_week_hours,
        system_month_hours=system_month_hours,
    )


def _handle_admin_action():
    action = request.form.get("action")
    if action == "delete_user":
        user = UserRepo.find_by_username(request.form.get("username"))
        if user and not user.is_admin: UserRepo.delete(user.id)
    elif action == "change_password":
        user, password = UserRepo.find_by_username(request.form.get("username")), request.form.get("new_password", "").strip()
        if user and valid_password(password):
            UserRepo.update_password(user, generate_password_hash(password))
            # Invalidate any outstanding API refresh tokens: the password
            # changed, so any prior session is no longer trustworthy.
            RefreshTokenRepo.revoke_all_for_user(user.id)
    elif action == "add_major": _create_major(request.form)
    elif action == "delete_major":
        major_id = request.form.get("major_id", type=int)
        major = MajorRepo.get(major_id)
        if major and major.key != "computer_science": MajorRepo.delete(major_id)
    elif action == "add_course": _create_course(request.form)
    elif action == "delete_course":
        course_id = request.form.get("course_id", type=int)
        course = CourseRepo.get(course_id)
        if course:
            CourseRepo.delete_preserve_tasks(course_id)
