"""
اسکریپت انتقال داده از data.json به PostgreSQL
فقط یکبار اجرا کنید: python migrate_from_json.py
"""
import json
import os
from datetime import date
from app import app, db, User, Major, Course, Task, init_db

JSON_FILE = "data.json"

def migrate():
    if not os.path.exists(JSON_FILE):
        print("فایل data.json پیدا نشد. فقط ساختار دیتابیس ساخته می‌شود.")
        with app.app_context():
            init_db()
        print("✅ دیتابیس با موفقیت ساخته شد.")
        return

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    with app.app_context():
        db.create_all()

        # انتقال رشته‌ها و دروس
        print("📚 در حال انتقال رشته‌ها و دروس...")
        major_map = {}  # name -> id
        for major_name, major_data in data.get("majors", {}).items():
            existing = Major.query.filter_by(name=major_name).first()
            if not existing:
                major = Major(name=major_name)
                db.session.add(major)
                db.session.flush()
            else:
                major = existing
            major_map[major_name] = major.id

            for course_name in major_data.get("courses", []):
                if not Course.query.filter_by(name=course_name, major_id=major.id).first():
                    db.session.add(Course(name=course_name, major_id=major.id))

        db.session.commit()

        # انتقال کاربران و تسک‌ها
        print("👥 در حال انتقال کاربران و تسک‌ها...")
        for username, user_data in data.get("users", {}).items():
            if User.query.filter_by(username=username).first():
                print(f"  ⚠️  کاربر '{username}' از قبل وجود دارد، رد شد.")
                continue

            try:
                created_at = date.fromisoformat(user_data.get("created_at", str(date.today())))
            except (ValueError, TypeError):
                created_at = date.today()

            user = User(
                username=username,
                password=user_data.get("password", ""),
                fullname=user_data.get("fullname", username),
                is_admin=user_data.get("is_admin", False),
                theme=user_data.get("theme", "dark"),
                created_at=created_at,
            )
            db.session.add(user)
            db.session.flush()

            for task_data in user_data.get("tasks", []):
                try:
                    task_date = date.fromisoformat(task_data.get("created_at", str(date.today())))
                except (ValueError, TypeError):
                    task_date = date.today()

                task = Task(
                    user_id=user.id,
                    title=task_data.get("title", ""),
                    description=task_data.get("description", ""),
                    done=task_data.get("done", False),
                    priority=task_data.get("priority", "medium"),
                    hours=float(task_data.get("hours", 0)),
                    created_at=task_date,
                )
                db.session.add(task)

            print(f"  ✅ کاربر '{username}' با {len(user_data.get('tasks', []))} تسک منتقل شد.")

        db.session.commit()
        print("\n🎉 migration با موفقیت انجام شد!")

if __name__ == "__main__":
    migrate()
