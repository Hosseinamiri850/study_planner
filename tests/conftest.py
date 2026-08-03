import sys
import uuid
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from app import create_app
from app.extensions import db
from app.models import User, Course, Major, Task, StudySession
from werkzeug.security import generate_password_hash


class TestConfig:
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = True
    RATELIMIT_ENABLED = False


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def create_user(app):
    counter = {"n": 0}
    def _create_user(username=None, password="testpass123", fullname="Test User", is_admin=False):
        counter["n"] += 1
        if username is None:
            username = f"user_{counter['n']}_{uuid.uuid4().hex[:6]}"
        user = User(
            username=username,
            password=generate_password_hash(password),
            fullname=fullname,
            is_admin=is_admin,
        )
        db.session.add(user)
        db.session.commit()
        return user
    return _create_user


@pytest.fixture
def create_major(app):
    counter = {"n": 0}
    def _create_major(key=None, name_fa="رشته تست", name_en="Test Major"):
        counter["n"] += 1
        if key is None:
            key = f"test_major_{counter['n']}_{uuid.uuid4().hex[:6]}"
        major = Major(key=key, name_fa=name_fa, name_en=name_en)
        db.session.add(major)
        db.session.commit()
        return major
    return _create_major


@pytest.fixture
def create_course(app, create_major):
    counter = {"n": 0}
    def _create_course(key=None, name_fa="درس تست", name_en="Test Course", major=None):
        counter["n"] += 1
        if major is None:
            major = create_major()
        if key is None:
            key = f"test_course_{counter['n']}_{uuid.uuid4().hex[:6]}"
        course = Course(key=key, name_fa=name_fa, name_en=name_en, major_id=major.id)
        db.session.add(course)
        db.session.commit()
        return course
    return _create_course


@pytest.fixture
def create_task(app, create_user, create_course):
    def _create_task(user=None, course=None, title="Test Task", description="", priority="medium", hours=1.0, done=False, status="pending", created_at=None):
        if user is None:
            user = create_user()
        if course is None:
            course = create_course()
        task = Task(
            user_id=user.id,
            course_id=course.id,
            course_key=course.key,
            title=title,
            description=description,
            priority=priority,
            hours=hours,
            done=done,
            status=status,
            created_at=created_at or date.today(),
        )
        db.session.add(task)
        db.session.commit()
        return task
    return _create_task


@pytest.fixture
def create_study_session(app, create_task):
    def _create_study_session(task=None, duration=60, started_at=None, ended_at=None):
        if task is None:
            task = create_task()
        session = StudySession(
            task_id=task.id,
            duration=duration,
            started_at=started_at,
            ended_at=ended_at,
        )
        db.session.add(session)
        db.session.commit()
        return session
    return _create_study_session


@pytest.fixture
def auth_client(client, create_user):
    user = create_user(username="authuser", password="testpass123")
    response = client.post("/api/auth/login", json={"username": user.username, "password": "testpass123"})
    assert response.status_code == 200, f"Login failed: {response.get_json()}"
    token = response.get_json()["access_token"]
    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client, user
