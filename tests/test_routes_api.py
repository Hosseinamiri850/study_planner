

from app.extensions import db


class TestAuthAPI:
    def test_register_success(self, client):
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "password": "securepass123",
            "fullname": "New User"
        })
        assert response.status_code == 201
        data = response.get_json()
        assert "user" in data
        assert "access_token" in data
        assert data["user"]["username"] == "newuser"
        assert data["user"]["fullname"] == "New User"

    def test_register_duplicate_username(self, client, create_user):
        create_user(username="existing")
        response = client.post("/api/auth/register", json={
            "username": "existing",
            "password": "securepass123",
            "fullname": "Existing"
        })
        assert response.status_code == 409
        data = response.get_json()
        assert "error" in data

    def test_register_invalid_input(self, client):
        response = client.post("/api/auth/register", json={
            "username": "ab",
            "password": "short",
            "fullname": ""
        })
        assert response.status_code == 400

    def test_login_success(self, client, create_user):
        create_user(username="loginuser", password="mypassword")
        response = client.post("/api/auth/login", json={
            "username": "loginuser",
            "password": "mypassword"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "access_token" in data
        assert data["user"]["username"] == "loginuser"

    def test_login_invalid_credentials(self, client):
        response = client.post("/api/auth/login", json={
            "username": "nouser",
            "password": "wrongpass"
        })
        assert response.status_code == 401


class TestTasksAPI:
    def test_list_tasks_requires_auth(self, client):
        response = client.get("/api/tasks")
        assert response.status_code == 401

    def test_list_tasks_empty(self, auth_client):
        client, user = auth_client
        response = client.get("/api/tasks")
        assert response.status_code == 200
        data = response.get_json()
        assert "tasks" in data
        assert len(data["tasks"]) == 0

    def test_list_tasks_returns_all_without_params(self, auth_client, create_task):
        client, user = auth_client
        for _ in range(3):
            create_task(user=user)
        data = client.get("/api/tasks").get_json()
        assert len(data["tasks"]) == 3
        # Legacy shape: no pagination envelope.
        assert "total" not in data

    def test_list_tasks_paginates_with_params(self, auth_client, create_task):
        client, user = auth_client
        for _ in range(5):
            create_task(user=user)
        data = client.get("/api/tasks?page=1&per_page=2").get_json()
        assert len(data["tasks"]) == 2
        assert data["total"] == 5
        assert data["pages"] == 3

    def test_list_tasks_clamps_per_page_to_100(self, auth_client, create_task):
        client, user = auth_client
        for _ in range(2):
            create_task(user=user)
        data = client.get("/api/tasks?page=1&per_page=9999").get_json()
        assert data["per_page"] == 100
        assert len(data["tasks"]) == 2

    def test_list_tasks_rejects_page_without_per_page(self, auth_client):
        client, user = auth_client
        response = client.get("/api/tasks?page=1")
        assert response.status_code == 400

    def test_list_tasks_rejects_per_page_without_page(self, auth_client):
        client, user = auth_client
        response = client.get("/api/tasks?per_page=10")
        assert response.status_code == 400

    def test_list_tasks_rejects_page_below_one(self, auth_client):
        client, user = auth_client
        response = client.get("/api/tasks?page=0&per_page=10")
        assert response.status_code == 400

    def test_list_tasks_rejects_per_page_below_one(self, auth_client):
        client, user = auth_client
        response = client.get("/api/tasks?page=1&per_page=0")
        assert response.status_code == 400

    def test_create_task_success(self, auth_client, create_course):
        client, user = auth_client
        course = create_course(key="test_course_api", name_fa="تست API", name_en="Test API")
        response = client.post("/api/tasks", json={
            "course_id": course.id,
            "title": "API Task",
            "description": "Test description",
            "priority": "high",
            "estimated_hours": 3.0
        })
        assert response.status_code == 201
        data = response.get_json()
        assert "task" in data
        assert data["task"]["title"] == "API Task"
        assert data["task"]["priority"] == "high"

    def test_create_task_requires_auth(self, client):
        response = client.post("/api/tasks", json={})
        assert response.status_code == 401

    def test_update_task(self, auth_client, create_task):
        client, user = auth_client
        task = create_task(user=user, title="Original")
        response = client.put(f"/api/tasks/{task.id}", json={
            "title": "Updated",
            "status": "completed"
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["task"]["title"] == "Updated"
        assert data["task"]["status"] == "completed"

    def test_update_task_not_found(self, auth_client):
        client, user = auth_client
        response = client.put("/api/tasks/99999", json={"title": "Updated"})
        assert response.status_code == 404

    def test_update_other_user_task(self, auth_client, create_user, create_task):
        client, user = auth_client
        other_user = create_user(username="other_api", password="pass123")
        other_task = create_task(user=other_user)
        response = client.put(f"/api/tasks/{other_task.id}", json={"title": "Hacked"})
        assert response.status_code == 404

    def test_delete_task(self, auth_client, create_task):
        client, user = auth_client
        task = create_task(user=user)
        response = client.delete(f"/api/tasks/{task.id}")
        assert response.status_code == 204

    def test_delete_other_user_task(self, auth_client, create_user, create_task):
        client, user = auth_client
        other_user = create_user(username="other_del_api", password="pass123")
        other_task = create_task(user=other_user)
        response = client.delete(f"/api/tasks/{other_task.id}")
        assert response.status_code == 404


class TestStatisticsAPI:
    def test_dashboard_stats_requires_auth(self, client):
        response = client.get("/api/statistics/dashboard")
        assert response.status_code == 401

    def test_dashboard_stats_empty(self, auth_client):
        client, user = auth_client
        response = client.get("/api/statistics/dashboard")
        assert response.status_code == 200
        data = response.get_json()
        assert "total_tasks" in data
        assert "today_hours" in data
        assert "week_hours" in data
        assert "month_hours" in data
        assert data["total_tasks"] == 0
        assert data["today_hours"] == 0

    def test_dashboard_stats_with_tasks(self, auth_client, create_task):
        client, user = auth_client
        create_task(user=user, done=True, hours=2.0)
        create_task(user=user, done=True, hours=1.5)
        response = client.get("/api/statistics/dashboard")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total_tasks"] == 2
        assert data["total_done"] == 2


class TestTranslateAPI:
    def test_translator_status(self, client):
        response = client.get("/api/translator-status")
        assert response.status_code == 200
        data = response.get_json()
        assert "available" in data
        assert isinstance(data["available"], bool)

    def test_translate_requires_auth(self, client):
        response = client.post("/api/translate", json={"text": "test"})
        assert response.status_code in (302, 400, 401)


class TestSessionsAPI:
    def test_start_session_success(self, auth_client, create_task):
        client, user = auth_client
        task = create_task(user=user)
        response = client.post(f"/api/tasks/{task.id}/sessions")
        assert response.status_code == 201
        data = response.get_json()
        assert data["session"]["is_open"] is True
        assert data["session"]["task_id"] == task.id
        assert data["session"]["duration"] is None  # open → unknown duration

    def test_start_session_rejects_duplicate_open(self, auth_client, create_task):
        client, user = auth_client
        task = create_task(user=user)
        client.post(f"/api/tasks/{task.id}/sessions")
        r = client.post(f"/api/tasks/{task.id}/sessions")
        assert r.status_code == 409

    def test_start_session_unknown_task(self, auth_client):
        client, user = auth_client
        r = client.post("/api/tasks/99999/sessions")
        assert r.status_code == 404

    def test_start_session_other_user_task(self, auth_client, create_user, create_task):
        client, user = auth_client
        other = create_user(username="other_session", password="pass123")
        task = create_task(user=other)
        r = client.post(f"/api/tasks/{task.id}/sessions")
        assert r.status_code == 404  # not the caller's task

    def test_stop_session_sets_duration(self, auth_client, create_task):
        client, user = auth_client
        task = create_task(user=user)
        start = client.post(f"/api/tasks/{task.id}/sessions").get_json()["session"]
        r = client.post(f"/api/tasks/{task.id}/sessions/{start['id']}/stop")
        assert r.status_code == 200
        data = r.get_json()["session"]
        assert data["is_open"] is False
        assert data["ended_at"] is not None
        assert data["duration"] is not None and data["duration"] >= 0

    def test_stop_session_idempotent(self, auth_client, create_task):
        client, user = auth_client
        task = create_task(user=user)
        start = client.post(f"/api/tasks/{task.id}/sessions").get_json()["session"]
        first = client.post(f"/api/tasks/{task.id}/sessions/{start['id']}/stop")
        assert first.status_code == 200
        second = client.post(f"/api/tasks/{task.id}/sessions/{start['id']}/stop")
        assert second.status_code == 200
        assert second.get_json()["session"]["duration"] == first.get_json()["session"]["duration"]

    def test_stop_unknown_session(self, auth_client, create_task):
        client, user = auth_client
        task = create_task(user=user)
        r = client.post(f"/api/tasks/{task.id}/sessions/99999/stop")
        assert r.status_code == 404

    def test_list_sessions(self, auth_client, create_task):
        client, user = auth_client
        task = create_task(user=user)
        s1 = client.post(f"/api/tasks/{task.id}/sessions").get_json()["session"]
        client.post(f"/api/tasks/{task.id}/sessions/{s1['id']}/stop")
        client.post(f"/api/tasks/{task.id}/sessions")
        data = client.get(f"/api/tasks/{task.id}/sessions").get_json()
        assert len(data["sessions"]) == 2
        assert data["sessions"][0]["is_open"] is True  # desc order → newest first


class TestRefreshTokens:
    def test_login_returns_refresh_token(self, client, create_user):
        create_user(username="rtuser", password="testpass123")
        response = client.post("/api/auth/login", json={"username": "rtuser", "password": "testpass123"})
        data = response.get_json()
        assert "refresh_token" in data and data["refresh_token"]

    def test_register_returns_refresh_token(self, client):
        response = client.post("/api/auth/register", json={
            "username": "rtreg", "password": "securepass123", "fullname": "RT Reg",
        })
        assert "refresh_token" in response.get_json()

    def test_refresh_issues_new_pair(self, client, login_tokens):
        user, access, refresh = login_tokens
        response = client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert response.status_code == 200
        new = response.get_json()
        assert "access_token" in new and "refresh_token" in new

    def test_refresh_rotates_old_token(self, client, login_tokens):
        user, access, refresh = login_tokens
        client.post("/api/auth/refresh", json={"refresh_token": refresh})
        replay = client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert replay.status_code == 401  # old token revoked by rotation

    def test_refresh_rejects_missing_token(self, client):
        assert client.post("/api/auth/refresh", json={}).status_code == 400

    def test_refresh_rejects_garbage(self, client):
        assert client.post("/api/auth/refresh", json={"refresh_token": "not-a-token"}).status_code == 401

    def test_refresh_rejects_revoked_after_password_change(self, client, login_tokens):
        user, access, refresh = login_tokens
        from werkzeug.security import generate_password_hash

        from app.models.refresh_token import revoke_user_refresh_tokens
        user.password = generate_password_hash("newpass123")
        revoke_user_refresh_tokens(user.id)
        db.session.commit()
        assert client.post("/api/auth/refresh", json={"refresh_token": refresh}).status_code == 401


class TestMeAPI:
    def test_me_requires_auth(self, client):
        assert client.get("/api/me").status_code == 401

    def test_me_returns_profile(self, auth_client):
        client, user = auth_client
        response = client.get("/api/me")
        assert response.status_code == 200
        data = response.get_json()["user"]
        assert data["id"] == user.id
        assert data["username"] == user.username
        assert data["fullname"] == user.fullname
        assert data["is_admin"] is False
        assert data["theme"] in {"dark", "light"}

    def test_me_rejects_garbage_token(self, client):
        client.environ_base["HTTP_AUTHORIZATION"] = "Bearer garbage"
        assert client.get("/api/me").status_code == 401

    def test_update_me_fullname_and_theme(self, auth_client):
        client, user = auth_client
        response = client.put("/api/me", json={"fullname": "Renamed User", "theme": "light"})
        assert response.status_code == 200
        data = response.get_json()["user"]
        assert data["fullname"] == "Renamed User"
        assert data["theme"] == "light"
        assert user.fullname == "Renamed User"

    def test_update_me_rejects_bad_theme(self, auth_client):
        client, _ = auth_client
        assert client.put("/api/me", json={"theme": "purple"}).status_code == 400

    def test_update_me_rejects_empty_fullname(self, auth_client):
        client, _ = auth_client
        assert client.put("/api/me", json={"fullname": "   "}).status_code == 400

    def test_update_me_password_change(self, auth_client):
        client, user = auth_client
        response = client.put("/api/me", json={"current_password": "testpass123", "password": "brandnewpass1"})
        assert response.status_code == 200
        from werkzeug.security import check_password_hash
        assert check_password_hash(user.password, "brandnewpass1")

    def test_update_me_password_wrong_current(self, auth_client):
        client, _ = auth_client
        response = client.put("/api/me", json={"current_password": "wrongpass", "password": "brandnewpass1"})
        assert response.status_code == 403

    def test_update_me_password_too_short(self, auth_client):
        client, _ = auth_client
        assert client.put("/api/me", json={"current_password": "testpass123", "password": "short"}).status_code == 400

    def test_update_me_password_revokes_refresh(self, client, login_tokens):
        user, access, refresh = login_tokens
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {access}"
        assert client.put("/api/me", json={"current_password": "testpass123", "password": "brandnewpass1"}).status_code == 200
        client.environ_base.pop("HTTP_AUTHORIZATION", None)
        # Old refresh token no longer mints access tokens.
        assert client.post("/api/auth/refresh", json={"refresh_token": refresh}).status_code == 401


class TestLogoutAPI:
    def test_logout_requires_auth(self, client):
        assert client.post("/api/auth/logout", json={}).status_code == 401

    def test_logout_revokes_refresh(self, client, login_tokens):
        user, access, refresh = login_tokens
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {access}"
        assert client.post("/api/auth/logout", json={"refresh_token": refresh}).status_code == 204
        client.environ_base.pop("HTTP_AUTHORIZATION", None)
        # Revoked refresh token cannot mint new access tokens.
        assert client.post("/api/auth/refresh", json={"refresh_token": refresh}).status_code == 401

    def test_logout_without_refresh_token_still_204(self, client, login_tokens):
        user, access, _ = login_tokens
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {access}"
        assert client.post("/api/auth/logout", json={}).status_code == 204

    def test_logout_garbage_token_safe(self, client, login_tokens):
        user, access, _ = login_tokens
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {access}"
        assert client.post("/api/auth/logout", json={"refresh_token": "garbage"}).status_code == 204

    def test_logout_other_users_token_ignored(self, client, create_user, login_tokens):
        """A user cannot revoke someone else's refresh token via logout."""
        other = create_user(username="otheruser")
        from app.utils.auth import issue_refresh_token
        other_token = issue_refresh_token(other)
        user, access, _ = login_tokens
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {access}"
        assert client.post("/api/auth/logout", json={"refresh_token": other_token}).status_code == 204
        client.environ_base.pop("HTTP_AUTHORIZATION", None)
        # Other user's token still valid.
        assert client.post("/api/auth/refresh", json={"refresh_token": other_token}).status_code == 200


def _login_admin(client):
    """Create + promote + log in an admin; return the bearer token."""
    created = client.post(
        "/api/auth/register",
        json={"username": "adminuser", "password": "testpass123", "fullname": "Admin"},
    ).get_json()
    from app.extensions import db
    from app.models import User
    user = db.session.get(User, created["user"]["id"])
    user.is_admin = True
    db.session.commit()
    login = client.post("/api/auth/login", json={"username": "adminuser", "password": "testpass123"})
    return login.get_json()["access_token"]


class TestCoursesMajorsAPI:
    def test_courses_requires_auth(self, client):
        assert client.get("/api/courses").status_code == 401

    def test_majors_requires_auth(self, client):
        assert client.get("/api/majors").status_code == 401

    def test_list_courses(self, auth_client, create_course):
        course = create_course()
        client = auth_client[0]
        response = client.get("/api/courses")
        assert response.status_code == 200
        courses = response.get_json()["courses"]
        assert any(c["id"] == course.id and c["key"] == course.key for c in courses)
        assert all("name_fa" in c and "name_en" in c for c in courses)

    def test_list_majors_nested_courses(self, auth_client, create_course):
        course = create_course()
        client = auth_client[0]
        response = client.get("/api/majors")
        assert response.status_code == 200
        majors = response.get_json()["majors"]
        target = next(m for m in majors if m["id"] == course.major.id)
        assert any(c["id"] == course.id for c in target["courses"])

    def test_create_course_admin_only(self, auth_client, create_major):
        client, _ = auth_client
        major = create_major()
        response = client.post("/api/courses", json={"name_fa": "dars", "name_en": "Lesson", "major_id": major.id})
        assert response.status_code == 403

    def test_create_course_admin_success(self, client, create_major):
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {_login_admin(client)}"
        major = create_major()
        response = client.post("/api/courses", json={"name_fa": "dars", "name_en": "Lesson", "major_id": major.id})
        assert response.status_code == 201
        assert response.get_json()["course"]["key"] == "lesson"

    def test_create_course_duplicate_key_409(self, client, create_major):
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {_login_admin(client)}"
        major = create_major()
        client.post("/api/courses", json={"name_fa": "dars", "name_en": "Lesson", "major_id": major.id})
        dup = client.post("/api/courses", json={"name_fa": "dars2", "name_en": "Lesson", "major_id": major.id})
        assert dup.status_code == 409

    def test_create_course_missing_fields(self, client, create_major):
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {_login_admin(client)}"
        major = create_major()
        assert client.post("/api/courses", json={"name_en": "Only English", "major_id": major.id}).status_code == 400
        assert client.post("/api/courses", json={"name_fa": "farsi", "name_en": "No Major"}).status_code == 400

    def test_update_course(self, client, create_course):
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {_login_admin(client)}"
        course = create_course()
        response = client.put(f"/api/courses/{course.id}", json={"name_en": "Renamed"})
        assert response.status_code == 200
        assert response.get_json()["course"]["name_en"] == "Renamed"

    def test_update_course_not_found(self, client):
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {_login_admin(client)}"
        assert client.put("/api/courses/99999", json={"name_en": "X"}).status_code == 404

    def test_delete_course_preserves_tasks(self, client, create_course, create_task):
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {_login_admin(client)}"
        course = create_course()
        task = create_task(course=course)
        assert client.delete(f"/api/courses/{course.id}").status_code == 204
        from app.repositories import TaskRepo
        assert TaskRepo.get(task.id) is not None  # task row survives
        assert TaskRepo.get(task.id).course_id is None  # FK nulled

    def test_create_major_admin_success_and_duplicate(self, client):
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {_login_admin(client)}"
        first = client.post("/api/majors", json={"name_fa": "reshte", "name_en": "Field"})
        assert first.status_code == 201
        dup = client.post("/api/majors", json={"name_fa": "reshte", "name_en": "Field"})
        assert dup.status_code == 409

    def test_delete_major_protects_default(self, client, create_major):
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {_login_admin(client)}"
        protected = create_major(key="computer_science")
        normal = create_major()
        assert client.delete(f"/api/majors/{protected.id}").status_code == 409
        assert client.delete(f"/api/majors/{normal.id}").status_code == 204
        assert client.delete(f"/api/majors/{normal.id}").status_code == 404


class TestTaskOpenSessionPayload:
    def test_list_tasks_includes_open_session_id(self, auth_client, create_task, create_study_session):
        """Release-QA regression: the SPA needs the open-session id in the
        task payload to restore the running timer after a page reload."""
        client, user = auth_client
        task = create_task(user=user)
        session = create_study_session(task=task, duration=None, started_at=None, ended_at=None)
        data = client.get("/api/tasks").get_json()
        row = next(t for t in data["tasks"] if t["id"] == task.id)
        assert row["open_session_id"] == session.id

    def test_list_tasks_open_session_id_null_when_closed(self, auth_client, create_task, create_study_session):
        client, user = auth_client
        task = create_task(user=user)
        closed = create_study_session(task=task, duration=60, started_at=None, ended_at=None)
        closed.ended_at = closed.started_at  # close it
        from app.extensions import db as _db
        _db.session.commit()
        data = client.get("/api/tasks").get_json()
        row = next(t for t in data["tasks"] if t["id"] == task.id)
        assert row["open_session_id"] is None

    def test_open_session_id_scoped_to_owner(self, auth_client, create_user, create_task, create_study_session):
        """Another user's open session must not leak into this user's payload."""
        client, _ = auth_client
        other = create_user(username="other_sess_user")
        other_task = create_task(user=other)
        create_study_session(task=other_task, duration=None, started_at=None, ended_at=None)
        data = client.get("/api/tasks").get_json()
        assert all(t["open_session_id"] is None for t in data["tasks"])
