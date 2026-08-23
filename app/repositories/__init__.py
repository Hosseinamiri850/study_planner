"""Data-access layer (repositories) for the Study Planner.

Owns every `db.session` / ORM-query usage that used to live in routes and
services. Routes and services call repositories; they do not touch the ORM
session directly. The seam also supports a future PostgreSQL read replica:
read methods may target a replica session, write methods always target the
primary. See `.ai/DESIGN.md` and `.ai/ROADMAP.md` (TASK-039).
"""

from app.repositories.base import Repo, read_session, write_session
from app.repositories.course_repo import CourseRepo
from app.repositories.major_repo import MajorRepo
from app.repositories.refresh_token_repo import RefreshTokenRepo
from app.repositories.task_repo import TaskRepo
from app.repositories.user_repo import UserRepo

__all__ = [
    "Repo",
    "read_session",
    "write_session",
    "CourseRepo",
    "MajorRepo",
    "RefreshTokenRepo",
    "TaskRepo",
    "UserRepo",
]
