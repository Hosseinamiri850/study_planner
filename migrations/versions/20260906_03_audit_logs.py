"""Audit log table (TASK-035).

Append-only before/after history for instrumented mutations. Indexes on
(institution_id, created_at) and (actor_user_id, created_at) serve the two
expected filter axes — tenant timeline and per-actor history — without
scanning a table expected to grow large. created_at gets its own single-
column index for retention/pruning jobs.

Downgrade drops the table; audit history is non-recoverable, which is the
expected lossy direction for a downgrade.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260906_03"
down_revision = "20260906_02"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        sa.Column("institution_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_institution_created", "audit_logs", ["institution_id", "created_at"])
    op.create_index("ix_audit_logs_actor_created", "audit_logs", ["actor_user_id", "created_at"])


def downgrade():
    op.drop_index("ix_audit_logs_actor_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_institution_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")
