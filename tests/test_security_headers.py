"""Tests for security headers + session-cookie hardening (TASK-029)."""

import pytest

from app import create_app
from app.extensions import db


class TestSecurityHeaders:
    def test_headers_on_html_response(self, client):
        response = client.get("/login")
        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        hsts = response.headers["Strict-Transport-Security"]
        assert "max-age=31536000" in hsts and "includeSubDomains" in hsts

    def test_csp_allows_bootstrap_and_inline(self, hardened_app):
        response = hardened_app.test_client().get("/login")
        assert response.status_code == 200
        csp = response.headers["Content-Security-Policy"]
        # CDN assets the templates load today...
        assert "https://cdn.jsdelivr.net" in csp
        # ...and the inline handlers/scripts still in use until the UI migration.
        assert "'unsafe-inline'" in csp
        assert "default-src 'self'" in csp

    def test_headers_on_api_json_response(self, auth_client):
        client, _user = auth_client
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "Content-Security-Policy" in response.headers

    def test_headers_on_health_probes(self, client):
        assert "X-Content-Type-Options" in client.get("/healthz").headers
        ready = client.get("/readyz")
        assert "Referrer-Policy" in ready.headers


@pytest.fixture
def hardened_app():
    """App on the real Config so the TASK-029 hardening keys are present —
    the shared TestConfig leaves them at Flask defaults. Overrides only what
    tests need (SQLite, no CSRF/ratelimit)."""
    from app.config import Config

    class HardenedConfig(Config):
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        TESTING = True
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False

    app = create_app(HardenedConfig)
    with app.app_context():
        db.create_all()
        yield app
        # See conftest.py: close pooled connections before DROP so leaked
        # transactions cannot block on PostgreSQL.
        db.session.remove()
        db.engine.dispose()
        db.drop_all()


class TestSessionCookieHardening:
    def test_cookie_flags_on_login(self, hardened_app):
        from werkzeug.security import generate_password_hash

        from app.repositories import UserRepo

        with hardened_app.app_context():
            UserRepo.create(
                username="cookieuser",
                password_hash=generate_password_hash("testpass123"),
                fullname="Cookie",
            )
        client = hardened_app.test_client()
        response = client.post(
            "/login", data={"username": "cookieuser", "password": "testpass123"}
        )
        set_cookie = response.headers.get("Set-Cookie", "")
        assert "HttpOnly" in set_cookie
        assert "SameSite=Lax" in set_cookie

    def test_secure_flag_off_by_default_in_tests(self, client, create_user):
        # Test config does not enable SESSION_COOKIE_SECURE (plain HTTP).
        create_user(username="plainuser", password="testpass123")
        response = client.post(
            "/login", data={"username": "plainuser", "password": "testpass123"}
        )
        set_cookie = response.headers.get("Set-Cookie", "")
        assert "Secure" not in set_cookie

    def test_secure_flag_enabled_via_env(self):
        class ProdConfig:
            SECRET_KEY = "test-secret-key"
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            DEBUG = False
            TESTING = True
            WTF_CSRF_ENABLED = False
            RATELIMIT_ENABLED = False
            SESSION_COOKIE_SECURE = True

        from app.config import Config as _  # noqa: F401 — import path sanity

        app = create_app(ProdConfig)
        with app.app_context():
            db.create_all()
            try:
                client = app.test_client()
                from werkzeug.security import generate_password_hash

                from app.repositories import UserRepo

                UserRepo.create(
                    username="produser",
                    password_hash=generate_password_hash("testpass123"),
                    fullname="Prod",
                )
                response = client.post(
                    "/login", data={"username": "produser", "password": "testpass123"}
                )
                assert "Secure" in response.headers.get("Set-Cookie", "")
            finally:
                db.session.remove()
                db.engine.dispose()
                db.drop_all()

    def test_permanent_session_lifetime_is_seven_days(self):
        # Assert against the real Config (tests use TestConfig, which leaves
        # the key at Flask's default).
        from app.config import Config

        assert Config.PERMANENT_SESSION_LIFETIME == 60 * 60 * 24 * 7
