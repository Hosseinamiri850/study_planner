"""Repository for refresh-token persistence.

Owns the writes that `utils/auth.py` (token issue + rotation) and the admin
password-change flow used to issue directly against `RefreshToken`. Reads may
target a replica; writes always go to the primary. The `RefreshToken.issue`
and `revoke_user_refresh_tokens` model helpers are preserved as thin wrappers
so existing callers keep working during the transition; new call sites should
go through this repo.
"""

from app.models.refresh_token import RefreshToken
from app.repositories.base import Repo


class RefreshTokenRepo(Repo):
    """Read + write access to `refresh_tokens`."""

    # --- reads ---

    @classmethod
    def find_by_jti(cls, jti):
        return cls._read().query(RefreshToken).filter(RefreshToken.jti == jti).first()

    # --- writes ---

    @classmethod
    def issue(cls, user, jti):
        """Create a fresh, un-revoked refresh-token row with a 30-day TTL."""
        token = RefreshToken.issue(user, jti)
        return token

    @classmethod
    def revoke(cls, token):
        token.revoke()

    @classmethod
    def revoke_presented(cls, user_id, signed_token):
        """Revoke the presented refresh token if it belongs to `user_id`.

        Safely ignores garbage/unknown/expired tokens (logout must never
        500 on a malformed client payload). Verifies ownership so a token
        from another account cannot be revoked by this user.
        """
        from app.utils.auth import verify_refresh_token

        payload = verify_refresh_token(signed_token)
        if payload is None:
            return False
        jti = payload.get("jti")
        if not jti or payload.get("user_id") != user_id:
            return False
        row = cls.find_by_jti(jti)
        if row is None or row.revoked or row.is_expired:
            return False
        row.revoke()
        cls._write().commit()
        return True

    @classmethod
    def revoke_all_for_user(cls, user_id):
        """Invalidate every outstanding refresh token for a user (password
        change, logout-all). Used by the admin password-change flow."""
        cls._write().query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked.is_(False),
        ).update({"revoked": True})
        cls._write().commit()

    @classmethod
    def commit(cls):
        cls._write().commit()
