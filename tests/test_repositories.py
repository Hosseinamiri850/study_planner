"""Tests for the repository/data-access layer (TASK-039).

Cover repo CRUD + list/pagination for TaskRepo, CourseRepo, MajorRepo,
UserRepo, and RefreshTokenRepo. Uses the in-memory SQLite conftest app, so
no replica is configured here — the read/write split seam is exercised in
`test_replication_seam.py`.
"""

from datetime import date

from app.repositories import (
    CourseRepo,
    MajorRepo,
    RefreshTokenRepo,
    TaskRepo,
    UserRepo,
)


class TestTaskRepo:
    def test_create_and_get(self, create_user, create_course):
        user, course = create_user(), create_course()
        task = TaskRepo.create(
            user_id=user.id,
            course_id=course.id,
            course_key=course.key,
            title="Read",
            description="ch1",
            priority="high",
            hours=2.0,
        )
        assert task.id is not None
        assert task.estimated_hours == 2.0
        assert task.hours == 2.0
        assert TaskRepo.get(task.id).title == "Read"

    def test_list_for_user_newest_first(self, create_user, create_task):
        user = create_user()
        t1 = create_task(user=user, title="t1")
        t2 = create_task(user=user, title="t2")
        ids = [task.id for task in TaskRepo.list_for_user(user.id)]
        assert ids == [t2.id, t1.id]

    def test_list_for_user_pagination(self, create_user, create_task):
        user = create_user()
        for i in range(5):
            create_task(user=user, title=f"t{i}")
        page1 = TaskRepo.list_for_user(user.id, page=1, per_page=2)
        page2 = TaskRepo.list_for_user(user.id, page=2, per_page=2)
        assert page1.total == 5
        assert len(page1.items) == 2
        assert len(page2.items) == 2
        assert page1.pages == 3

    def test_counts(self, create_user, create_task):
        user = create_user()
        create_task(user=user, done=False)
        create_task(user=user, done=True)
        assert TaskRepo.count_total_for_user(user.id) == 2
        assert TaskRepo.count_done_for_user(user.id) == 1

    def test_mark_complete_and_pending(self, create_user, create_task):
        task = create_task(user=create_user(), done=False)
        TaskRepo.mark_complete(task)
        assert task.done is True
        assert task.status == "completed"
        assert TaskRepo.count_done_for_user(task.user_id) == 1
        TaskRepo.mark_pending(task)
        assert task.done is False
        assert task.status == "pending"
        assert task.completed_at is None

    def test_update_fields_mirrors_hours(self, create_user, create_task):
        task = create_task(user=create_user(), hours=1.0)
        TaskRepo.update_fields(task, estimated_hours=4.5, priority="low")
        TaskRepo.commit()
        assert task.estimated_hours == 4.5
        assert task.hours == 4.5
        assert task.priority == "low"

    def test_update_course_link(self, create_user, create_task, create_course):
        task = create_task(user=create_user())
        course = create_course()
        TaskRepo.update_course_link(task, course)
        TaskRepo.commit()
        assert task.course_id == course.id
        assert task.course_key == course.key

    def test_update_course_link_no_match_keeps_submitted_key(self, create_user, create_task):
        # Editing a task to a course_key with no matching course must still
        # write the submitted key to the legacy column (CLAUDE.md: never
        # silently stop writing to one side).
        task = create_task(user=create_user(), title="legacy")
        original_key = task.course_key
        TaskRepo.update_course_link(task, None, course_key="nonexistent_key")
        TaskRepo.commit()
        fresh = TaskRepo.get_for_write(task.id)
        assert fresh.course_id is None
        assert fresh.course_key == "nonexistent_key"
        assert fresh.course_key != original_key

    def test_delete(self, create_user, create_task):
        task = create_task(user=create_user())
        TaskRepo.delete(task)
        assert TaskRepo.get(task.id) is None

    def test_start_and_stop_session(self, create_user, create_task):
        task = create_task(user=create_user())
        session = TaskRepo.start_session(task)
        assert session.id is not None
        assert TaskRepo.active_session(task.id).id == session.id
        TaskRepo.stop_session(session)
        assert TaskRepo.active_session(task.id) is None
        assert session.duration is not None and session.duration >= 0

    def test_list_sessions_for_task(self, create_user, create_task):
        task = create_task(user=create_user())
        s1 = TaskRepo.start_session(task)
        TaskRepo.stop_session(s1)
        s2 = TaskRepo.start_session(task)
        TaskRepo.stop_session(s2)
        sessions = TaskRepo.list_sessions_for_task(task.id)
        assert [s.id for s in sessions] == [s2.id, s1.id]  # newest first

    def test_get_session(self, create_user, create_task):
        task = create_task(user=create_user())
        session = TaskRepo.start_session(task)
        assert TaskRepo.get_session(session.id).id == session.id

    def test_sum_seconds_by_day_for_user(self, create_user, create_task, create_study_session):
        from datetime import datetime, timedelta

        user = create_user()
        today = date.today()
        yesterday = today - timedelta(days=1)
        task = create_task(user=user, hours=2.0, done=True)
        create_study_session(task=task, duration=3600, started_at=datetime(today.year, today.month, today.day, 10))
        create_study_session(task=task, duration=1800, started_at=datetime(yesterday.year, yesterday.month, yesterday.day, 10))
        rows = TaskRepo.sum_seconds_by_day_for_user(user.id)
        by_day = {str(r.day): r.seconds for r in rows}
        assert by_day[str(today)] == 3600
        assert by_day[str(yesterday)] == 1800

    def test_sum_seconds_by_day_excludes_open_sessions(self, create_user, create_task, create_study_session):
        from datetime import datetime

        user = create_user()
        task = create_task(user=user, done=True)
        create_study_session(task=task, duration=None, started_at=datetime(date.today().year, date.today().month, date.today().day, 10), ended_at=None)
        rows = TaskRepo.sum_seconds_by_day_for_user(user.id)
        assert all(r.day is None or r.seconds == 0 for r in rows)

    def test_sum_seconds_by_course_for_user(self, create_user, create_course, create_task, create_study_session):
        from datetime import datetime

        user = create_user()
        course = create_course()
        task1 = create_task(user=user, course=course, done=True)
        task2 = create_task(user=user, course=course, done=True)
        noon = datetime(date.today().year, date.today().month, date.today().day, 12)
        create_study_session(task=task1, duration=3600, started_at=noon)
        create_study_session(task=task2, duration=900, started_at=noon)
        rows = TaskRepo.sum_seconds_by_course_for_user(user.id)
        by_key = {r.course_key: r.seconds for r in rows}
        assert by_key[course.key] == 4500

    def test_system_sum_seconds_by_day(self, create_user, create_task, create_study_session):
        from datetime import datetime

        task = create_task(user=create_user(), hours=1.0, done=True)
        noon = datetime(date.today().year, date.today().month, date.today().day, 12)
        create_study_session(task=task, duration=3600, started_at=noon)
        rows = TaskRepo.system_sum_seconds_by_day()
        assert len(rows) >= 1


class TestCourseRepo:
    def test_get_and_find_by_key(self, create_course):
        course = create_course(key="data_structures")
        assert CourseRepo.get(course.id).id == course.id
        assert CourseRepo.find_by_key("data_structures").id == course.id

    def test_find_by_key_major(self, create_major, create_course):
        major = create_major()
        c1 = create_course(key="algo", major=major)
        assert CourseRepo.find_by_key_major("algo", major.id).id == c1.id
        assert CourseRepo.find_by_key_major("algo", major.id + 999) is None

    def test_list_all_joins_major(self, create_major, create_course):
        m1, m2 = create_major(name_en="A"), create_major(name_en="B")
        create_course(major=m1, name_en="c1")
        create_course(major=m2, name_en="c2")
        keys = [c.name_en for c in CourseRepo.list_all()]
        assert keys == ["c1", "c2"]

    def test_list_for_major(self, create_major, create_course):
        m = create_major()
        create_course(major=m, name_en="x")
        create_course(major=m, name_en="y")
        assert len(CourseRepo.list_for_major(m.id)) == 2

    def test_create_and_delete_preserve_tasks(self, create_user, create_course, create_task):
        course = create_course(key="text")
        task = create_task(course=course, user=create_user())
        # task.course_id points at the course.
        assert TaskRepo.get(task.id).course_id == course.id
        CourseRepo.delete_preserve_tasks(course.id)
        assert CourseRepo.get(course.id) is None
        # Task survives with null course_id, legacy course_key intact.
        fresh = TaskRepo.get_for_write(task.id)
        assert fresh.course_id is None
        assert fresh.course_key == "text"


class TestMajorRepo:
    def test_get_and_find_by_key(self, create_major):
        major = create_major(key="cs")
        assert MajorRepo.get(major.id).id == major.id
        assert MajorRepo.find_by_key("cs").id == major.id

    def test_list_all_ordered(self, create_major):
        create_major(name_en="Zeta")
        create_major(name_en="Alpha")
        names = [m.name_en for m in MajorRepo.list_all()]
        assert names == ["Alpha", "Zeta"]

    def test_majors_for_template_shape(self, app, create_major, create_course):
        m = create_major(key="cs", name_en="Computer Science")
        create_course(key="algo", major=m, name_en="Algorithms")
        # display_name() reads the session-backed language preference, so this
        # read-model helper needs a request context like the templates do.
        with app.test_request_context():
            payload = MajorRepo.majors_for_template()
        assert isinstance(payload, list)
        cs = next(p for p in payload if p["key"] == "cs")
        assert cs["name"]
        assert cs["courses"][0]["key"] == "algo"

    def test_add_flush_and_commit(self, create_major):
        from app.models import Major

        m = Major(key="flush_test_major", name_fa="m", name_en="M")
        MajorRepo.add_flush(m)
        assert m.id is not None  # flush assigned id without commit.
        MajorRepo.commit()
        assert MajorRepo.find_by_key("flush_test_major") is not None

    def test_delete(self, create_major):
        major = create_major(key="del")
        assert MajorRepo.delete(major.id) is True
        assert MajorRepo.find_by_key("del") is None

    def test_delete_missing_is_noop(self, app):
        assert MajorRepo.delete(999999) is False


class TestUserRepo:
    def test_find_by_username(self, create_user):
        user = create_user(username="alice")
        assert UserRepo.find_by_username("alice").id == user.id
        assert UserRepo.find_by_username("nobody") is None

    def test_list_non_admin_and_admin(self, create_user):
        create_user(username="stu1", is_admin=False)
        create_user(username="admin1", is_admin=True)
        non_admin_names = [u.username for u in UserRepo.list_non_admin()]
        admin_names = [u.username for u in UserRepo.list_admin()]
        assert "stu1" in non_admin_names and "admin1" not in non_admin_names
        assert "admin1" in admin_names

    def test_first_admin(self, create_user):
        create_user(username="a", is_admin=True)
        assert UserRepo.first_admin() is not None

    def test_create_add_delete(self, create_user):
        from werkzeug.security import generate_password_hash

        u = UserRepo.create(
            username="repo_user",
            password_hash=generate_password_hash("testpass123"),
            fullname="Repo User",
        )
        assert UserRepo.find_by_username("repo_user").id == u.id
        assert UserRepo.delete(u.id) is True
        assert UserRepo.find_by_username("repo_user") is None

    def test_delete_missing_is_noop(self, app):
        assert UserRepo.delete(999999) is False

    def test_update_password(self, app, create_user):
        user = create_user(username="pw")
        with app.app_context():
            # update_password stages only; the admin flow commits it together
            # with the refresh-token revocation in one transaction.
            UserRepo.update_password(user, "newhash123")
            UserRepo.commit()
        assert UserRepo.find_by_username("pw").password == "newhash123"

    def test_update_theme(self, create_user):
        user = create_user(username="th")
        UserRepo.update_theme(user, "light")
        assert UserRepo.find_by_username("th").theme == "light"


class TestRefreshTokenRepo:
    def test_issue_find_revoke(self, create_user):
        user = create_user(username="tok")
        RefreshTokenRepo.issue(user, "jti-1")
        row = RefreshTokenRepo.find_by_jti("jti-1")
        assert row is not None and row.revoked is False
        RefreshTokenRepo.revoke(row)
        RefreshTokenRepo.commit()
        assert RefreshTokenRepo.find_by_jti("jti-1").revoked is True

    def test_revoke_all_for_user(self, create_user):
        user = create_user(username="multi")
        for jti in ("a", "b", "c"):
            RefreshTokenRepo.issue(user, jti)
        RefreshTokenRepo.revoke_all_for_user(user.id)
        for jti in ("a", "b", "c"):
            assert RefreshTokenRepo.find_by_jti(jti).revoked is True
