from functools import wraps

from flask import flash, redirect, session, url_for

from app.models import User
from app.utils.i18n import t


def current_user():
    username = session.get("username")
    return User.query.filter_by(username=username).first() if username else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("web.login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("web.login"))
        if not user.is_admin:
            flash(t("admin.unauthorized"), "error")
            return redirect(url_for("web.dashboard"))
        return view(*args, **kwargs)
    return wrapped
