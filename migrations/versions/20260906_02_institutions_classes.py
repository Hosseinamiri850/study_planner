"""Multi-tenancy: institutions + classes tables, User FK wiring (TASK-037).

Adds the Institution and Class tables on the shared database (no schema
separation in this revision) and upgrades the User columns added in
20260906_01:
- `institution_id` (plain integer until now) gains a real FK constraint to
  institutions.id.
- `class_id` arrives as a new nullable FK to classes.id.

Existing users end up with institution_id/class_id NULL — they are B2C
users and are unaffected. SQLite cannot add a FK with plain ALTER, so the
users table goes through batch_alter_table (a table rebuild there; a
no-op-level change on PostgreSQL).

Downgrade drops the class_id column and both tables, leaving
`institution_id` in its pre-revision state (present, no FK). Users lose
their institution/class association — non-recoverable, expected for a
downgrade.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260906_02"
down_revision = "20260906_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "institutions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False, server_default="school"),
        sa.Column("plan_tier", sa.String(length=30), nullable=False, server_default="free"),
        sa.Column("created_at", sa.Date(), nullable=False),
    )
    op.create_table(
        "classes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("grade_level", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_classes_institution_id", "classes", ["institution_id"])

    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("class_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_users_institution_id_institutions", "institutions", ["institution_id"], ["id"]
        )
        batch.create_foreign_key("fk_users_class_id_classes", "classes", ["class_id"], ["id"])


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("fk_users_class_id_classes", type_="foreignkey")
        batch.drop_constraint("fk_users_institution_id_institutions", type_="foreignkey")
        batch.drop_column("class_id")
    op.drop_index("ix_classes_institution_id", table_name="classes")
    op.drop_table("classes")
    op.drop_table("institutions")
