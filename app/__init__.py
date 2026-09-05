"""Application factory and Flask CLI commands."""

import os

import click
from flask import Flask, jsonify
from sqlalchemy import text

from app.config import Config
from app.extensions import csrf, db, limiter, migrate
from app.repositories import UserRepo
from app.services.seed import seed_reference_data
from app.utils.i18n import inject_i18n
from app.utils.logging import configure_logging, init_sentry
from app.utils.validation import valid_password, valid_username


def create_app(config_object=None):
    """Create a configured Study Planner application instance."""
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config_object or Config)
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY must be set in the environment or .env file.")

    configure_logging(app)
    init_sentry(app)
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)

    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.school import school_bp
    from app.routes.web import web_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(school_bp)
    app.context_processor(inject_i18n)

    @app.after_request
    def set_security_headers(response):
        """Attach the security headers from config (TASK-029). Applied to every
        response including API JSON and health probes — they are cheap and
        harmless there."""
        response.headers.setdefault(
            "Strict-Transport-Security",
            f"max-age={os.environ.get('HSTS_MAX_AGE', '31536000')}; includeSubDomains",
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "; ".join(
                f"{directive} {app.config[key]}"
                for directive, key in (
                    ("default-src", "CSP_DEFAULT_SRC"),
                    ("script-src", "CSP_SCRIPT_SRC"),
                    ("style-src", "CSP_STYLE_SRC"),
                    ("img-src", "CSP_IMG_SRC"),
                    ("connect-src", "CSP_CONNECT_SRC"),
                )
                if key in app.config
            ),
        )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    @app.cli.command("seed-reference-data")
    def seed_reference_data_command():
        """Insert bundled majors and courses after running migrations."""
        seed_reference_data()
        click.echo("Reference data seeded.")

    @app.cli.command("create-admin")
    @click.argument("username")
    @click.option("--promote", is_flag=True, help="Grant admin role to an existing user instead of creating one.")
    def create_admin_command(username, promote):
        """Create an administrator account (or promote an existing user).

        Prompts for a password; the password is hashed and never echoed or
        logged. Intentionally the only way to bootstrap the first admin —
        `seed-reference-data` creates none.
        """
        existing = UserRepo.find_by_username(username)
        if existing and not promote:
            click.echo(f"Error: username '{username}' already exists. "
                       f"Use --promote to grant it admin role, or pick another username.")
            return
        if promote:
            if not existing:
                click.echo(f"Error: no user named '{username}' to promote.")
                return
            if existing.is_admin:
                click.echo(f"'{username}' is already an administrator.")
                return
            existing.is_admin = True
            UserRepo.commit()
            click.echo(f"Promoted '{username}' to administrator.")
            return
        if not valid_username(username):
            click.echo("Error: username must be 3–80 letters, numbers, or underscores.")
            return
        password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
        if not valid_password(password):
            click.echo("Error: password must be at least 8 characters.")
            return
        from werkzeug.security import generate_password_hash
        UserRepo.create(
            username=username,
            password_hash=generate_password_hash(password),
            fullname=username,
            is_admin=True,
        )
        click.echo(f"Administrator '{username}' created.")

    @app.route("/healthz", methods=["GET"])
    @csrf.exempt
    def healthz():
        """Liveness probe — process is up. No DB check, always 200."""
        return jsonify({"status": "ok"}), 200

    @app.route("/readyz", methods=["GET"])
    @csrf.exempt
    def readyz():
        """Readiness probe — DB reachable via `SELECT 1`. 503 on failure."""
        try:
            db.session.execute(text("SELECT 1")).scalar()
        except Exception:
            return jsonify({"status": "error", "db": "unavailable"}), 503
        return jsonify({"status": "ok", "db": "ready"}), 200

    return app
