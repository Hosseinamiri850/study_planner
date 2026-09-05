from datetime import date

from app.extensions import db

# Institution types (multi-tenancy, TASK-037). Plain strings per the
# role/status convention: no PG enum, validation at assignment boundaries.
TYPE_SCHOOL = "school"
TYPE_UNIVERSITY = "university"
TYPE_ACADEMY = "academy"

VALID_INSTITUTION_TYPES = (TYPE_SCHOOL, TYPE_UNIVERSITY, TYPE_ACADEMY)


class Institution(db.Model):
    __tablename__ = "institutions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    type = db.Column(db.String(20), default=TYPE_SCHOOL, nullable=False)
    # Commercial tier (free/pro/etc.). Plain string; values are a product
    # decision that lands with the billing feature, not a schema constraint.
    plan_tier = db.Column(db.String(30), default="free", nullable=False)
    created_at = db.Column(db.Date, default=date.today, nullable=False)
    classes = db.relationship("Class", back_populates="institution", cascade="all, delete-orphan", lazy="dynamic")


class Class(db.Model):
    __tablename__ = "classes"

    id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    grade_level = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.Date, default=date.today, nullable=False)
    institution = db.relationship("Institution", back_populates="classes")
