"""Tests for structured logging setup (TASK-021)."""

import json
import logging

import pytest

from app import create_app
from app.utils.logging import JsonFormatter, init_sentry


@pytest.fixture(autouse=True)
def _isolate_root_logger():
    """configure_logging mutates the root logger globally; snapshot/restore
    handlers so each test starts clean and leaks don't reach the suite.
    """
    root = logging.getLogger()
    saved = list(root.handlers)
    saved_level = root.level
    yield
    root.handlers = saved
    root.setLevel(saved_level)


class TestConfigureLogging:
    def test_does_not_stack_duplicate_handlers_across_recreate(self):
        create_app(_LoggingTestConfig())
        first = sum(1 for h in logging.getLogger().handlers
                    if getattr(h, "_study_planner_structured", False))
        create_app(_LoggingTestConfig())
        second = sum(1 for h in logging.getLogger().handlers
                     if getattr(h, "_study_planner_structured", False))
        assert first == 1
        assert second == 1  # replaced, not added again

    def test_debug_config_uses_human_format_not_json(self):
        cfg = _LoggingTestConfig()
        cfg.DEBUG = True
        create_app(cfg)
        handler = next(h for h in logging.getLogger().handlers
                       if getattr(h, "_study_planner_structured", False))
        assert not isinstance(handler.formatter, JsonFormatter)

    def test_non_debug_config_uses_json_formatter(self):
        cfg = _LoggingTestConfig()
        cfg.DEBUG = False
        cfg.TESTING = False  # TESTING drives a human-format fallback; override it
        create_app(cfg)
        handler = next(h for h in logging.getLogger().handlers
                       if getattr(h, "_study_planner_structured", False))
        assert isinstance(handler.formatter, JsonFormatter)


class TestJsonFormatter:
    def test_record_serialises_to_json_object(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger", level=logging.ERROR, pathname=__file__,
            lineno=1, msg="translation failed %s", args=("upstream",),
            exc_info=None,
        )
        out = json.loads(formatter.format(record))
        assert out["level"] == "error"
        assert out["logger"] == "test.logger"
        assert out["message"] == "translation failed upstream"
        assert "timestamp" in out

    def test_extra_fields_are_preserved(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="app", level=logging.INFO, pathname=__file__,
            lineno=1, msg="hello", args=(), exc_info=None,
        )
        record.user_id = 42
        record.endpoint = "/api/tasks"
        out = json.loads(formatter.format(record))
        assert out["user_id"] == 42
        assert out["endpoint"] == "/api/tasks"

    def test_exc_info_included_when_present(self):
        formatter = JsonFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            record = logging.LogRecord(
                name="app", level=logging.ERROR, pathname=__file__,
                lineno=1, msg="went bad", args=(),
                exc_info=sys.exc_info(),
            )
        out = json.loads(formatter.format(record))
        assert "exc_info" in out
        assert "ValueError" in out["exc_info"]


class _LoggingTestConfig:
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


class TestInitSentry:
    def test_no_dsn_is_noop(self, app):
        # No SENTRY_DSN → init_sentry returns without touching the SDK.
        init_sentry(app)  # should not raise even though sentry_sdk is absent

    def test_dsn_without_sdk_logs_warning(self, app, caplog):
        app.config["SENTRY_DSN"] = "https://example@sentry.invalid/1"
        with caplog.at_level(logging.WARNING):
            init_sentry(app)
        assert any("sentry-sdk not installed" in r.message for r in caplog.records)

    def test_dsn_with_mock_sdk_initializes(self, app, monkeypatch):
        import sys
        from unittest.mock import MagicMock
        sdk = MagicMock()
        monkeypatch.setitem(sys.modules, "sentry_sdk", sdk)
        app.config["SENTRY_DSN"] = "https://example@sentry.invalid/1"
        app.config["SENTRY_ENVIRONMENT"] = "test-env"
        app.config["SENTRY_TRACES_SAMPLE_RATE"] = 0.5
        init_sentry(app)
        sdk.init.assert_called_once()
        _, kwargs = sdk.init.call_args
        assert kwargs["dsn"] == "https://example@sentry.invalid/1"
        assert kwargs["environment"] == "test-env"
        assert kwargs["traces_sample_rate"] == 0.5
        assert kwargs["send_default_pii"] is False
