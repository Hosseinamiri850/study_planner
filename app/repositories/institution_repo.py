"""Repository for Institution + Class persistence.

Multi-tenancy read/write access (TASK-037). Same read/write session seam as
the other repositories: reads may target a replica when one is configured,
writes always go to the primary.
"""

from app.models import Class, Institution
from app.repositories.base import Repo


class InstitutionRepo(Repo):
    """Read + write access to `institutions`."""

    # --- reads ---

    @classmethod
    def get(cls, institution_id):
        return cls._read().get(Institution, institution_id)

    @classmethod
    def get_for_write(cls, institution_id):
        """Load via the write session — required before mutating + committing."""
        return cls._write().get(Institution, institution_id)

    @classmethod
    def list_all(cls):
        return cls._read().query(Institution).order_by(Institution.name).all()

    # --- writes ---

    @classmethod
    def create(cls, *, name, type, plan_tier="free"):
        institution = Institution(name=name, type=type, plan_tier=plan_tier)
        cls._write().add(institution)
        cls._write().commit()
        return institution

    @classmethod
    def delete(cls, institution):
        cls._write().delete(institution)
        cls._write().commit()

    @classmethod
    def commit(cls):
        cls._write().commit()


class ClassRepo(Repo):
    """Read + write access to `classes`."""

    # --- reads ---

    @classmethod
    def get(cls, class_id):
        return cls._read().get(Class, class_id)

    @classmethod
    def get_for_write(cls, class_id):
        """Load via the write session — required before mutating + committing."""
        return cls._write().get(Class, class_id)

    @classmethod
    def list_for_institution(cls, institution_id):
        return (
            cls._read()
            .query(Class)
            .filter(Class.institution_id == institution_id)
            .order_by(Class.created_at.desc(), Class.id.desc())
            .all()
        )

    # --- writes ---

    @classmethod
    def create(cls, *, institution_id, name, grade_level=None):
        klass = Class(institution_id=institution_id, name=name, grade_level=grade_level)
        cls._write().add(klass)
        cls._write().commit()
        return klass

    @classmethod
    def update_fields(cls, klass, **fields):
        """Apply scalar field updates (name/grade_level). Does NOT commit —
        caller commits after batching edits."""
        for key, value in fields.items():
            if hasattr(klass, key):
                setattr(klass, key, value)
        return klass

    @classmethod
    def delete(cls, klass):
        cls._write().delete(klass)
        cls._write().commit()

    @classmethod
    def commit(cls):
        cls._write().commit()
