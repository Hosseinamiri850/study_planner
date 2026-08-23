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
    # Application cache (TASK-025). Distinct from RATELIMIT_STORAGE_URI so the
    # rate limiter and the data cache can use different Redis DBs. Empty =
    # no caching; every read goes to the database.
    REDIS_URL = os.environ.get("REDIS_URL", "")
    # Auth endpoints are brute-force targets — allow 5 attempts per minute.
    RATELIMIT_AUTH = "5 per minute"
    # Sentry is optional: blank DSN → SDK never initializes. Set via env in prod.
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
    SENTRY_ENVIRONMENT = os.environ.get("SENTRY_ENVIRONMENT", "production")
    SENTRY_TRACES_SAMPLE_RATE = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.0"))
