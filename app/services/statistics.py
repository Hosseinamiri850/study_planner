"""Read-model helpers for dashboard and administration statistics."""

from datetime import date, timedelta

from app.models import Course, Major


def get_user_stats(user):
    today = date.today()
    tasks = user.tasks.all()
    completed = [task for task in tasks if task.done]
    hours_for = lambda day: sum(task.hours for task in completed if task.created_at == day)
    week_hours = {str(today - timedelta(days=offset)): hours_for(today - timedelta(days=offset)) for offset in range(7)}
    month_hours = {
        str(today - timedelta(days=offset)): hours_for(today - timedelta(days=offset))
        for offset in range(30)
        if hours_for(today - timedelta(days=offset)) > 0
    }
    return {
        "tasks": tasks,
        "total_tasks": len(tasks),
        "total_done": len(completed),
        "today_hours": hours_for(today),
        "week_hours": week_hours,
        "total_week_hours": sum(week_hours.values()),
        "month_hours": month_hours,
        "total_month_hours": sum(month_hours.values()),
    }


def all_courses_list():
    courses = Course.query.join(Major).order_by(Major.name_en, Course.name_en).all()
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
    return [
        {"key": major.key, "name": major.display_name(), "courses": [{"key": course.key, "name": course.display_name()} for course in major.courses]}
        for major in Major.query.order_by(Major.name_en).all()
    ]
