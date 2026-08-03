"""Structured logging setup.

Emits one JSON object per log record, so logs can be shipped to a
collector (Loki, CloudWatch, a future Sentry breadcrumb feed) without
parsing. Falls back to human-readable console output when FLASK_DEBUG=true
or when running under pytest (TESTING=true).

No third-party dependency — stdlib logging plus a small JSON formatter.
"""

import json
import logging
import sys
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """Render each LogRecord as a JSON object on a single line."""

    # Map stdlib log levels to the short names a collector expects.
    _LEVELS = {"DEBUG": "debug", "INFO": "info", "WARNING": "warning",
               "ERROR": "error", "CRITICAL": "critical"}

    def format(self, record):
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": self._LEVELS.get(record.levelname, record.levelname.lower()),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Attach any extra fields the caller attached via logger.info("...", extra={...}).
        for key, value in record.__dict__.items():
            if key in payload or key.startswith("_") or key in {
                "args", "msg", "name", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName",
            }:
                continue
            try:
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(app):
    """Attach a JSON handler to the app logger and the root logger.

    Call once from create_app. Idempotent: re-configuration replaces the
    existing handler rather than stacking duplicates (important for tests,
    where create_app runs per-test).
    """
    handler = logging.StreamHandler(sys.stderr)
    if app.config.get("TESTING") or app.config.get("DEBUG"):
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    else:
        handler.setFormatter(JsonFormatter())
    handler._study_planner_structured = True  # marker for idempotent replacement

    root = logging.getLogger()
    # Remove any previously-installed structured handler so re-config in tests
    # does not duplicate output.
    root.handlers = [h for h in root.handlers if not getattr(h, "_study_planner_structured", False)]
    root.addHandler(handler)
    root.setLevel(logging.INFO if not app.config.get("DEBUG") else logging.DEBUG)

    # Quiet Flask's noisy request logger unless debugging; errors still surface via werkzeug.
    logging.getLogger("werkzeug").setLevel(logging.WARNING if not app.config.get("DEBUG") else logging.INFO)
