"""Add incremental task fields and study-session tracking."""

from alembic import op
import sqlalchemy as sa


revision = "20260723_02"
down_revision = "20260723_01"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("course_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("title", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("status", sa.String(length=20), nullable=True))
        batch.add_column(sa.Column("estimated_hours", sa.Float(), nullable=True))
        batch.add_column(sa.Column("completed_at", sa.DateTime(), nullable=True))
        batch.create_foreign_key("fk_tasks_course_id", "courses", ["course_id"], ["id"])
        batch.create_index("ix_tasks_course_id", ["course_id"])
        batch.create_index("ix_tasks_status", ["status"])
    op.execute("UPDATE tasks SET status = CASE WHEN done THEN 'completed' ELSE 'pending' END")
    op.execute("UPDATE tasks SET estimated_hours = hours")
    with op.batch_alter_table("tasks") as batch:
        batch.alter_column("status", existing_type=sa.String(length=20), nullable=False)
        batch.alter_column("estimated_hours", existing_type=sa.Float(), nullable=False)
    op.create_table("study_sessions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("task_id", sa.Integer(), nullable=False), sa.Column("duration", sa.Integer(), nullable=False), sa.Column("started_at", sa.DateTime(), nullable=False), sa.Column("ended_at", sa.DateTime(), nullable=True), sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"))
    op.create_index("ix_study_sessions_task_id", "study_sessions", ["task_id"])
    op.create_index("ix_study_sessions_started_at", "study_sessions", ["started_at"])


def downgrade():
    op.drop_index("ix_study_sessions_started_at", table_name="study_sessions")
    op.drop_index("ix_study_sessions_task_id", table_name="study_sessions")
    op.drop_table("study_sessions")
    with op.batch_alter_table("tasks") as batch:
        batch.drop_index("ix_tasks_status")
        batch.drop_index("ix_tasks_course_id")
        batch.drop_constraint("fk_tasks_course_id", type_="foreignkey")
        batch.drop_column("completed_at")
        batch.drop_column("estimated_hours")
        batch.drop_column("status")
        batch.drop_column("title")
        batch.drop_column("course_id")
