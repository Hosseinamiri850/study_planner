from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import User, Course, Major, Task, StudySession
from app.services.statistics import get_user_stats, all_courses_list, course_stats, majors_for_template
from app.services.seed import seed_reference_data
from sqlalchemy.exc import IntegrityError


class TestUserModel:
    def test_create_user(self, create_user):
        user = create_user(username="alice", password="password123", fullname="Alice Smith")
        assert user.id is not None
        assert user.username == "alice"
        assert user.fullname == "Alice Smith"
        assert user.is_admin is False
        assert user.theme == "dark"
        assert user.created_at == date.today()

    def test_user_password_hashing(self, create_user):
        user = create_user(password="securepass")
        assert user.password != "securepass"
        assert len(user.password) > 20

    def test_admin_user(self, create_user):
        admin = create_user(username="admin", is_admin=True)
        assert admin.is_admin is True

    def test_user_tasks_relationship(self, create_user, create_task):
        user = create_user()
        task1 = create_task(user=user)
        task2 = create_task(user=user)
        assert user.tasks.count() == 2
        assert task1.user == user
        assert task2.user == user


class TestMajorModel:
    def test_create_major(self, create_major):
        major = create_major(key="math", name_fa="ریاضی", name_en="Mathematics")
        assert major.id is not None
        assert major.key == "math"
        assert major.name_fa == "ریاضی"
        assert major.name_en == "Mathematics"

    def test_major_courses_relationship(self, create_major, create_course):
        major = create_major()
        course1 = create_course(major=major)
        course2 = create_course(major=major)
        assert major.courses.count() == 2
        assert course1.major == major


class TestCourseModel:
    def test_create_course(self, create_course, create_major):
        major = create_major(key="cs")
        course = create_course(major=major, key="python")
        assert course.id is not None
        assert course.key == "python"
        assert course.major == major

    def test_course_unique_constraint(self, create_course, create_major):
        major = create_major()
        create_course(major=major, key="unique_course")
        with pytest.raises(IntegrityError):
            db.session.add(Course(key="unique_course", name_fa="تکراری", name_en="Duplicate", major_id=major.id))
            db.session.commit()
        db.session.rollback()


class TestTaskModel:
    def test_create_task(self, create_task, create_user, create_course):
        user = create_user()
        course = create_course()
        task = create_task(user=user, course=course, title="My Task", hours=2.5)
        assert task.id is not None
        assert task.title == "My Task"
        assert task.hours == 2.5
        assert task.done is False
        assert task.status == "pending"
        assert task.priority == "medium"

    def test_mark_complete(self, create_task):
        task = create_task()
        assert task.done is False
        assert task.status == "pending"
        assert task.completed_at is None
        task.mark_complete()
        db.session.commit()
        assert task.done is True
        assert task.status == "completed"
        assert task.completed_at is not None

    def test_mark_pending(self, create_task):
        task = create_task()
        task.mark_complete()
        db.session.commit()
        task.mark_pending()
        db.session.commit()
        assert task.done is False
        assert task.status == "pending"
        assert task.completed_at is None

    def test_display_title_with_course(self, app, create_task, create_course):
        from flask import session
        with app.test_request_context():
            session["lang"] = "fa"
            course = create_course(name_fa="داده‌ساختار", name_en="Data Structures")
            task = create_task(course=course, title="")
            assert "داده‌ساختار" in task.display_title()

    def test_display_title_without_course(self, create_task):
        task = create_task(title="Standalone Task")
        assert task.display_title() == "Standalone Task"


class TestStudySessionModel:
    def test_create_study_session(self, create_study_session, create_task):
        task = create_task()
        session = create_study_session(task=task, duration=90)
        assert session.id is not None
        assert session.duration == 90
        assert session.task == task
        assert session.started_at is not None

    def test_task_study_sessions_relationship(self, create_task, create_study_session):
        task = create_task()
        session1 = create_study_session(task=task)
        session2 = create_study_session(task=task)
        assert task.study_sessions.count() == 2
        assert session1.task == task
        assert session2.task == task


class TestStatisticsService:
    def test_get_user_stats_empty(self, create_user):
        user = create_user()
        stats = get_user_stats(user)
        assert stats["total_tasks"] == 0
        assert stats["total_done"] == 0
        assert stats["today_hours"] == 0
        assert stats["total_week_hours"] == 0
        assert stats["total_month_hours"] == 0

    def test_get_user_stats_with_tasks(self, app, create_user, create_task):
        from flask import session
        with app.test_request_context():
            session["lang"] = "fa"
            user = create_user()
            today = date.today()
            create_task(user=user, done=True, hours=2.0, created_at=today)
            create_task(user=user, done=True, hours=1.5, created_at=today)
            create_task(user=user, done=False, hours=3.0)
            stats = get_user_stats(user)
            assert stats["total_tasks"] == 3
            assert stats["total_done"] == 2
            assert stats["today_hours"] == 3.5

    def test_get_user_stats_week_calculation(self, app, create_user, create_task):
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

    def test_all_courses_list(self, app, create_course, create_major):
        with app.test_request_context():
            major1 = create_major(key="cs_major", name_fa="کامپیوتر", name_en="CS")
            major2 = create_major(key="math_major", name_fa="ریاضی", name_en="Math")
            c1 = create_course(major=major1, key="algo", name_fa="الگوریتم", name_en="Algo")
            c2 = create_course(major=major2, key="calc", name_fa="حسابان", name_en="Calc")
            courses = all_courses_list()
            assert len(courses) == 2
            keys = {c["key"] for c in courses}
            assert "algo" in keys
            assert "calc" in keys

    def test_all_courses_list_deduplicates(self, app, create_course, create_major):
        with app.test_request_context():
            major1 = create_major(key="m1")
            major2 = create_major(key="m2")
            create_course(major=major1, key="shared", name_fa="اولی", name_en="First")
            create_course(major=major2, key="shared", name_fa="دومی", name_en="Second")
            courses = all_courses_list()
            shared = [c for c in courses if c["key"] == "shared"]
            assert len(shared) == 1

    def test_course_stats(self, app, create_user, create_course, create_task):
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

    def test_majors_for_template(self, app, create_major, create_course):
        with app.test_request_context():
            major = create_major(key="cs_tpl", name_fa="کامپیوتر", name_en="CS")
            create_course(major=major, key="algo_tpl", name_fa="الگوریتم", name_en="Algo")
            majors = majors_for_template()
            assert len(majors) == 1
            assert majors[0]["key"] == "cs_tpl"
            assert len(majors[0]["courses"]) == 1
            assert majors[0]["courses"][0]["key"] == "algo_tpl"


class TestSeedService:
    def test_seed_reference_data_idempotent(self, app):
        seed_reference_data()
        majors_before = Major.query.count()
        courses_before = Course.query.count()
        seed_reference_data()
        assert Major.query.count() == majors_before
        assert Course.query.count() == courses_before

    def test_seed_reference_data_creates_majors(self, app):
        Major.query.delete()
        Course.query.delete()
        db.session.commit()
        seed_reference_data()
        assert Major.query.count() > 0
        assert Major.query.filter_by(key="computer_science").first() is not None

    def test_seed_reference_data_creates_courses(self, app):
        Major.query.delete()
        Course.query.delete()
        db.session.commit()
        seed_reference_data()
        assert Course.query.count() > 0
        cs_courses = Course.query.join(Major).filter(Major.key == "computer_science").all()
        assert len(cs_courses) == 13
