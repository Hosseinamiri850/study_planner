from datetime import date

from app.extensions import db

# Roles for the multi-tenancy foundation (TASK-037). Stored as a plain
# string (same convention as Task.status) so SQLite/PostgreSQL behave
# identically; validation happens at the boundaries that assign roles.
ROLE_STUDENT = "student"
ROLE_TEACHER = "teacher"
ROLE_SCHOOL_ADMIN = "school_admin"
ROLE_SITE_ADMIN = "site_admin"
ROLE_SUPPORT = "support"

VALID_ROLES = (ROLE_STUDENT, ROLE_TEACHER, ROLE_SCHOOL_ADMIN, ROLE_SITE_ADMIN, ROLE_SUPPORT)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    fullname = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(20), default=ROLE_STUDENT, nullable=False, index=True)
    # Multi-tenancy foundation: which institution the user belongs to.
    # Plain integer for now — the institutions table (and FK constraint)
    # arrives with the Institution feature itself.
    institution_id = db.Column(db.Integer, nullable=True)
    theme = db.Column(db.String(10), default="dark", nullable=False)
    created_at = db.Column(db.Date, default=date.today, nullable=False)
    tasks = db.relationship("Task", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def is_admin(self):
        """Backwards-compatibility shim over `role` (TASK-037).

        Kept so existing routes, templates, tests, and the SPA's `is_admin`
        field on /api/me keep working while the RBAC rollout lands. The
        declarative constructor routes `User(is_admin=...)` kwargs through
        the setter too, so creation call sites are unchanged.
        """
        return self.role == ROLE_SITE_ADMIN

    @is_admin.setter
    def is_admin(self, value):
        self.role = ROLE_SITE_ADMIN if value else ROLE_STUDENT
