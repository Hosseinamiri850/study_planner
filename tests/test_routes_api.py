

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
