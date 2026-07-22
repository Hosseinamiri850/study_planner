from functools import wraps

from flask import current_app, flash, g, redirect, request, session, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.models import User
from app.extensions import db
from app.utils.i18n import t


def current_user():
    username = session.get("username")
    return User.query.filter_by(username=username).first() if username else None


def create_access_token(user):
    """Create a short-lived signed token for the mobile/API client contract."""
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="study-planner-api")
    return serializer.dumps({"user_id": user.id})


def api_auth_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not token:
            return {"error": "Bearer authentication is required."}, 401
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="study-planner-api")
        try:
            payload = serializer.loads(token, max_age=60 * 60 * 24)
        except (BadSignature, SignatureExpired):
            return {"error": "Invalid or expired access token."}, 401
        user = db.session.get(User, payload.get("user_id"))
        if not user:
            return {"error": "User not found."}, 401
        g.api_user = user
        return view(*args, **kwargs)
    return wrapped


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
