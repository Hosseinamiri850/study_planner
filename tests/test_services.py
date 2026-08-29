from datetime import date, datetime, timedelta

from app.services.statistics import all_courses_list, course_stats, get_user_stats, majors_for_template


def _dt(day, hour=12, minute=0):
    """Naive timestamp on `day` (session columns are naive UTC)."""
    return datetime(day.year, day.month, day.day, hour, minute)


class TestGetUserStats:
    def test_empty_user_stats(self, create_user):
        user = create_user()
        stats = get_user_stats(user)
        assert stats["total_tasks"] == 0
        assert stats["total_done"] == 0
        assert stats["today_hours"] == 0
        assert stats["total_week_hours"] == 0
        assert stats["total_month_hours"] == 0
        assert "tasks" in stats
        assert "week_hours" in stats
        assert "month_hours" in stats

    def test_stats_from_study_sessions_not_task_hours(self, app, create_user, create_task, create_study_session):
        """The TASK-027 contract: hours come from tracked session durations
        bucketed by started_at day — NOT from task.hours on created_at."""
        with app.test_request_context():
            user = create_user()
            today = date.today()
            # Estimated hours 2.0/1.5 would show 3.5 under the old signal;
            # tracked time is 1.0 + 0.5.
            task1 = create_task(user=user, done=True, hours=2.0, created_at=today)
            task2 = create_task(user=user, done=True, hours=1.5, created_at=today)
            create_study_session(task=task1, duration=3600, started_at=_dt(today, 10), ended_at=_dt(today, 11))
            create_study_session(task=task2, duration=1800, started_at=_dt(today, 12), ended_at=_dt(today, 12, 30))
            stats = get_user_stats(user)
            assert stats["today_hours"] == 1.5
            assert stats["total_week_hours"] == 1.5

    def test_estimated_hours_without_sessions_count_zero(self, create_user, create_task):
        """A completed task with no tracked sessions contributes no hours —
        estimate is not treated as real study time."""
        user = create_user()
        create_task(user=user, done=True, hours=5.0)
        stats = get_user_stats(user)
        assert stats["today_hours"] == 0
        assert stats["total_week_hours"] == 0
        assert stats["total_done"] == 1  # task still counted as done

    def test_open_session_excluded(self, create_user, create_task, create_study_session):
        """An open session (duration NULL) is not counted anywhere."""
        user = create_user()
        task = create_task(user=user, done=False, hours=2.0)
        create_study_session(task=task, duration=None, started_at=_dt(date.today(), 9), ended_at=None)
        stats = get_user_stats(user)
        assert stats["today_hours"] == 0
        assert stats["total_week_hours"] == 0

    def test_zero_duration_session_counted_as_zero(self, create_user, create_task, create_study_session):
        user = create_user()
        task = create_task(user=user, done=True)
        create_study_session(task=task, duration=0, started_at=_dt(date.today()), ended_at=_dt(date.today()))
        stats = get_user_stats(user)
        assert stats["today_hours"] == 0

    def test_pending_task_sessions_still_counted(self, app, create_user, create_task, create_study_session):
        """Studying happens on pending tasks too — session time counts
        regardless of the task's done status."""
        with app.test_request_context():
            user = create_user()
            task = create_task(user=user, done=False, hours=1.0)
            create_study_session(task=task, duration=1800, started_at=_dt(date.today(), 10), ended_at=_dt(date.today(), 10, 30))
            stats = get_user_stats(user)
            assert stats["today_hours"] == 0.5
            assert stats["total_week_hours"] == 0.5

    def test_session_on_other_users_task_not_counted(self, create_user, create_task, create_study_session):
        owner, other = create_user(), create_user()
        task = create_task(user=owner, done=True)
        create_study_session(task=task, duration=3600, started_at=_dt(date.today(), 10), ended_at=_dt(date.today(), 11))
        stats = get_user_stats(other)
        assert stats["today_hours"] == 0

    def test_user_stats_week_calculation(self, app, create_user, create_task, create_study_session):
        with app.test_request_context():
            user = create_user()
            today = date.today()
            week_ago = today - timedelta(days=6)
            old_day = today - timedelta(days=10)
            task_week = create_task(user=user, done=True, created_at=week_ago)
            task_old = create_task(user=user, done=True, created_at=old_day)
            create_study_session(task=task_week, duration=3600, started_at=_dt(week_ago, 10), ended_at=_dt(week_ago, 11))
            create_study_session(task=task_old, duration=7200, started_at=_dt(old_day, 10), ended_at=_dt(old_day, 12))
            stats = get_user_stats(user)
            assert stats["total_week_hours"] == 1.0
            assert stats["total_month_hours"] == 3.0

    def test_sessions_bucketed_by_started_day_not_creation(self, app, create_user, create_task, create_study_session):
        """A session that started yesterday shows on yesterday, even if the
        task row was created today."""
        with app.test_request_context():
            user = create_user()
            yesterday = date.today() - timedelta(days=1)
            task = create_task(user=user, done=True, created_at=date.today())
            create_study_session(task=task, duration=1800, started_at=_dt(yesterday, 22), ended_at=_dt(yesterday, 22, 30))
            stats = get_user_stats(user)
            assert stats["week_hours"][str(yesterday)] == 0.5
            assert stats["today_hours"] == 0


class TestAllCoursesList:
    def test_empty_list(self, app):
        with app.test_request_context():
            courses = all_courses_list()
            assert courses == []

    def test_list_sorted_by_name(self, app, create_course, create_major):
        with app.test_request_context():
            major = create_major()
            create_course(major=major, key="zebra", name_fa="زebra", name_en="Zebra")
            create_course(major=major, key="apple", name_fa="apple", name_en="Apple")
            create_course(major=major, key="mango", name_fa="mango", name_en="Mango")
            courses = all_courses_list()
            assert len(courses) == 3
            names = [c["name"] for c in courses]
            assert names == sorted(names)

    def test_deduplicates_by_key(self, app, create_course, create_major):
        with app.test_request_context():
            major1 = create_major(key="m1_svc")
            major2 = create_major(key="m2_svc")
            create_course(major=major1, key="shared", name_fa="اولی", name_en="First")
            create_course(major=major2, key="shared", name_fa="دومی", name_en="Second")
            courses = all_courses_list()
            shared = [c for c in courses if c["key"] == "shared"]
            assert len(shared) == 1


class TestCourseStats:
    def test_empty_stats(self, app, create_course, create_major):
        with app.test_request_context():
            major = create_major()
            create_course(major=major, key="empty")
            courses = [{"key": "empty", "name": "Empty"}]
            tasks = []
            stats = course_stats(tasks, courses)
            assert stats["empty"]["total"] == 0
            assert stats["empty"]["done"] == 0
            assert stats["empty"]["hours"] == 0

    def test_course_stats_uses_tracked_time(self, app, create_user, create_course, create_task, create_study_session):
        """Per-course hours come from tracked sessions via the course_hours
        map — not summed task.hours estimates."""
        with app.test_request_context():
            user = create_user()
            course = create_course(key="py_stats", name_fa="پایتون", name_en="Python")
            task1 = create_task(user=user, course=course, done=True, hours=5.0)
            task2 = create_task(user=user, course=course, done=True, hours=3.0)
            create_task(user=user, course=course, done=False, hours=2.0)
            create_study_session(task=task1, duration=3600, started_at=_dt(date.today(), 10), ended_at=_dt(date.today(), 11))
            create_study_session(task=task2, duration=1800, started_at=_dt(date.today(), 12), ended_at=_dt(date.today(), 12, 30))
            tasks = user.tasks.all()
            courses = [{"key": "py_stats", "name": "پایتون"}]
            stats = get_user_stats(user)
            result = course_stats(tasks, courses, stats["course_hours"])
            assert result["py_stats"]["total"] == 3
            assert result["py_stats"]["done"] == 2
            assert result["py_stats"]["hours"] == 1.5  # tracked, not 8.0 estimated

    def test_course_stats_multiple_courses(self, app, create_user, create_course, create_task, create_study_session):
        with app.test_request_context():
            user = create_user()
            course1 = create_course(key="py_multi", name_fa="پایتون", name_en="Python")
            course2 = create_course(key="js_multi", name_fa="جاوا", name_en="Java")
            task1 = create_task(user=user, course=course1, done=True, hours=5.0)
            create_task(user=user, course=course2, done=False, hours=3.0)
            create_study_session(task=task1, duration=3600, started_at=_dt(date.today(), 10), ended_at=_dt(date.today(), 11))
            tasks = user.tasks.all()
            courses = [
                {"key": "py_multi", "name": "پایتون"},
                {"key": "js_multi", "name": "جاوا"},
            ]
            stats = get_user_stats(user)
            result = course_stats(tasks, courses, stats["course_hours"])
            assert result["py_multi"]["total"] == 1
            assert result["py_multi"]["done"] == 1
            assert result["py_multi"]["hours"] == 1.0
            assert result["js_multi"]["total"] == 1
            assert result["js_multi"]["done"] == 0
            assert result["js_multi"]["hours"] == 0


class TestMajorsForTemplate:
    def test_empty_majors(self, app):
        with app.test_request_context():
            majors = majors_for_template()
            assert majors == []

    def test_single_major_with_courses(self, app, create_major, create_course):
        with app.test_request_context():
            major = create_major(key="cs_tpl_2", name_fa="کامپیوتر", name_en="CS")
            create_course(major=major, key="algo_tpl", name_fa="الگوریتم", name_en="Algo")
            create_course(major=major, key="ds_tpl", name_fa="داده struct", name_en="DS")
            majors = majors_for_template()
            assert len(majors) == 1
            assert majors[0]["key"] == "cs_tpl_2"
            assert len(majors[0]["courses"]) == 2

    def test_multiple_majors_sorted(self, app, create_major, create_course):
        with app.test_request_context():
            major_z = create_major(key="z_tpl", name_fa="مست", name_en="Z")
            major_a = create_major(key="a_tpl", name_fa="اولی", name_en="A")
            create_course(major=major_z)
            create_course(major=major_a)
            majors = majors_for_template()
            keys = [m["key"] for m in majors]
            assert keys == ["a_tpl", "z_tpl"]
