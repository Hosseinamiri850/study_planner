"""Refresh-token persistence for the API client auth contract.

Access tokens stay stateless signed tokens (URLSafeTimedSerializer) and are
SHORT-lived. Refresh tokens are tracked here so they can be rotated and
revoked — on logout, on password change, or when an account is compromised.
"""

from datetime import UTC, datetime, timedelta

from app.extensions import db


def _utcnow():
    """Naive UTC (see app/models/task.py:_utcnow for why naive matters
    under psycopg + TIMESTAMP WITHOUT TIME ZONE columns)."""
    return datetime.now(UTC).replace(tzinfo=None)


REFRESH_TTL_DAYS = 30


class RefreshToken(db.Model):
    __tablename__ = "refresh_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # jti is the token id baked into the signed refresh token; unverifying its
    # existence+state here is what makes revocation possible.
    jti = db.Column(db.String(64), unique=True, nullable=False, index=True)
    issued_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked = db.Column(db.Boolean, default=False, nullable=False, index=True)
    user = db.relationship("User")

    @classmethod
    def issue(cls, user, jti):
        """Create a fresh, un-revoked refresh-token row with a 30-day TTL."""
        token = cls(user_id=user.id, jti=jti,
                     issued_at=_utcnow(),
                     expires_at=_utcnow() + timedelta(days=REFRESH_TTL_DAYS))
        db.session.add(token)
        return token

    @property
    def is_expired(self):
        now = _utcnow()
        exp = self.expires_at
        if exp.tzinfo is None:
            now = now.replace(tzinfo=None)
        return now >= exp

    def revoke(self):
        self.revoked = True


def revoke_user_refresh_tokens(user_id):
    """Invalidate all refresh tokens for a user (password change, logout-all)."""
    RefreshToken.query.filter_by(user_id=user_id, revoked=False).update({"revoked": True})
