"""Application factory and Flask CLI commands."""

import click
from flask import Flask

from app.config import Config
from app.extensions import csrf, db, migrate
from app.services.seed import seed_reference_data
from app.utils.i18n import inject_i18n


def create_app(config_object=None):
    """Create a configured Study Planner application instance."""
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config_object or Config)
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY must be set in the environment or .env file.")

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.web import web_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.context_processor(inject_i18n)

    @app.cli.command("seed-reference-data")
    def seed_reference_data_command():
        """Insert bundled majors and courses after running migrations."""
        seed_reference_data()
        click.echo("Reference data seeded.")

    return app
