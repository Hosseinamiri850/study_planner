"""Read-model helpers for dashboard and administration statistics."""

from collections import defaultdict
from datetime import date, datetime, timedelta

from flask import session

from app.repositories import CourseRepo, MajorRepo, TaskRepo
from app.utils.caching import cached

# Hot read models shared by every dashboard/admin render. TTL is a safety
# net only — correctness comes from explicit invalidation on course/major
# writes (see the repos).
_COURSES_TTL = 300
_MAJORS_TTL = 300

SECONDS_PER_HOUR = 3600.0


def _request_lang():
    try:
        return session.get("lang", "fa")
    except RuntimeError:  # outside request context (scripts, some tests)
        return "fa"


def _coerce_date(value):
    """Normalize a day bucket to `date`. func.date() yields TEXT on SQLite
    and DATE (datetime.date) on PostgreSQL; rows round-trip both ways."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def hours_map_by_day(rows):
    """(seconds, day) repo rows -> {date: hours} with open sessions (NULL
    duration summed as 0 by COALESCE) collapsed correctly."""
    hours = defaultdict(float)
    for row in rows:
        if row.day is None:
            continue
        hours[_coerce_date(row.day)] += (row.seconds or 0) / SECONDS_PER_HOUR
    return hours


def _hours_by_course(rows):
    """(course_key, seconds) repo rows -> {course_key: hours}."""
    hours = defaultdict(float)
    for row in rows:
        hours[row.course_key] += (row.seconds or 0) / SECONDS_PER_HOUR
    return hours


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
    # Hours come from tracked StudySession time (TASK-027), bucketed by the
    # day each session started — not estimated task hours on created_at.
    hours_by_day = hours_map_by_day(TaskRepo.sum_seconds_by_day_for_user(user.id))
    course_hours = _hours_by_course(TaskRepo.sum_seconds_by_course_for_user(user.id))
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
        "course_hours": course_hours,
    }


def course_stats(tasks, courses, course_hours=None):
    """Per-course totals. `hours` is tracked session time per course key
    (pass `get_user_stats(...)["course_hours"]`); tasks themselves carry no
    hours signal anymore — actual time lives on their study sessions."""
    course_hours = course_hours or {}
    return {
        course["key"]: {
            "name": course["name"],
            "total": len([task for task in tasks if task.course_key == course["key"]]),
            "done": len([task for task in tasks if task.course_key == course["key"] and task.done]),
            "hours": round(course_hours.get(course["key"], 0.0), 2),
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
