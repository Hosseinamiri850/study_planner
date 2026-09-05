"""Tests for browser routes in app/routes/admin.py (TASK-015).

Covers admin panel access control, user deletion, password change, major/
course CRUD, and the delete_course task-preservation behavior. CSRF is
disabled in TestConfig so form POSTs succeed without a token.
"""

from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import Course, Major, Task, User


def login_admin(client, create_user, username="superadmin"):
    create_user(username=username, password="validpass123", is_admin=True)
    with client.session_transaction() as sess:
        sess["username"] = username


class TestAdminAccess:
    def test_admin_requires_login(self, client):
        r = client.get("/admin")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_admin_rejects_non_admin(self, client, create_user):
        create_user(username="regular")
        with client.session_transaction() as sess:
            sess["username"] = "regular"
        r = client.get("/admin")
        assert r.status_code == 302
        assert "/dashboard" in r.headers["Location"]

    def test_admin_renders_for_admin(self, client, create_user):
        login_admin(client, create_user)
        assert client.get("/admin").status_code == 200


class TestAdminUserManagement:
    def test_admin_deletes_non_admin_user(self, client, create_user):
        login_admin(client, create_user)
        create_user(username="victim")
        assert User.query.filter_by(username="victim").first() is not None
        client.post("/admin", data={"action": "delete_user", "username": "victim"})
        assert User.query.filter_by(username="victim").first() is None

    def test_admin_cannot_delete_admin(self, client, create_user):
        login_admin(client, create_user, username="adminone")
        create_user(username="admintwo", is_admin=True)
        client.post("/admin", data={"action": "delete_user", "username": "admintwo"})
        # admintwo must survive — admins are protected.
        assert User.query.filter_by(username="admintwo").first() is not None

    def test_admin_cannot_delete_self_silently_no_admin_removal(self, client, create_user):
        login_admin(client, create_user, username="adminone")
        create_user(username="admintwo", is_admin=True)
        client.post("/admin", data={"action": "delete_user", "username": "adminone"})
        assert User.query.filter_by(username="adminone").first() is not None

    def test_admin_changes_password(self, client, create_user):
        login_admin(client, create_user)
        create_user(username="pwuser", password="oldpasspass")
        client.post("/admin", data={
            "action": "change_password", "username": "pwuser",
            "new_password": "brandnewpass123"
        })
        user = User.query.filter_by(username="pwuser").first()
        assert check_password_hash(user.password, "brandnewpass123")
        assert not check_password_hash(user.password, "oldpasspass")

    def test_admin_rejects_short_new_password(self, client, create_user):
        login_admin(client, create_user)
        create_user(username="pwuser", password="oldpasspass")
        client.post("/admin", data={
            "action": "change_password", "username": "pwuser",
            "new_password": "short"
        })
        user = User.query.filter_by(username="pwuser").first()
        assert check_password_hash(user.password, "oldpasspass")  # unchanged
        assert not check_password_hash(user.password, "short")

    def test_admin_change_password_unknown_user_noop(self, client, create_user):
        login_admin(client, create_user)
        client.post("/admin", data={
            "action": "change_password", "username": "ghost",
            "new_password": "brandnewpass123"
        })
        assert User.query.filter_by(username="ghost").first() is None


class TestMajorCrud:
    def test_admin_creates_major(self, client, create_user):
        login_admin(client, create_user)
        client.post("/admin", data={
            "action": "add_major", "name_fa": "ریاضی", "name_en": "Mathematics"
        })
        major = Major.query.filter_by(key="mathematics").first()
        assert major is not None
        assert major.name_en == "Mathematics"

    def test_admin_duplicate_major_ignored(self, client, create_user):
        login_admin(client, create_user)
        client.post("/admin", data={
            "action": "add_major", "name_fa": "ریاضی", "name_en": "Mathematics"
        })
        # Second create with same name_en must not add a duplicate.
        client.post("/admin", data={
            "action": "add_major", "name_fa": "ریاضی دو", "name_en": "Mathematics"
        })
        assert Major.query.filter_by(key="mathematics").count() == 1

    def test_admin_deletes_major(self, client, create_user, create_major):
        login_admin(client, create_user)
        major = create_major(key="delete_me")
        client.post("/admin", data={"action": "delete_major", "major_id": major.id})
        assert db.session.get(Major, major.id) is None

    def test_admin_cannot_delete_protected_major(self, client, create_user):
        login_admin(client, create_user)
        major = Major(key="computer_science", name_fa="cs", name_en="Computer Science")
        db.session.add(major)
        db.session.commit()
        client.post("/admin", data={"action": "delete_major", "major_id": major.id})
        # computer_science is hardcoded as protected.
        assert db.session.get(Major, major.id) is not None


class TestCourseCrud:
    def test_admin_creates_course(self, client, create_user, create_major):
        login_admin(client, create_user)
        major = create_major()
        client.post("/admin", data={
            "action": "add_course", "major_key": major.key,
            "name_fa": "درس جدید", "name_en": "New Course"
        })
        assert Course.query.filter_by(key="new_course").first() is not None

    def test_admin_deletes_course_preserves_tasks(self, client, create_user, create_major):
        login_admin(client, create_user)
        admin = User.query.filter_by(role="site_admin").first()
        # Create a real course and a task attached to it.
        major = create_major()
        course = Course(key="doomed_course", name_fa="dc", name_en="Doomed Course", major_id=major.id)
        db.session.add(course)
        db.session.commit()
        task = Task(user_id=admin.id, course_id=course.id, course_key=course.key,
                    title="t", description="", priority="medium", hours=1,
                    estimated_hours=1, done=False, status="pending")
        db.session.add(task)
        db.session.commit()

        client.post("/admin", data={"action": "delete_course", "course_id": course.id})
        assert db.session.get(Course, course.id) is None
        fresh = db.session.get(Task, task.id)
        assert fresh is not None
        assert fresh.course_id is None  # preserved, unlinked

    def test_admin_deletes_unknown_course_noop(self, client, create_user):
        login_admin(client, create_user)
        # No exception for a missing/invalid course_id.
        client.post("/admin", data={"action": "delete_course", "course_id": 999999})
        assert Course.query.count() == 0
