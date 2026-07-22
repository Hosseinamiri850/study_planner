from datetime import date

from app.extensions import db


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_key = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default="")
    done = db.Column(db.Boolean, default=False, nullable=False)
    priority = db.Column(db.String(10), default="medium", nullable=False)
    hours = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.Date, default=date.today, nullable=False)
    user = db.relationship("User", back_populates="tasks")

    def display_title(self):
        from app.models.course import Course

        course = Course.query.filter_by(key=self.course_key).first()
        return course.display_name() if course else self.course_key
