from datetime import date, timedelta

from flask import Blueprint, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from app.repositories import CourseRepo, MajorRepo, TaskRepo, UserRepo
from app.repositories.refresh_token_repo import RefreshTokenRepo
from app.routes.web import _create_course, _create_major
from app.services.audit import record as audit_record
from app.services.statistics import hours_map_by_day, majors_for_template
from app.utils.auth import admin_required, current_user
from app.utils.validation import valid_password

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin", methods=["GET", "POST"])
@admin_required
def admin_panel():
    if request.method == "POST":
        _handle_admin_action()
        return redirect(url_for("admin.admin_panel"))

    users = UserRepo.list_non_admin()
    today = date.today()
    users_stats = []
    for user in users:
        tasks = TaskRepo.list_for_user_raw(user.id)
        completed = [task for task in tasks if task.done]
        # Tracked session time (TASK-027), not estimated task hours.
        hours_by_day = hours_map_by_day(TaskRepo.sum_seconds_by_day_for_user(user.id))
        users_stats.append({"username": user.username, "fullname": user.fullname, "total_tasks": len(tasks), "done_tasks": len(completed), "today_hours": hours_by_day[today], "week_hours": sum(hours for day, hours in hours_by_day.items() if day > today - timedelta(days=7)), "total_hours": sum(hours_by_day.values()), "created_at": str(user.created_at)})
    # System-wide study-time-by-day via a single grouped SQL query instead of
    # loading every completed task and scanning 30 days in Python.
    hours_by_day = hours_map_by_day(TaskRepo.system_sum_seconds_by_day())
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
    actor = current_user()
    if action == "delete_user":
        user = UserRepo.find_by_username(request.form.get("username"))
        if user and not user.is_admin:
            UserRepo.delete(user.id)
            audit_record(actor, "user.delete", ("user", user.id), before={"username": user.username})
    elif action == "change_password":
        user, password = UserRepo.find_by_username(request.form.get("username")), request.form.get("new_password", "").strip()
        if user and valid_password(password):
            UserRepo.update_password(user, generate_password_hash(password))
            # Invalidate any outstanding API refresh tokens: the password
            # changed, so any prior session is no longer trustworthy.
            RefreshTokenRepo.revoke_all_for_user(user.id)
            UserRepo.commit()
            # No before/after snapshot: the password hash must never land in
            # the audit trail, only the fact that it changed.
            audit_record(actor, "user.password_change", ("user", user.id))
    elif action == "add_major":
        _create_major(request.form)
    elif action == "delete_major":
        major_id = request.form.get("major_id", type=int)
        major = MajorRepo.get(major_id)
        if major and major.key != "computer_science":
            before = {"key": major.key, "name_fa": major.name_fa, "name_en": major.name_en}
            MajorRepo.delete(major_id)
            audit_record(actor, "major.delete", ("major", major_id), before=before)
    elif action == "add_course":
        _create_course(request.form)
    elif action == "delete_course":
        course_id = request.form.get("course_id", type=int)
        course = CourseRepo.get(course_id)
        if course:
            before = {"key": course.key, "name_fa": course.name_fa, "name_en": course.name_en, "major_id": course.major_id}
            CourseRepo.delete_preserve_tasks(course_id)
            audit_record(actor, "course.delete", ("course", course_id), before=before)
