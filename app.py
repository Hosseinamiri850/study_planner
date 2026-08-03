"""Development entry point for Study Planner.

Production servers should import ``app:create_app`` rather than this module.
"""

from app import create_app


app = create_app()


if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
