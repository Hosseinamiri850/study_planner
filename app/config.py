"""Configuration loaded exclusively from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/study_planner",
    )
    # Replication readiness seam: comma-separated read-replica URIs. Empty
    # today — no replica implemented. When set, the data-access layer routes
    # read-only queries to a replica session and writes always go to the
    # primary. See `.ai/DESIGN.md` and TASK-039.
    DATABASE_REPLICA_URLS = os.environ.get("DATABASE_REPLICA_URLS", "")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    # Rate-limit storage URI: Redis when set, in-memory otherwise.
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    # Auth endpoints are brute-force targets — allow 5 attempts per minute.
    RATELIMIT_AUTH = "5 per minute"
    # Sentry is optional: blank DSN → SDK never initializes. Set via env in prod.
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
    SENTRY_ENVIRONMENT = os.environ.get("SENTRY_ENVIRONMENT", "production")
    SENTRY_TRACES_SAMPLE_RATE = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.0"))
    # Session cookie hardening (TASK-029). HTTPONLY + Samesite=Lax apply in all
    # environments; Secure is opt-in via env because local dev is plain HTTP.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    # 7 days: matches the refresh-token TTL's spirit; the browser session
    # should not outlive a reasonable "remember me on this machine" window.
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7
    # Content-Security-Policy (TASK-029). Deliberately permissive while the
    # server-rendered templates use CDN assets and inline handlers/scripts:
    # Bootstrap + bootstrap-icons + Chart.js from jsDelivr, 'unsafe-inline'
    # for style/script until the Next.js migration removes them. Tighten then.
    CSP_DEFAULT_SRC = "'self'"
    CSP_SCRIPT_SRC = "'self' https://cdn.jsdelivr.net 'unsafe-inline'"
    CSP_STYLE_SRC = "'self' https://cdn.jsdelivr.net 'unsafe-inline'"
    CSP_IMG_SRC = "'self' data:"
    CSP_CONNECT_SRC = "'self'"
