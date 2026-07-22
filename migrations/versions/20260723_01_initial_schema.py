"""Initial schema for the legacy Study Planner data model."""

from alembic import op
import sqlalchemy as sa


revision = "20260723_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("majors", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("key", sa.String(length=100), nullable=False), sa.Column("name_fa", sa.String(length=150), nullable=False), sa.Column("name_en", sa.String(length=150), nullable=False), sa.UniqueConstraint("key"))
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("username", sa.String(length=80), nullable=False), sa.Column("password", sa.String(length=255), nullable=False), sa.Column("fullname", sa.String(length=150), nullable=False), sa.Column("is_admin", sa.Boolean(), nullable=False), sa.Column("theme", sa.String(length=10), nullable=False), sa.Column("created_at", sa.Date(), nullable=False), sa.UniqueConstraint("username"))
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table("courses", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("key", sa.String(length=100), nullable=False), sa.Column("name_fa", sa.String(length=150), nullable=False), sa.Column("name_en", sa.String(length=150), nullable=False), sa.Column("major_id", sa.Integer(), nullable=False), sa.ForeignKeyConstraint(["major_id"], ["majors.id"]), sa.UniqueConstraint("key", "major_id", name="uq_course_major"))
    op.create_table("tasks", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), nullable=False), sa.Column("course_key", sa.String(length=100), nullable=False), sa.Column("description", sa.Text()), sa.Column("done", sa.Boolean(), nullable=False), sa.Column("priority", sa.String(length=10), nullable=False), sa.Column("hours", sa.Float(), nullable=False), sa.Column("created_at", sa.Date(), nullable=False), sa.ForeignKeyConstraint(["user_id"], ["users.id"]))


def downgrade():
    op.drop_table("tasks")
    op.drop_table("courses")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
    op.drop_table("majors")
