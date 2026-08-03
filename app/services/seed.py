"""Explicit development/reference-data seeding; never runs during app startup."""

from app.extensions import db
from app.models import Course, Major

DEFAULT_DATA = {
    "majors": [{"key": "computer_science", "name_fa": "مهندسی کامپیوتر", "name_en": "Computer Science", "courses": [
        {"key": "data_structures", "name_fa": "ساختمان داده", "name_en": "Data Structures"},
        {"key": "algorithms", "name_fa": "طراحی الگوریتم", "name_en": "Algorithm Design"},
        {"key": "artificial_intelligence", "name_fa": "هوش مصنوعی", "name_en": "Artificial Intelligence"},
        {"key": "theory_of_languages", "name_fa": "نظریه زبان", "name_en": "Theory of Languages"},
        {"key": "logic_circuits", "name_fa": "مدار منطقی", "name_en": "Logic Circuits"},
        {"key": "computer_architecture", "name_fa": "معماری کامپیوتر", "name_en": "Computer Architecture"},
        {"key": "operating_systems", "name_fa": "سیستم عامل", "name_en": "Operating Systems"},
        {"key": "computer_networks", "name_fa": "شبکه‌های کامپیوتری", "name_en": "Computer Networks"},
        {"key": "database", "name_fa": "پایگاه داده", "name_en": "Database"},
        {"key": "math1", "name_fa": "ریاضی ۱", "name_en": "Mathematics 1"},
        {"key": "math2", "name_fa": "ریاضی ۲", "name_en": "Mathematics 2"},
        {"key": "probability", "name_fa": "احتمال", "name_en": "Probability"},
        {"key": "discrete_math", "name_fa": "ریاضی گسسته", "name_en": "Discrete Mathematics"},
    ]}],
}


def seed_reference_data():
    for major_data in DEFAULT_DATA["majors"]:
        major = Major.query.filter_by(key=major_data["key"]).first()
        if not major:
            major = Major(key=major_data["key"], name_fa=major_data["name_fa"], name_en=major_data["name_en"])
            db.session.add(major)
            db.session.flush()
        for course_data in major_data["courses"]:
            if not Course.query.filter_by(key=course_data["key"], major_id=major.id).first():
                db.session.add(Course(major_id=major.id, **course_data))
    db.session.commit()
