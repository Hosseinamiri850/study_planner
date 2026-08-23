"""Repository for User persistence.

Owns User lookups + writes that routes, services, and the admin CLI used to
issue directly. Reads may target a replica session; writes always go to the
primary. Auth-token machinery (`utils/auth.py`) still uses `db.session.get`
directly for cross-cutting auth state — that is intentionally out of scope
(TASK-039 targets routes and services), flagged as a non-blocking note in the
implementation result.
"""

from app.models import User
from app.repositories.base import Repo


class UserRepo(Repo):
    """Read + write access to `users`."""

    # --- reads ---

    @classmethod
    def get(cls, user_id):
        return cls._read().get(User, user_id)

    @classmethod
    def get_for_write(cls, user_id):
        """Load via the write session — required before mutating + committing."""
        return cls._write().get(User, user_id)

    @classmethod
    def find_by_username(cls, username):
        return cls._read().query(User).filter(User.username == username).first()

    @classmethod
    def list_non_admin(cls):
        return cls._read().query(User).filter(User.is_admin.is_(False)).all()

    @classmethod
    def list_admin(cls):
        return cls._read().query(User).filter(User.is_admin.is_(True)).all()

    @classmethod
    def first_admin(cls):
        return cls._read().query(User).filter(User.is_admin.is_(True)).first()

    # --- writes ---

    @classmethod
    def create(cls, *, username, password_hash, fullname, is_admin=False):
        user = User(
            username=username,
            password=password_hash,
            fullname=fullname,
            is_admin=is_admin,
        )
        cls._write().add(user)
        cls._write().commit()
        return user

    @classmethod
    def delete(cls, user_id):
        """Delete by id via the write session (safe under a configured
        replica: the instance is attached to the session that deletes it)."""
        user = cls.get_for_write(user_id)
        if user is None:
            return False
        cls._write().delete(user)
        cls._write().commit()
        return True

    @classmethod
    def update_password(cls, user, password_hash):
        """Stage the new hash without committing. Callers pair it with the
        refresh-token revocation so both land in one transaction."""
        user.password = password_hash

    @classmethod
    def update_theme(cls, user, theme):
        user.theme = theme
        cls._write().commit()

    @classmethod
    def commit(cls):
        cls._write().commit()
