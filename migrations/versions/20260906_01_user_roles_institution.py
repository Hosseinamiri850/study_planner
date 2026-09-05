"""Multi-tenancy foundations: User.role + User.institution_id (TASK-037).

Replaces the `is_admin` boolean with a role string. Backfill rule:
every existing `is_admin=True` row becomes role='site_admin', every
other row becomes role='student' — no data loss, no manual intervention.

Downgrade mirrors the backfill exactly: role='site_admin' -> is_admin=1,
anything else -> is_admin=0, then drops both new columns. New roles
introduced after this revision (teacher/school_admin/support) collapse to
non-admin on downgrade — that is the lossy direction and is expected.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260906_01"
down_revision = "20260829_01"
branch_labels = None
depends_on = None

_SITE_ADMIN = "site_admin"


def upgrade():
    op.add_column("users", sa.Column("role", sa.String(length=20), nullable=False, server_default="student"))
    op.add_column("users", sa.Column("institution_id", sa.Integer(), nullable=True))
    op.create_index("ix_users_role", "users", ["role"])
    # Backfill from the legacy boolean before dropping it. Uses a bind
    # param for the boolean comparison so the operator exists on both
    # PostgreSQL (= true) and SQLite (= 1).
    conn = op.get_bind()
    users = sa.table(
        "users",
        sa.column("is_admin", sa.Boolean),
        sa.column("role", sa.String),
    )
    conn.execute(
        users.update()
        .where(users.c.is_admin == sa.true())
        .values(role=_SITE_ADMIN)
    )
    op.drop_column("users", "is_admin")


def downgrade():
    # is_admin comes back with a non-null default so the add succeeds even
    # if rows exist; the backfill then sets the real values.
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    conn = op.get_bind()
    users = sa.table(
        "users",
        sa.column("is_admin", sa.Boolean),
        sa.column("role", sa.String),
    )
    conn.execute(
        users.update()
        .where(users.c.role == _SITE_ADMIN)
        .values(is_admin=sa.true())
    )
    op.drop_index("ix_users_role", table_name="users")
    op.drop_column("users", "institution_id")
    op.drop_column("users", "role")
