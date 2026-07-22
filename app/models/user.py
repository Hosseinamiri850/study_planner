from datetime import date

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    fullname = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    theme = db.Column(db.String(10), default="dark", nullable=False)
    created_at = db.Column(db.Date, default=date.today, nullable=False)
    tasks = db.relationship("Task", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
