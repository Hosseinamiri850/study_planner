

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
