"""Configuration loaded exclusively from environment variables."""

import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/study_planner",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
