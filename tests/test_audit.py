"""Tests for the audit trail (TASK-035): model defaults, the record()
service contract (never breaks the mutation, actor may be None,
institution denormalized from the actor), and the endpoint wiring in
app/routes/api.py and app/routes/admin.py."""

from app.extensions import db
from app.models import AuditLog, User
from app.services.audit import record


def _logs_for(action=None):
    query = AuditLog.query.order_by(AuditLog.id)
    if action:
        query = query.filter_by(action=action)
    return query.all()


class TestAuditService:
    def test_record_writes_row(self, create_user):
        user = create_user(username="auditor")
        row = record(user, "task.create", ("task", 42), after={"title": "T"})
        assert row is not None
        assert row.actor_user_id == user.id
        assert row.action == "task.create"
        assert row.target_type == "task"
        assert row.target_id == 42
        assert row.before is None
        assert row.after == {"title": "T"}
        assert row.created_at is not None

    def test_record_with_system_actor(self, app):
        row = record(None, "system.seed", ("major", None), after={"key": "computer_science"})
        assert row.actor_user_id is None
        assert row.institution_id is None
        assert row.target_id is None

    def test_institution_denormalized_from_actor(self, create_user, create_institution):
        institution = create_institution(name="Tenant School")
        user = create_user(username="tenanted")
        user.institution_id = institution.id
        db.session.commit()
        row = record(user, "task.update", ("task", 1))
        assert row.institution_id == institution.id

    def test_record_never_breaks_caller_on_bad_target(self, create_user):
        """A malformed target tuple is logged and swallowed — record()
        returns None but does not raise."""
        user = create_user(username="resilient")
        assert record(user, "weird.action", "not-a-tuple") is None
        assert _logs_for("weird.action") == []

    def test_record_outside_app_context_is_dropped(self):
        assert record(None, "system.noop", ("task", 1)) is None

    def test_record_commit_visible_after_return(self, create_user):
        user = create_user(username="committed")
        record(user, "course.create", ("course", 7), after={"key": "math"})
        fetched = AuditLog.query.filter_by(action="course.create").first()
        assert fetched is not None and fetched.target_id == 7


class TestApiTaskAudit:
    def test_task_create_audited(self, auth_client, create_course):
        client, user = auth_client
        course = create_course()
        client.post("/api/tasks", json={"course_id": course.id, "title": "Read", "estimated_hours": 1})
        rows = _logs_for("task.create")
        assert len(rows) == 1
        assert rows[0].actor_user_id == user.id
        assert rows[0].after["title"] == "Read"
        assert rows[0].before is None

    def test_task_update_audited_with_before_after(self, auth_client, create_course):
        client, user = auth_client
        course = create_course()
        task = client.post("/api/tasks", json={"course_id": course.id, "title": "Before", "estimated_hours": 1}).get_json()["task"]
        client.put(f"/api/tasks/{task['id']}", json={"title": "After", "status": "completed"})
        row = _logs_for("task.update")[0]
        assert row.before["title"] == "Before" and row.before["status"] == "pending"
        assert row.after["title"] == "After" and row.after["status"] == "completed"
        assert row.target_id == task["id"]

    def test_task_delete_audited_with_before(self, auth_client, create_course):
        client, user = auth_client
        course = create_course()
        task = client.post("/api/tasks", json={"course_id": course.id, "title": "Doomed", "estimated_hours": 1}).get_json()["task"]
        client.delete(f"/api/tasks/{task['id']}")
        row = _logs_for("task.delete")[0]
        assert row.before["title"] == "Doomed"
        assert row.after is None
        assert row.target_id == task["id"]

    def test_other_users_task_not_audited_on_404(self, auth_client, create_user, create_course, create_task):
        client, _ = auth_client
        owner = create_user(username="owner")
        course = create_course()
        task = create_task(user=owner, course=course)
        client.delete(f"/api/tasks/{task.id}")  # 404 — someone else's task
        assert _logs_for("task.delete") == []


class TestApiCatalogAudit:
    def test_course_create_update_delete_audited(self, app, client, create_user, create_major):
        create_user(username="catadmin", is_admin=True)
        with client.session_transaction() as sess:
            sess["username"] = "catadmin"
        from app.utils.auth import create_access_token
        user = User.query.filter_by(username="catadmin").first()
        headers = {"Authorization": f"Bearer {create_access_token(user)}"}
        major = create_major()

        course = client.post("/api/courses", json={"name_fa": "درس", "name_en": "Lesson", "major_id": major.id}, headers=headers).get_json()["course"]
        client.put(f"/api/courses/{course['id']}", json={"name_en": "Renamed"}, headers=headers)
        client.delete(f"/api/courses/{course['id']}", headers=headers)

        created = _logs_for("course.create")[0]
        assert created.after["name_en"] == "Lesson"
        updated = _logs_for("course.update")[0]
        assert updated.before["name_en"] == "Lesson" and updated.after["name_en"] == "Renamed"
        deleted = _logs_for("course.delete")[0]
        assert deleted.before["name_en"] == "Renamed" and deleted.after is None

    def test_major_create_update_delete_audited(self, app, client, create_user):
        create_user(username="majadmin", is_admin=True)
        with client.session_transaction() as sess:
            sess["username"] = "majadmin"
        from app.utils.auth import create_access_token
        user = User.query.filter_by(username="majadmin").first()
        headers = {"Authorization": f"Bearer {create_access_token(user)}"}

        major = client.post("/api/majors", json={"name_fa": "ریاضی", "name_en": "Math"}, headers=headers).get_json()["major"]
        client.put(f"/api/majors/{major['id']}", json={"name_en": "Mathematics"}, headers=headers)
        client.delete(f"/api/majors/{major['id']}", headers=headers)

        assert _logs_for("major.create")[0].after["name_en"] == "Math"
        updated = _logs_for("major.update")[0]
        assert updated.before["name_en"] == "Math" and updated.after["name_en"] == "Mathematics"
        assert _logs_for("major.delete")[0].before["name_en"] == "Mathematics"


class TestAdminAudit:
    def test_delete_user_audited(self, client, create_user):
        create_user(username="superadmin", password="validpass123", is_admin=True)
        create_user(username="victim", password="validpass123")
        with client.session_transaction() as sess:
            sess["username"] = "superadmin"
        client.post("/admin", data={"action": "delete_user", "username": "victim"})
        row = _logs_for("user.delete")[0]
        assert row.before == {"username": "victim"}
        actor = User.query.filter_by(username="superadmin").first()
        assert row.actor_user_id == actor.id

    def test_admin_delete_user_not_audited_when_blocked(self, client, create_user):
        create_user(username="superadmin", password="validpass123", is_admin=True)
        create_user(username="safeadmin", password="validpass123", is_admin=True)
        with client.session_transaction() as sess:
            sess["username"] = "superadmin"
        client.post("/admin", data={"action": "delete_user", "username": "safeadmin"})
        assert _logs_for("user.delete") == []

    def test_password_change_audited_without_hash(self, client, create_user):
        create_user(username="superadmin", password="validpass123", is_admin=True)
        create_user(username="target", password="validpass123")
        with client.session_transaction() as sess:
            sess["username"] = "superadmin"
        client.post("/admin", data={"action": "change_password", "username": "target", "new_password": "newpass123"})
        row = _logs_for("user.password_change")[0]
        # The hash must never land in the audit trail.
        assert row.before is None and row.after is None
        target = User.query.filter_by(username="target").first()
        assert row.target_id == target.id

    def test_delete_major_and_course_audited(self, client, create_user, create_major, create_course):
        create_user(username="superadmin", password="validpass123", is_admin=True)
        with client.session_transaction() as sess:
            sess["username"] = "superadmin"
        major = create_major(key="doomed_major", name_en="Doomed Major")
        course = create_course(key="doomed_course", name_en="Doomed Course", major=major)
        client.post("/admin", data={"action": "delete_course", "course_id": course.id})
        client.post("/admin", data={"action": "delete_major", "major_id": major.id})
        assert _logs_for("course.delete")[0].before["key"] == "doomed_course"
        assert _logs_for("major.delete")[0].before["key"] == "doomed_major"

    def test_default_major_delete_not_audited(self, client, create_user, create_major):
        create_user(username="superadmin", password="validpass123", is_admin=True)
        with client.session_transaction() as sess:
            sess["username"] = "superadmin"
        client.post("/admin", data={"action": "delete_major", "major_id": 1})
        assert _logs_for("major.delete") == []


class TestAuditQueryShape:
    def test_model_repr_and_columns(self, create_user):
        user = create_user(username="shape")
        row = record(user, "x.y", ("t", 1), before={"a": 1}, after={"a": 2})
        fetched = db.session.get(AuditLog, row.id)
        assert fetched.target_type == "t"
        assert fetched.before == {"a": 1} and fetched.after == {"a": 2}
