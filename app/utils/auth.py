import uuid
from functools import wraps

from flask import current_app, flash, g, redirect, request, session, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.extensions import db
from app.models import User
from app.models.refresh_token import REFRESH_TTL_DAYS, RefreshToken
from app.utils.i18n import t

# Access tokens are stateless signed tokens; they live this many seconds.
# Kept short so a leaked access token has a small blast window; the access
# token is refreshed with the (revocable) refresh token.
ACCESS_TOKEN_TTL_SECONDS = 15 * 60
ACCESS_SALT = "study-planner-api-access"
REFRESH_SALT = "study-planner-api-refresh"


def current_user():
    username = session.get("username")
    return User.query.filter_by(username=username).first() if username else None


def _access_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=ACCESS_SALT)


def _refresh_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=REFRESH_SALT)


def create_access_token(user):
    """Create a short-lived stateless signed access token (15 min)."""
    return _access_serializer().dumps({"user_id": user.id})


def issue_refresh_token(user):
    """Create a new refresh token and persist its jti for revocation control.

    Returns the signed token string. `rotate_refresh_token` revokes+reissues.
    """
    jti = uuid.uuid4().hex
    RefreshToken.issue(user, jti)
    db.session.commit()
    return _refresh_serializer().dumps({"user_id": user.id, "jti": jti})


def verify_refresh_token(signed_token):
    """Decode a signed refresh token, or return None when invalid/expired.

    Signature/TTL check only — no DB lookup (callers check jti state)."""
    try:
        return _refresh_serializer().loads(signed_token, max_age=REFRESH_TTL_DAYS * 24 * 60 * 60)
    except (BadSignature, SignatureExpired):
        return None


def rotate_refresh_token(signed_token):
    """Verify a refresh token, revoke it (rotation), and issue a new pair.

    Returns (user, new_access_token, new_refresh_token) on success, or
    (None, None, None) on any failure (expired, revoked, bad signature, or
    stale DB row) — the caller surfaces a 401.
    """
    payload = verify_refresh_token(signed_token)
    if not payload:
        return None, None, None
    user_id = payload.get("user_id")
    jti = payload.get("jti")
    if not user_id or not jti:
        return None, None, None
    row = RefreshToken.query.filter_by(jti=jti).first()
    if row is None or row.revoked or row.is_expired:
        return None, None, None
    user = db.session.get(User, user_id)
    if user is None:
        return None, None, None
    # Rotate: revoke the presented refresh token and issue a fresh one.
    row.revoke()
    new_refresh = issue_refresh_token(user)
    return user, create_access_token(user), new_refresh


def _authenticate_api():
    """Resolve the Bearer token to a user, or return an error response.

    Returns (user, None) on success — the user is also stashed on `g.api_user`
    — or (None, (body, status)) on any failure.
    """
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not token:
        return None, ({"error": "Bearer authentication is required."}, 401)
    try:
        payload = _access_serializer().loads(token, max_age=ACCESS_TOKEN_TTL_SECONDS)
    except (BadSignature, SignatureExpired):
        return None, ({"error": "Invalid or expired access token."}, 401)
    user = db.session.get(User, payload.get("user_id"))
    if not user:
        return None, ({"error": "User not found."}, 401)
    g.api_user = user
    return user, None


def api_auth_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user, error = _authenticate_api()
        if error is not None:
            return error
        return view(*args, **kwargs)
    return wrapped


def api_admin_required(view):
    """Bearer auth + administrator role for write-guarded API endpoints."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user, error = _authenticate_api()
        if error is not None:
            return error
        if not user.is_admin:
            return {"error": "Administrator privileges required."}, 403
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
