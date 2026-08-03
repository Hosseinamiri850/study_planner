"""Tests for rate limiting on auth endpoints (TASK-014).

Uses a dedicated app config that re-enables Flask-Limiter, which the main
TestConfig disables so the rest of the suite isn't throttled.
"""

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import User


class RateLimitConfig:
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    RATELIMIT_ENABLED = True
    # Keep the same 5/min auth limit as production, but a tiny window so the
    # sixth-in-a-row attempt trips it deterministically without waiting.
    RATELIMIT_AUTH = "5 per minute"
    RATELIMIT_STORAGE_URI = "memory://"


@pytest.fixture
def rl_app():
    app = create_app(RateLimitConfig)
    with app.app_context():
        db.create_all()
        db.session.add(User(username="lockeduser",
                            password=generate_password_hash("validpass123"),
                            fullname="Locked User"))
        db.session.commit()
        yield app
        db.drop_all()


@pytest.fixture
def rl_client(rl_app):
    return rl_app.test_client()


class TestAuthRateLimit:
    """5 auth POSTs per minute per IP → 6th is 429."""

    def test_api_login_throttles_after_limit(self, rl_client):
        creds = {"username": "lockeduser", "password": "boguspass"}
        for _ in range(5):
            r = rl_client.post("/api/auth/login", json=creds)
            assert r.status_code == 401  # wrong password, allowed
        sixth = rl_client.post("/api/auth/login", json=creds)
        assert sixth.status_code == 429

    def test_api_register_throttles_after_limit(self, rl_client):
        for _ in range(5):
            r = rl_client.post("/api/auth/register", json={
                "username": "u", "password": "weak", "fullname": ""
            })
            assert r.status_code == 400  # invalid input, allowed
        sixth = rl_client.post("/api/auth/register", json={
            "username": "u", "password": "weak", "fullname": ""
        })
        assert sixth.status_code == 429

    def test_non_auth_endpoint_not_limited(self, rl_client, rl_app, monkeypatch):
        # Non-auth GET requests must not share the auth limiter; stub the
        # translator check so no real network call is made.
        import app.routes.api as api_mod
        monkeypatch.setattr(api_mod, "translator_available", lambda: False)
        for _ in range(8):
            r = rl_client.get("/api/translator-status")
            assert r.status_code == 200
