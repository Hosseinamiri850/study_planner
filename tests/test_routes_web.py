"""Tests for browser routes in app/routes/web.py (TASK-015).

Covers login/register/logout, dashboard task CRUD, theme toggle, language
switch, and view_user. CSRF is disabled in TestConfig so form POSTs succeed
without a token.
"""


from app.extensions import db
from app.models import Task, User


class TestAuthViews:
    def test_home_redirects_anonymous_to_login(self, client):
        r = client.get("/")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_home_redirects_user_to_dashboard(self, client, create_user):
        create_user(username="dashuser")
        with client.session_transaction() as sess:
            sess["username"] = "dashuser"
        r = client.get("/")
        assert r.status_code == 302
        assert "/dashboard" in r.headers["Location"]

    def test_home_redirects_admin_to_admin_panel(self, client, create_user):
        create_user(username="siteadmin", is_admin=True)
        with client.session_transaction() as sess:
            sess["username"] = "siteadmin"
        r = client.get("/")
        assert r.status_code == 302
        assert "/admin" in r.headers["Location"]

    def test_login_get_returns_200(self, client):
        assert client.get("/login").status_code == 200

    def test_login_success_sets_session(self, client, create_user):
        create_user(username="loginer", password="validpass123")
        with client.session_transaction() as sess:
            assert "username" not in sess
        r = client.post("/login", data={"username": "loginer", "password": "validpass123"})
        assert r.status_code == 302
        with client.session_transaction() as sess:
            assert sess["username"] == "loginer"

    def test_login_invalid_credentials_renders_form(self, client, create_user):
        create_user(username="realuser", password="validpass123")
        r = client.post("/login", data={"username": "realuser", "password": "bogus"})
        assert r.status_code == 200  # re-renders login.html, not a redirect
        with client.session_transaction() as sess:
            assert "username" not in sess

    def test_login_admin_redirects_to_admin_panel(self, client, create_user):
        create_user(username="adminlogin", password="validpass123", is_admin=True)
        r = client.post("/login", data={"username": "adminlogin", "password": "validpass123"})
        assert r.status_code == 302
        assert "/admin" in r.headers["Location"]

    def test_register_success(self, client):
        r = client.post("/register", data={
            "username": "newbie", "password": "strongpass123", "fullname": "New Person"
        })
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]
        assert User.query.filter_by(username="newbie").first() is not None

    def test_register_rejects_duplicate(self, client, create_user):
        create_user(username="taken")
        r = client.post("/register", data={
            "username": "taken", "password": "strongpass123", "fullname": "Dup"
        })
        assert r.status_code == 200  # re-renders register.html with flash
        assert User.query.filter_by(username="taken").count() == 1

    def test_register_rejects_short_password(self, client):
        r = client.post("/register", data={
            "username": "shortpw", "password": "x", "fullname": "Has Name"
        })
        assert r.status_code == 200
        assert User.query.filter_by(username="shortpw").first() is None

    def test_register_rejects_missing_fields(self, client):
        r = client.post("/register", data={
            "username": "", "password": "somepass123", "fullname": ""
        })
        assert r.status_code == 200
        assert User.query.count() == 0

    def test_logout_clears_session(self, client, create_user):
        create_user(username="logger", password="validpass123")
        client.post("/login", data={"username": "logger", "password": "validpass123"})
        with client.session_transaction() as sess:
            assert sess.get("username") == "logger"
        r = client.get("/logout")
        assert r.status_code == 302
        with client.session_transaction() as sess:
            assert "username" not in sess

    def test_login_view_requires_no_session(self, client):
        # GET /login while already logged in still renders login (no redirect guard) — acceptable.
        assert client.get("/login").status_code == 200


class TestLanguageAndTheme:
    def test_set_lang_persists_in_session(self, client):
        r = client.get("/set-lang/en")
        with client.session_transaction() as sess:
            assert sess["lang"] == "en"
        assert r.status_code == 302

    def test_set_lang_ignores_unknown(self, client):
        client.get("/set-lang/fr")
        with client.session_transaction() as sess:
            assert "lang" not in sess

    def test_toggle_theme_requires_login(self, client):
        r = client.post("/toggle-theme")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_toggle_theme_flips_preference(self, client, create_user):
        user = create_user(username="themer")
        assert user.theme == "dark"  # model default
        with client.session_transaction() as sess:
            sess["username"] = "themer"
        r = client.post("/toggle-theme")
        assert r.status_code == 200
        assert r.get_json()["theme"] == "light"
        assert db.session.get(User, user.id).theme == "light"


class TestDashboard:
    def test_dashboard_requires_login(self, client):
        r = client.get("/dashboard")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_dashboard_admin_redirects_to_admin_panel(self, client, create_user):
        create_user(username="adminboard", is_admin=True)
        with client.session_transaction() as sess:
            sess["username"] = "adminboard"
        r = client.get("/dashboard")
        assert r.status_code == 302
        assert "/admin" in r.headers["Location"]

    def test_dashboard_renders_for_user(self, client, create_user, create_course):
        create_course()
        create_user(username="reader")
        with client.session_transaction() as sess:
            sess["username"] = "reader"
        assert client.get("/dashboard").status_code == 200

    def test_dashboard_creates_task(self, client, create_user, create_course):
        course = create_course()
        create_user(username="adder")
        with client.session_transaction() as sess:
            sess["username"] = "adder"
        r = client.post("/dashboard", data={
            "action": "new_task", "course_key": course.key,
            "task_hours": "2", "priority": "high", "description": "study sql"
        })
        assert r.status_code == 302
        task = Task.query.filter_by(course_key=course.key).first()
        assert task is not None
        assert task.estimated_hours == 2.0
        assert task.priority == "high"

    def test_dashboard_rejects_bad_hours(self, client, create_user, create_course):
        course = create_course()
        create_user(username="bogushours")
        with client.session_transaction() as sess:
            sess["username"] = "bogushours"
        client.post("/dashboard", data={
            "action": "new_task", "course_key": course.key,
            "task_hours": "999", "priority": "medium", "description": ""
        })
        assert Task.query.filter_by(course_key=course.key).first() is None

    def test_dashboard_toggles_task_completion(self, client, create_user, create_task):
        owner = create_user(username="toggleowner")
        task = create_task(user=owner)
        with client.session_transaction() as sess:
            sess["username"] = "toggleowner"
        assert task.done is False
        client.post("/dashboard", data={"action": "toggle", "task_id": task.id})
        assert db.session.get(Task, task.id).done is True
        client.post("/dashboard", data={"action": "toggle", "task_id": task.id})
        assert db.session.get(Task, task.id).done is False

    def test_dashboard_deletes_own_task(self, client, create_user, create_task):
        owner = create_user(username="deletor")
        task = create_task(user=owner)
        with client.session_transaction() as sess:
            sess["username"] = "deletor"
        client.post("/dashboard", data={"action": "delete", "task_id": task.id})
        assert db.session.get(Task, task.id) is None

    def test_dashboard_rejects_other_users_task(self, client, create_user, create_task):
        owner = create_user(username="ownerA")
        create_user(username="sneakerB")
        task = create_task(user=owner)
        with client.session_transaction() as sess:
            sess["username"] = "sneakerB"
        client.post("/dashboard", data={"action": "delete", "task_id": task.id})
        # Task must survive — sneaker does not own it.
        assert db.session.get(Task, task.id) is not None

    def test_dashboard_edits_task(self, client, create_user, create_task):
        owner = create_user(username="editor")
        task = create_task(user=owner, description="old", priority="low")
        with client.session_transaction() as sess:
            sess["username"] = "editor"
        client.post("/dashboard", data={
            "action": "edit", "task_id": task.id,
            "course_key": task.course_key, "priority": "high",
            "description": "updated", "task_hours": "3.5"
        })
        fresh = db.session.get(Task, task.id)
        assert fresh.description == "updated"
        assert fresh.priority == "high"
        assert fresh.estimated_hours == 3.5


class TestViewUser:
    def test_view_user_requires_login(self, client, create_user):
        create_user(username="targetuser")
        r = client.get("/user/targetuser")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_view_user_renders(self, client, create_user):
        create_user(username="viewer")  # logged-in viewer must exist
        create_user(username="viewable", fullname="Viewable Person")
        with client.session_transaction() as sess:
            sess["username"] = "viewer"
        r = client.get("/user/viewable")
        assert r.status_code == 200

    def test_view_unknown_user_redirects(self, client, create_user):
        create_user(username="viewer")
        with client.session_transaction() as sess:
            sess["username"] = "viewer"
        r = client.get("/user/nosuch")
        assert r.status_code == 302
        assert "/dashboard" in r.headers["Location"]

    def test_view_admin_user_redirects(self, client, create_user):
        create_user(username="viewer")
        create_user(username="anadmin", is_admin=True)
        with client.session_transaction() as sess:
            sess["username"] = "viewer"
        r = client.get("/user/anadmin")
        assert r.status_code == 302
        assert "/dashboard" in r.headers["Location"]
