"""Repository for Course persistence.

Owns the Course queries + writes that routes and services used to issue
directly. Reads may target a replica session; writes always go to the primary.
"""

from app.models import Course, Major, Task
from app.repositories.base import Repo
from app.utils.caching import KEY_COURSES_ALL, KEY_MAJORS_TEMPLATE, cache_delete


def _invalidate_course_caches():
    """Course writes dirty both the flat course list and the nested major/
    course tree the templates render."""
    cache_delete(KEY_COURSES_ALL, KEY_MAJORS_TEMPLATE)


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
    def get_for_write(cls, course_id):
        """Load via the write session — required before mutating + committing."""
        return cls._write().get(Course, course_id)

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
        _invalidate_course_caches()
        return course

    @classmethod
    def commit(cls):
        """Commit the pending unit of work and invalidate the read caches."""
        cls._write().commit()
        _invalidate_course_caches()

    @classmethod
    def add_flush(cls, course):
        """Add a course and flush so its `.id` is available to subsequent
        writes in the same unit of work (used by the idempotent seeder).
        Does NOT invalidate — the seeder commits once via MajorRepo.commit,
        which invalidates."""
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
        _invalidate_course_caches()
        return True
