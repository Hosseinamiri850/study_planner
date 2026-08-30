from datetime import UTC, date, datetime

from app.extensions import db


def _utcnow():
    """Naive UTC timestamp for the DateTime columns (all naive). Must be
    NAIVE, not tz-aware: psycopg sends an aware value as timestamptz and
    PostgreSQL then converts it to the server's local zone when storing
    into a TIMESTAMP WITHOUT TIME ZONE column, which corrupts the wall
    clock on any non-UTC host (surfaced as negative study-session
    durations via the frontend, 2026-08-30). datetime.utcnow() yields the
    naive UTC wall clock that both SQLite and PostgreSQL store verbatim."""
    return datetime.now(UTC).replace(tzinfo=None)


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

    @property
    def active_session(self):
        """Return the currently-open StudySession for this task, or None."""
        return StudySession.query.filter_by(task_id=self.id, ended_at=None).order_by(StudySession.started_at.desc()).first()

    def start_session(self):
        """Open a new study session for this task. Caller is responsible for
        checking there isn't one already open (`active_session`)."""
        session = StudySession(task_id=self.id)
        db.session.add(session)
        return session


class StudySession(db.Model):
    __tablename__ = "study_sessions"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    duration = db.Column(db.Integer)  # seconds; NULL while the session is still open
    started_at = db.Column(db.DateTime, default=_utcnow, nullable=False, index=True)
    ended_at = db.Column(db.DateTime)
    task = db.relationship("Task", back_populates="study_sessions")

    @property
    def is_open(self):
        return self.ended_at is None

    def stop(self):
        """Close the session: stamp ended_at and compute duration in seconds."""
        if self.ended_at is not None:
            return False  # already closed; caller should treat as no-op
        end = _utcnow()
        self.ended_at = end
        start = self.started_at
        if start is not None:
            # Columns are naive UTC; start may come back naive after a round
            # trip through SQLite while end is tz-aware. Normalise both sides.
            if hasattr(start, "tzinfo") and start.tzinfo is not None:
                start = start.replace(tzinfo=None)
            if hasattr(end, "tzinfo") and end.tzinfo is not None:
                end = end.replace(tzinfo=None)
            delta = end - start
            self.duration = int(delta.total_seconds())
        else:
            self.duration = 0
        return True
