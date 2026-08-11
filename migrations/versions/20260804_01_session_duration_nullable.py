"""Allow open study sessions: make study_sessions.duration nullable.

An open session has no duration until it is stopped. The original schema
mandated NOT NULL on duration, which only made sense for closed sessions.
This revision relaxes duration to nullable and ensures started_at has an
index for the "find the latest open session" query path.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260804_01"
down_revision = "20260723_02"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("study_sessions") as batch:
        batch.alter_column("duration", existing_type=sa.Integer(), nullable=True)


def downgrade():
    # Closed rows already carry a duration; open sessions (NULL duration)
    # would fail the NOT NULL restore. Sentinel them to 0 before reverting.
    op.execute("UPDATE study_sessions SET duration = 0 WHERE duration IS NULL")
    with op.batch_alter_table("study_sessions") as batch:
        batch.alter_column("duration", existing_type=sa.Integer(), nullable=False)
