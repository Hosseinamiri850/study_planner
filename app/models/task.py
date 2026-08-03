from datetime import UTC, date, datetime

from app.extensions import db


def _utcnow():
    """Timezone-aware UTC timestamp, for use as a SQLAlchemy column default
    or a manual assignment. Stored as a naive UTC value because none of the
    DateTime columns carry tz info; the intent (UTC) is preserved here."""
    return datetime.now(UTC)


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # Legacy columns remain during the transition so existing records and UI work.
    course_key = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), index=True)
    title = db.Column(db.String(255))
    description = db.Column(db.Text, default="")
    done = db.Column(db.Boolean, default=False, nullable=False)
    priority = db.Column(db.String(10), default="medium", nullable=False)
    hours = db.Column(db.Float, default=0.0, nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False, index=True)
    estimated_hours = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.Date, default=date.today, nullable=False)
    completed_at = db.Column(db.DateTime)
    user = db.relationship("User", back_populates="tasks")
    course = db.relationship("Course", back_populates="tasks")
    study_sessions = db.relationship("StudySession", back_populates="task", cascade="all, delete-orphan", lazy="dynamic")

    def display_title(self):
        from app.models.course import Course

        course = self.course or Course.query.filter_by(key=self.course_key).first()
        return self.title or (course.display_name() if course else self.course_key)

    def mark_complete(self):
        self.done = True
        self.status = "completed"
        self.completed_at = _utcnow()

    def mark_pending(self):
        self.done = False
        self.status = "pending"
        self.completed_at = None


class StudySession(db.Model):
    __tablename__ = "study_sessions"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    duration = db.Column(db.Integer, nullable=False)
    started_at = db.Column(db.DateTime, default=_utcnow, nullable=False, index=True)
    ended_at = db.Column(db.DateTime)
    task = db.relationship("Task", back_populates="study_sessions")
