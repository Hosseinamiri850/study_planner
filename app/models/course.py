from flask import session

from app.extensions import db


class Major(db.Model):
    __tablename__ = "majors"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    name_fa = db.Column(db.String(150), nullable=False)
    name_en = db.Column(db.String(150), nullable=False)
    courses = db.relationship("Course", back_populates="major", cascade="all, delete-orphan", lazy="dynamic")

    def display_name(self):
        return self.name_fa if session.get("lang", "fa") == "fa" else self.name_en


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False)
    name_fa = db.Column(db.String(150), nullable=False)
    name_en = db.Column(db.String(150), nullable=False)
    major_id = db.Column(db.Integer, db.ForeignKey("majors.id"), nullable=False)
    major = db.relationship("Major", back_populates="courses")
    tasks = db.relationship("Task", back_populates="course")

    __table_args__ = (db.UniqueConstraint("key", "major_id", name="uq_course_major"),)

    def display_name(self):
        return self.name_fa if session.get("lang", "fa") == "fa" else self.name_en
