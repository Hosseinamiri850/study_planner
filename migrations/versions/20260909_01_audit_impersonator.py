"""Support impersonation: impersonator_id on audit_logs (TASK-040).

Revision ID: 20260909_01
Revises: 20260906_03
Create Date: 2026-09-09

Set when the actor's token was minted by /api/support/impersonate — the
support agent behind an action. NULL for every direct (non-impersonated)
write, so the column is sparse by design and needs no index yet; a
"who did this support agent touch" query can scan the small set of
support agents' own rows first if it ever becomes hot.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260909_01"
down_revision = "20260906_03"
branch_labels = None
depends_on = None


def upgrade():
    # Batch mode: SQLite cannot ALTER-add a constraint; the table is
    # recreated with the new column + FK. Production (PostgreSQL) takes
    # the same batch path safely inside a transaction.
    with op.batch_alter_table("audit_logs") as batch:
        batch.add_column(sa.Column("impersonator_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_audit_logs_impersonator_id_users",
            "users",
            ["impersonator_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("audit_logs") as batch:
        batch.drop_constraint("fk_audit_logs_impersonator_id_users", type_="foreignkey")
        batch.drop_column("impersonator_id")
