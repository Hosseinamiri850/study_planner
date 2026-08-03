from datetime import date, timedelta

from app.services.statistics import all_courses_list, course_stats, get_user_stats, majors_for_template


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

    def test_user_stats_with_completed_tasks_today(self, app, create_user, create_task):
        with app.test_request_context():
            user = create_user()
            today = date.today()
            create_task(user=user, done=True, hours=2.0, created_at=today)
            create_task(user=user, done=True, hours=1.5, created_at=today)
            create_task(user=user, done=False, hours=3.0)
            stats = get_user_stats(user)
            assert stats["today_hours"] == 3.5
            assert stats["total_week_hours"] == 3.5

    def test_user_stats_pending_tasks_not_counted(self, create_user, create_task):
        user = create_user()
        create_task(user=user, done=False, hours=10.0)
        stats = get_user_stats(user)
        assert stats["today_hours"] == 0
        assert stats["total_done"] == 0
        assert stats["total_tasks"] == 1

    def test_user_stats_week_calculation(self, app, create_user, create_task):
        with app.test_request_context():
            user = create_user()
            today = date.today()
            week_ago = today - timedelta(days=6)
            old_day = today - timedelta(days=10)
            create_task(user=user, done=True, hours=1.0, created_at=week_ago)
            create_task(user=user, done=True, hours=2.0, created_at=old_day)
            stats = get_user_stats(user)
            assert stats["total_week_hours"] == 1.0
            assert stats["total_month_hours"] == 3.0


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

    def test_course_stats_calculations(self, app, create_user, create_course, create_task):
        with app.test_request_context():
            user = create_user()
            course = create_course(key="py_stats", name_fa="پایتون", name_en="Python")
            create_task(user=user, course=course, done=True, hours=5.0)
            create_task(user=user, course=course, done=True, hours=3.0)
            create_task(user=user, course=course, done=False, hours=2.0)
            tasks = user.tasks.all()
            courses = [{"key": "py_stats", "name": "پایتون"}]
            stats = course_stats(tasks, courses)
            assert stats["py_stats"]["total"] == 3
            assert stats["py_stats"]["done"] == 2
            assert stats["py_stats"]["hours"] == 8.0

    def test_course_stats_multiple_courses(self, app, create_user, create_course, create_task):
        with app.test_request_context():
            user = create_user()
            course1 = create_course(key="py_multi", name_fa="پایتون", name_en="Python")
            course2 = create_course(key="js_multi", name_fa="جاوا", name_en="Java")
            create_task(user=user, course=course1, done=True, hours=5.0)
            create_task(user=user, course=course2, done=False, hours=3.0)
            tasks = user.tasks.all()
            courses = [
                {"key": "py_multi", "name": "پایتون"},
                {"key": "js_multi", "name": "جاوا"},
            ]
            stats = course_stats(tasks, courses)
            assert stats["py_multi"]["total"] == 1
            assert stats["py_multi"]["done"] == 1
            assert stats["py_multi"]["hours"] == 5.0
            assert stats["js_multi"]["total"] == 1
            assert stats["js_multi"]["done"] == 0
            assert stats["js_multi"]["hours"] == 0


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
