"""Repository for Course persistence.

Owns the Course queries + writes that routes and services used to issue
directly. Reads may target a replica session; writes always go to the primary.
"""

from app.models import Course, Major, Task
from app.repositories.base import Repo


class CourseRepo(Repo):
    """Read + write access to `courses`."""

    # --- reads ---

    @classmethod
    def get(cls, course_id):
        return cls._read().get(Course, course_id)

    @classmethod
    def find_by_key(cls, key, *, major_id=None):
        """Find a course by key, optionally scoped to a major."""
        query = cls._read().query(Course).filter(Course.key == key)
        if major_id is not None:
            query = query.filter(Course.major_id == major_id)
        return query.first()

    @classmethod
    def find_by_key_major(cls, key, major_id):
        return (
            cls._read()
            .query(Course)
            .filter(Course.key == key, Course.major_id == major_id)
            .first()
        )

    @classmethod
    def list_all(cls):
        """All courses ordered by major then course name (display order)."""
        return (
            cls._read()
            .query(Course)
            .join(Major)
            .order_by(Major.name_en, Course.name_en)
            .all()
        )

    @classmethod
    def list_for_major(cls, major_id):
        return (
            cls._read()
            .query(Course)
            .filter(Course.major_id == major_id)
            .all()
        )

    # --- writes ---

    @classmethod
    def create(cls, *, key, name_fa, name_en, major_id):
        course = Course(key=key, name_fa=name_fa, name_en=name_en, major_id=major_id)
        cls._write().add(course)
        cls._write().commit()
        return course

    @classmethod
    def add_flush(cls, course):
        """Add a course and flush so its `.id` is available to subsequent
        writes in the same unit of work (used by the idempotent seeder)."""
        cls._write().add(course)
        cls._write().flush()
        return course

    @classmethod
    def delete_preserve_tasks(cls, course_id):
        """Null `tasks.course_id` then delete the course. Preserves the
        historical task rows (legacy `course_key` stays intact on them).
        Loads via the write session so both steps share one transaction on
        the primary even when reads go to a replica."""
        session = cls._write()
        course = session.get(Course, course_id)
        if course is None:
            return False
        session.query(Task).filter_by(course_id=course.id).update({"course_id": None})
        session.delete(course)
        session.commit()
        return True
