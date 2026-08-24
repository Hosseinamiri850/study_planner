"""WSGI entry point for production servers (gunicorn wsgi:app).

The package directory `app/` shadows a module-level `app.py` inside the
container, so gunicorn cannot resolve `app:app`; this module gives servers
an unambiguous target.
"""

from app import create_app

app = create_app()
