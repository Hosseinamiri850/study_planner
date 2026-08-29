"""Repository for Task + StudySession persistence.

All task/session lookups and writes from routes and services go through here.
Keeps legacy columns (`course_key`, `hours`, `done`) written alongside the
normalized ones (`course_id`, `estimated_hours`, `status`) per CLAUDE.md.
"""

from sqlalchemy import func

from app.models import StudySession, Task
from app.repositories.base import Repo


class TaskRepo(Repo):
    """Read + write access to `tasks` and `study_sessions`."""

    # --- reads (may target a replica when configured) ---

    @classmethod
    def get(cls, task_id):
        return cls._read().get(Task, task_id)

    @classmethod
    def get_for_write(cls, task_id):
        """Load via the write session — required before mutating + committing,
        so the UPDATE lands on the primary even when reads go to a replica."""
        return cls._write().get(Task, task_id)

    @classmethod
    def list_for_user(cls, user_id, *, page=None, per_page=None):
        """List a user's tasks newest-first. When page+per_page are both given,
        returns a Flask-SQLAlchemy `Pagination`; otherwise returns a plain list
        (legacy shape)."""
        query = (
            cls._read()
            .query(Task)
            .filter(Task.user_id == user_id)
            .order_by(Task.created_at.desc(), Task.id.desc())
        )
        if page is None or per_page is None:
            return query.all()
        return query.paginate(page=page, per_page=per_page, error_out=False)

    @classmethod
    def list_for_user_raw(cls, user_id):
        """All a user's tasks as a list (used by stats + dashboard)."""
        return (
            cls._read()
            .query(Task)
            .filter(Task.user_id == user_id)
            .all()
        )

    @classmethod
    def sum_seconds_by_day_for_user(cls, user_id):
        """Study time by day for a user, from StudySession durations.

        The correct hours signal (TASK-027): actual tracked session time,
        bucketed by the UTC day the session STARTED, not the task's
        estimated hours on its created_at date. Open sessions (duration
        NULL) and their days are excluded. `day` comes from func.date(),
        which is TEXT on SQLite and DATE on PostgreSQL — callers normalize
        via statistics._coerce_date.
        """
        return (
            cls._read()
            .query(
                func.coalesce(func.sum(StudySession.duration), 0).label("seconds"),
                func.date(StudySession.started_at).label("day"),
            )
            .select_from(StudySession)
            .join(Task, StudySession.task_id == Task.id)
            .filter(Task.user_id == user_id, StudySession.duration.isnot(None))
            .group_by(func.date(StudySession.started_at))
            .all()
        )

    @classmethod
    def sum_seconds_by_course_for_user(cls, user_id):
        """Study time per course key (legacy `course_key` mirror) for a user.
        Same semantics as `sum_seconds_by_day_for_user`."""
        return (
            cls._read()
            .query(
                Task.course_key.label("course_key"),
                func.coalesce(func.sum(StudySession.duration), 0).label("seconds"),
            )
            .select_from(StudySession)
            .join(Task, StudySession.task_id == Task.id)
            .filter(Task.user_id == user_id, StudySession.duration.isnot(None))
            .group_by(Task.course_key)
            .all()
        )

    @classmethod
    def system_sum_seconds_by_day(cls):
        """System-wide study time by day (admin panel). Same semantics as
        `sum_seconds_by_day_for_user`, no user filter."""
        return (
            cls._read()
            .query(
                func.coalesce(func.sum(StudySession.duration), 0).label("seconds"),
                func.date(StudySession.started_at).label("day"),
            )
            .select_from(StudySession)
            .join(Task, StudySession.task_id == Task.id)
            .filter(StudySession.duration.isnot(None))
            .group_by(func.date(StudySession.started_at))
            .all()
        )

    @classmethod
    def count_total_for_user(cls, user_id):
        return cls._read().query(Task).filter(Task.user_id == user_id).count()

    @classmethod
    def count_done_for_user(cls, user_id):
        return (
            cls._read()
            .query(Task)
            .filter(Task.user_id == user_id, Task.done.is_(True))
            .count()
        )

    @classmethod
    def active_session(cls, task_id):
        """The currently-open StudySession for a task, or None."""
        return (
            cls._read()
            .query(StudySession)
            .filter(StudySession.task_id == task_id, StudySession.ended_at.is_(None))
            .order_by(StudySession.started_at.desc())
            .first()
        )

    @classmethod
    def list_sessions_for_task(cls, task_id):
        return (
            cls._read()
            .query(StudySession)
            .filter(StudySession.task_id == task_id)
            .order_by(StudySession.started_at.desc())
            .all()
        )

    @classmethod
    def get_session(cls, session_id):
        return cls._read().get(StudySession, session_id)

    @classmethod
    def get_session_for_write(cls, session_id):
        """Write-session variant of `get_session` — use before stop()."""
        return cls._write().get(StudySession, session_id)

    # --- writes (always primary) ---

    @classmethod
    def create(cls, *, user_id, course_id, course_key, title, description, priority, hours):
        task = Task(
            user_id=user_id,
            course_id=course_id,
            course_key=course_key,
            title=title,
            description=description,
            priority=priority,
            hours=hours,
            estimated_hours=hours,
        )
        cls._write().add(task)
        cls._write().commit()
        return task

    @classmethod
    def update_course_link(cls, task, course, *, course_key=None):
        """Bind a task to a course (both normalized FK and legacy key).

        When no matching course exists (`course=None`), the submitted
        `course_key` is still written to the legacy column so it keeps
        mirroring what the user typed — the original dashboard edit flow did
        this and CLAUDE.md forbids silently dropping the legacy write."""
        task.course = course
        if course is not None:
            task.course_id = course.id
            task.course_key = course.key
        else:
            task.course_id = None
            if course_key is not None:
                task.course_key = course_key

    @classmethod
    def mark_complete(cls, task):
        task.mark_complete()
        cls._write().commit()

    @classmethod
    def mark_pending(cls, task):
        task.mark_pending()
        cls._write().commit()

    @classmethod
    def update_fields(cls, task, **fields):
        """Apply arbitrary scalar field updates (title/description/priority/
        estimated_hours/status). `estimated_hours` also mirrors to legacy
        `hours`. Does NOT commit — caller commits after batching edits, to
        keep parity with the existing web dashboard edit flow."""
        for key, value in fields.items():
            if key == "estimated_hours" and value is not None:
                task.estimated_hours = value
                task.hours = value
            elif hasattr(task, key):
                setattr(task, key, value)
        return task

    @classmethod
    def delete(cls, task):
        cls._write().delete(task)
        cls._write().commit()

    @classmethod
    def start_session(cls, task):
        session = task.start_session()
        cls._write().commit()
        return session

    @classmethod
    def stop_session(cls, session):
        session.stop()
        cls._write().commit()
        return session

    @classmethod
    def commit(cls):
        cls._write().commit()
