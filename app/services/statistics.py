"""Read-model helpers for dashboard and administration statistics."""

from collections import defaultdict
from datetime import date, timedelta

from flask import session

from app.repositories import CourseRepo, MajorRepo, TaskRepo
from app.utils.caching import cached

# Hot read models shared by every dashboard/admin render. TTL is a safety
# net only — correctness comes from explicit invalidation on course/major
# writes (see the repos).
_COURSES_TTL = 300
_MAJORS_TTL = 300


def _request_lang():
    try:
        return session.get("lang", "fa")
    except RuntimeError:  # outside request context (scripts, some tests)
        return "fa"


@cached("courses", "all", _COURSES_TTL)
def _courses_rows_cached():
    """Language-neutral course rows. `display_name()` is request-scoped (it
    reads the session language), so it must NOT be baked into the cache —
    the raw fa/en names are cached and rendered per request in
    `all_courses_list`."""
    courses = CourseRepo.list_all()
    seen, result = set(), []
    for course in courses:
        if course.key not in seen:
            seen.add(course.key)
            result.append({"key": course.key, "name_fa": course.name_fa, "name_en": course.name_en})
    return result


def all_courses_list():
    rows = _courses_rows_cached()
    lang = _request_lang()
    return [{"key": row["key"], "name": row[f"name_{lang}"]} for row in rows]


def get_user_stats(user):
    today = date.today()
    tasks = TaskRepo.list_for_user_raw(user.id)
    completed = [task for task in tasks if task.done]
    rows = TaskRepo.sum_hours_by_day_for_user(user.id)
    hours_by_day = defaultdict(float)
    for row in rows:
        if row.day is not None:
            hours_by_day[row.day] += row.hours or 0
    week_hours = {str(today - timedelta(days=offset)): hours_by_day[today - timedelta(days=offset)] for offset in range(7)}
    month_hours = {
        str(day): hours
        for day, hours in ((today - timedelta(days=offset), hours_by_day[today - timedelta(days=offset)]) for offset in range(30))
        if hours > 0
    }
    return {
        "tasks": tasks,
        "total_tasks": len(tasks),
        "total_done": len(completed),
        "today_hours": hours_by_day[today],
        "week_hours": week_hours,
        "total_week_hours": sum(week_hours.values()),
        "month_hours": month_hours,
        "total_month_hours": sum(month_hours.values()),
    }


def course_stats(tasks, courses):
    return {
        course["key"]: {
            "name": course["name"],
            "total": len([task for task in tasks if task.course_key == course["key"]]),
            "done": len([task for task in tasks if task.course_key == course["key"] and task.done]),
            "hours": sum(task.hours for task in tasks if task.course_key == course["key"] and task.done),
        }
        for course in courses
    }


@cached("majors", "template", _MAJORS_TTL)
def _majors_rows_cached():
    """Language-neutral major/course tree — same reasoning as
    `_courses_rows_cached`: names are rendered per request."""
    return [
        {
            "id": major.id,
            "key": major.key,
            "name_fa": major.name_fa,
            "name_en": major.name_en,
            "courses": [
                {"id": c.id, "key": c.key, "name_fa": c.name_fa, "name_en": c.name_en}
                for c in major.courses
            ],
        }
        for major in MajorRepo.list_all()
    ]


def majors_for_template():
    payload = _majors_rows_cached()
    lang = _request_lang()
    for major in payload:
        major["name"] = major[f"name_{lang}"]
        for course in major["courses"]:
            course["name"] = course[f"name_{lang}"]
    return payload
