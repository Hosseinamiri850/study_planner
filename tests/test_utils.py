from datetime import date

import pytest

from app.utils.validation import valid_username, valid_password, valid_priority, positive_hours


class TestValidation:
    @pytest.mark.parametrize("value,expected", [
        ("valid_user", True),
        ("user_123", True),
        ("ab", False),
        ("", False),
        ("user name", False),
        ("user@name", False),
        ("a" * 81, False),
    ])
    def test_valid_username(self, value, expected):
        assert valid_username(value) == expected

    @pytest.mark.parametrize("value,expected", [
        ("password123", True),
        ("12345678", True),
        ("short", False),
        ("", False),
        ("a" * 1000, True),
    ])
    def test_valid_password(self, value, expected):
        assert valid_password(value) == expected

    @pytest.mark.parametrize("value,expected", [
        ("high", True),
        ("medium", True),
        ("low", True),
        ("urgent", False),
        ("", False),
        ("HIGH", False),
    ])
    def test_valid_priority(self, value, expected):
        assert valid_priority(value) == expected

    @pytest.mark.parametrize("value,expected", [
        (0, 0.0),
        (5, 5.0),
        (24, 24.0),
        (12.5, 12.5),
        (-1, None),
        (25, None),
        ("abc", None),
        (None, None),
    ])
    def test_positive_hours(self, value, expected):
        assert positive_hours(value) == expected


class TestI18n:
    def test_supported_langs(self):
        from app.utils.i18n import SUPPORTED_LANGS
        assert "fa" in SUPPORTED_LANGS
        assert "en" in SUPPORTED_LANGS

    def test_get_lang_default(self, app):
        from app.utils.i18n import get_lang
        with app.test_request_context():
            assert get_lang() == "fa"

    def test_get_lang_from_session(self, app):
        from app.utils.i18n import get_lang
        with app.test_request_context():
            from flask import session
            session["lang"] = "en"
            assert get_lang() == "en"

    def test_translate_existing_key(self, app):
        from app.utils.i18n import t
        with app.test_request_context():
            result = t("app_name")
            assert result == "برنامه‌ریز مطالعه"

    def test_translate_nested_key(self, app):
        from app.utils.i18n import t
        with app.test_request_context():
            result = t("auth.login_title")
            assert result == "ورود به حساب"

    def test_translate_missing_key(self, app):
        from app.utils.i18n import t
        with app.test_request_context():
            result = t("nonexistent.key")
            assert result == "nonexistent.key"

    def test_inject_i18n_context_processor(self, app):
        from app.utils.i18n import inject_i18n
        with app.test_request_context():
            ctx = inject_i18n()
            assert "t" in ctx
            assert "lang" in ctx
            assert "dir" in ctx
            assert "supported_langs" in ctx
            assert "translator_available" in ctx


class TestAuth:
    def test_current_user_returns_none_when_not_logged_in(self, app):
        from app.utils.auth import current_user
        with app.test_request_context():
            assert current_user() is None

    def test_current_user_returns_user_when_logged_in(self, app, create_user):
        from app.utils.auth import current_user
        user = create_user(username="testuser")
        with app.test_request_context():
            from flask import session
            session["username"] = "testuser"
            assert current_user() == user

    def test_login_required_redirects(self, app, client):
        from app.utils.auth import login_required
        @login_required
        def protected():
            return "ok"
        with app.test_request_context():
            from flask import session
            session.clear()
            response = protected()
            assert response.status_code == 302

    def test_admin_required_redirects_non_admin(self, app, create_user, client):
        from app.utils.auth import admin_required
        user = create_user(username="regular", is_admin=False)
        @admin_required
        def protected():
            return "ok"
        with app.test_request_context():
            from flask import session, flash
            session["username"] = "regular"
            response = protected()
            assert response.status_code == 302
