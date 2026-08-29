"""Repository for Major persistence.

Owns the Major queries + writes that routes and services used to issue
directly. Reads may target a replica session; writes always go to the primary.
"""

from app.models import Major
from app.repositories.base import Repo
from app.utils.caching import KEY_COURSES_ALL, KEY_MAJORS_TEMPLATE, cache_delete


def _invalidate_major_caches():
    """Major writes dirty the nested template tree and the flat course list
    (course ordering joins majors)."""
    cache_delete(KEY_COURSES_ALL, KEY_MAJORS_TEMPLATE)


class MajorRepo(Repo):
    """Read + write access to `majors`."""

    # --- reads ---

    @classmethod
    def get(cls, major_id):
        return cls._read().get(Major, major_id)

    @classmethod
    def get_for_write(cls, major_id):
        """Load via the write session — required before mutating + committing."""
        return cls._write().get(Major, major_id)

    @classmethod
    def find_by_key(cls, key):
        return cls._read().query(Major).filter(Major.key == key).first()

    @classmethod
    def list_all(cls):
        """All majors ordered by English name (display order)."""
        return cls._read().query(Major).order_by(Major.name_en).all()

    @classmethod
    def list_courses_for_major(cls, major_id):
        """Courses of a major ordered by English name (display order)."""
        from app.models import Course

        return cls._read().query(Course).filter(Course.major_id == major_id).order_by(Course.name_en).all()

    @classmethod
    def majors_for_template(cls):
        """List shape the templates expect: majors with nested courses."""
        return [
            {
                "id": major.id,
                "key": major.key,
                "name": major.display_name(),
                "courses": [
                    {"id": course.id, "key": course.key, "name": course.display_name()}
                    for course in major.courses
                ],
            }
            for major in cls.list_all()
        ]

    # --- writes ---

    @classmethod
    def create(cls, *, key, name_fa, name_en):
        major = Major(key=key, name_fa=name_fa, name_en=name_en)
        cls._write().add(major)
        cls._write().commit()
        _invalidate_major_caches()
        return major

    @classmethod
    def add_flush(cls, major):
        """Add a new major and flush so its `.id` is available to subsequent
        writes in the same unit of work (used by the idempotent seeder)."""
        cls._write().add(major)
        cls._write().flush()
        return major

    @classmethod
    def delete(cls, major_id):
        """Delete by id via the write session (safe under a configured
        replica: the instance is attached to the session that deletes it)."""
        major = cls.get_for_write(major_id)
        if major is None:
            return False
        cls._write().delete(major)
        cls._write().commit()
        _invalidate_major_caches()
        return True

    @classmethod
    def commit(cls):
        """Commit the pending unit of work (seeder batches majors + courses
        into one transaction) and invalidate the read caches afterwards."""
        cls._write().commit()
        _invalidate_major_caches()
