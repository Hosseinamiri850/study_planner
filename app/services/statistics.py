"""Read-model helpers for dashboard and administration statistics."""

from collections import defaultdict
from datetime import date, timedelta

from app.repositories import CourseRepo, MajorRepo, TaskRepo


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


def all_courses_list():
    courses = CourseRepo.list_all()
    seen, result = set(), []
    for course in courses:
        if course.key not in seen:
            seen.add(course.key)
            result.append({"key": course.key, "name": course.display_name()})
    return result


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


def majors_for_template():
    return MajorRepo.majors_for_template()
