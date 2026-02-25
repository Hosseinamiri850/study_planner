from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import date, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your-secret-key-change-this-in-production")

# ===== تنظیمات PostgreSQL =====
# مثال: postgresql://username:password@localhost:5432/study_planner
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/study_planner"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ===== مدل‌های دیتابیس =====

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


class Major(db.Model):
    __tablename__ = "majors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    courses = db.relationship("Course", back_populates="major", cascade="all, delete-orphan", lazy="dynamic")


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    major_id = db.Column(db.Integer, db.ForeignKey("majors.id"), nullable=False)

    major = db.relationship("Major", back_populates="courses")

    __table_args__ = (db.UniqueConstraint("name", "major_id", name="uq_course_major"),)


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default="")
    done = db.Column(db.Boolean, default=False, nullable=False)
    priority = db.Column(db.String(10), default="medium", nullable=False)
    hours = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.Date, default=date.today, nullable=False)

    user = db.relationship("User", back_populates="tasks")


# ===== ساخت جداول و داده‌های اولیه =====

def init_db():
    db.create_all()

    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            password="admin",
            fullname="مدیر سیستم",
            is_admin=True,
            theme="dark"
        )
        db.session.add(admin)

    if not Major.query.filter_by(name="کامپیوتر").first():
        major = Major(name="کامپیوتر")
        db.session.add(major)
        db.session.flush()
        default_courses = [
            "ساختمان داده", "طراحی الگوریتم", "هوش مصنوعی", "نظریه زبان",
            "مدار منطقی", "معماری", "سیستم عامل", "شبکه های کامپیوتری",
            "پایگاه داده", "ریاضی 1", "ریاضی 2", "احتمال", "گسسته"
        ]
        for c in default_courses:
            db.session.add(Course(name=c, major_id=major.id))

    db.session.commit()


# ===== دکوراتورها =====

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        user = User.query.filter_by(username=session["username"]).first()
        if not user or not user.is_admin:
            flash("دسترسی غیرمجاز!", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


# ===== توابع کمکی =====

def get_user_stats(user):
    today = date.today()
    today_str = str(today)
    tasks = user.tasks.all()
    total_tasks = len(tasks)
    total_done = sum(1 for t in tasks if t.done)
    today_hours = sum(t.hours for t in tasks if t.done and str(t.created_at) == today_str)

    week_hours = {}
    for i in range(7):
        day = today - timedelta(days=i)
        day_str = str(day)
        week_hours[day_str] = sum(t.hours for t in tasks if t.done and str(t.created_at) == day_str)
    total_week_hours = sum(week_hours.values())

    month_hours = {}
    for i in range(30):
        day = today - timedelta(days=i)
        day_str = str(day)
        day_total = sum(t.hours for t in tasks if t.done and str(t.created_at) == day_str)
        if day_total > 0:
            month_hours[day_str] = day_total
    total_month_hours = sum(month_hours.values())

    return dict(
        tasks=tasks, total_tasks=total_tasks, total_done=total_done,
        today_hours=today_hours, week_hours=week_hours, total_week_hours=total_week_hours,
        month_hours=month_hours, total_month_hours=total_month_hours,
    )


def get_all_courses():
    courses = Course.query.join(Major).order_by(Major.name, Course.name).all()
    seen, result = [], []
    for c in courses:
        if c.name not in seen:
            seen.append(c.name)
            result.append(c.name)
    return result


def get_course_stats(tasks, all_courses):
    stats = {}
    for course in all_courses:
        ct = [t for t in tasks if t.title == course]
        stats[course] = {
            "total": len(ct),
            "done": sum(1 for t in ct if t.done),
            "hours": sum(t.hours for t in ct if t.done),
        }
    return stats


# ===== روت‌ها =====

@app.route("/")
def home():
    if "username" in session:
        user = User.query.filter_by(username=session["username"]).first()
        if user and user.is_admin:
            return redirect(url_for("admin_panel"))
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session["username"] = username
            return redirect(url_for("admin_panel") if user.is_admin else url_for("dashboard"))
        flash("نام کاربری یا رمز عبور اشتباه است!", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        fullname = request.form.get("fullname", "").strip()
        if not username or not password or not fullname:
            flash("لطفاً همه فیلدها را پر کنید!", "error")
            return render_template("register.html")
        if User.query.filter_by(username=username).first():
            flash("این نام کاربری قبلاً ثبت شده است!", "error")
        else:
            db.session.add(User(username=username, password=password, fullname=fullname))
            db.session.commit()
            flash("ثبت‌نام با موفقیت انجام شد! وارد شوید.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))


@app.route("/toggle-theme", methods=["POST"])
@login_required
def toggle_theme():
    user = User.query.filter_by(username=session["username"]).first()
    user.theme = "light" if user.theme == "dark" else "dark"
    db.session.commit()
    return jsonify({"theme": user.theme})


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    user = User.query.filter_by(username=session["username"]).first()
    if user.is_admin:
        return redirect(url_for("admin_panel"))

    today = str(date.today())

    if request.method == "POST":
        if "new_task" in request.form:
            course = request.form.get("course")
            priority = request.form.get("priority", "medium")
            description = request.form.get("description", "").strip()
            try:
                hours = float(request.form.get("task_hours", "0"))
            except ValueError:
                hours = 0.0
            if course:
                db.session.add(Task(user_id=user.id, title=course, description=description, priority=priority, hours=hours))

        elif "toggle" in request.form:
            task = Task.query.get(int(request.form["toggle"]))
            if task and task.user_id == user.id:
                task.done = not task.done

        elif "delete" in request.form:
            task = Task.query.get(int(request.form["delete"]))
            if task and task.user_id == user.id:
                db.session.delete(task)

        elif "edit_idx" in request.form:
            task = Task.query.get(int(request.form["edit_idx"]))
            if task and task.user_id == user.id:
                new_course = request.form.get("edit_course")
                if new_course:
                    task.title = new_course
                    task.priority = request.form.get("edit_priority")
                    task.description = request.form.get("edit_description", "")
                    try:
                        task.hours = float(request.form.get("edit_hours", "0"))
                    except ValueError:
                        task.hours = 0.0

        elif "new_major" in request.form:
            name = request.form.get("new_major", "").strip()
            if name and not Major.query.filter_by(name=name).first():
                db.session.add(Major(name=name))

        elif "add_course" in request.form:
            major = Major.query.filter_by(name=request.form.get("major_for_course")).first()
            course_name = request.form.get("new_course", "").strip()
            if major and course_name and not Course.query.filter_by(name=course_name, major_id=major.id).first():
                db.session.add(Course(name=course_name, major_id=major.id))

        elif "delete_course" in request.form:
            major = Major.query.filter_by(name=request.form.get("delete_major")).first()
            if major:
                course = Course.query.filter_by(name=request.form.get("delete_course"), major_id=major.id).first()
                if course:
                    db.session.delete(course)

        db.session.commit()
        return redirect(url_for("dashboard"))

    stats = get_user_stats(user)
    all_courses = get_all_courses()
    course_stats = get_course_stats(stats["tasks"], all_courses)
    majors = Major.query.order_by(Major.name).all()

    all_users_data = []
    for u in User.query.filter_by(is_admin=False).all():
        u_tasks = u.tasks.all()
        all_users_data.append({
            "username": u.username,
            "fullname": u.fullname,
            "total_tasks": len(u_tasks),
            "done_tasks": sum(1 for t in u_tasks if t.done),
            "today_hours": sum(t.hours for t in u_tasks if t.done and str(t.created_at) == today),
            "is_current": u.username == user.username,
        })

    return render_template(
        "dashboard.html",
        current_user=user.username,
        fullname=user.fullname,
        tasks=stats["tasks"],
        total_done=stats["total_done"],
        total_tasks=stats["total_tasks"],
        today=today,
        today_hours=stats["today_hours"],
        courses=all_courses,
        course_stats=course_stats,
        week_hours=stats["week_hours"],
        total_week_hours=stats["total_week_hours"],
        month_hours=stats["month_hours"],
        total_month_hours=stats["total_month_hours"],
        all_users=all_users_data,
        theme=user.theme,
        majors={m.name: {"courses": [c.name for c in m.courses]} for m in majors},
    )


@app.route("/user/<username>")
@login_required
def view_user(username):
    current = User.query.filter_by(username=session["username"]).first()
    target = User.query.filter_by(username=username).first()
    if not target or target.is_admin:
        flash("کاربر یافت نشد!", "error")
        return redirect(url_for("dashboard"))

    today = str(date.today())
    stats = get_user_stats(target)
    all_courses = get_all_courses()
    course_stats = get_course_stats(stats["tasks"], all_courses)

    return render_template(
        "view_user.html",
        viewed_user=target.username,
        fullname=target.fullname,
        tasks=stats["tasks"],
        total_done=stats["total_done"],
        total_tasks=stats["total_tasks"],
        today=today,
        today_hours=stats["today_hours"],
        courses=all_courses,
        course_stats=course_stats,
        week_hours=stats["week_hours"],
        total_week_hours=stats["total_week_hours"],
        month_hours=stats["month_hours"],
        total_month_hours=stats["total_month_hours"],
        is_own_profile=(target.username == current.username),
        theme=current.theme,
    )


@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin_panel():
    today = str(date.today())

    if request.method == "POST":
        if "delete_user" in request.form:
            uname = request.form.get("delete_user")
            if uname != "admin":
                u = User.query.filter_by(username=uname).first()
                if u:
                    db.session.delete(u)

        elif "change_password" in request.form:
            u = User.query.filter_by(username=request.form.get("change_password")).first()
            new_pw = request.form.get("new_password")
            if u and new_pw:
                u.password = new_pw

        elif "delete_major" in request.form:
            name = request.form.get("delete_major")
            if name != "کامپیوتر":
                m = Major.query.filter_by(name=name).first()
                if m:
                    db.session.delete(m)

        elif "add_major" in request.form:
            name = request.form.get("new_major", "").strip()
            if name and not Major.query.filter_by(name=name).first():
                db.session.add(Major(name=name))

        elif "add_course" in request.form:
            major = Major.query.filter_by(name=request.form.get("major_for_course")).first()
            course_name = request.form.get("new_course", "").strip()
            if major and course_name and not Course.query.filter_by(name=course_name, major_id=major.id).first():
                db.session.add(Course(name=course_name, major_id=major.id))

        elif "delete_course" in request.form:
            major = Major.query.filter_by(name=request.form.get("course_major")).first()
            if major:
                course = Course.query.filter_by(name=request.form.get("delete_course"), major_id=major.id).first()
                if course:
                    db.session.delete(course)

        db.session.commit()
        return redirect(url_for("admin_panel"))

    non_admin = User.query.filter_by(is_admin=False).all()
    total_users = len(non_admin)
    total_tasks_all = sum(u.tasks.count() for u in non_admin)
    total_done_all = sum(u.tasks.filter_by(done=True).count() for u in non_admin)

    users_stats = []
    for u in non_admin:
        u_tasks = u.tasks.all()
        week_start = str(date.today() - timedelta(days=7))
        users_stats.append({
            "username": u.username,
            "fullname": u.fullname,
            "total_tasks": len(u_tasks),
            "done_tasks": sum(1 for t in u_tasks if t.done),
            "today_hours": sum(t.hours for t in u_tasks if t.done and str(t.created_at) == today),
            "week_hours": sum(t.hours for t in u_tasks if t.done and str(t.created_at) >= week_start),
            "total_hours": sum(t.hours for t in u_tasks if t.done),
            "created_at": str(u.created_at),
        })

    all_done_tasks = Task.query.filter_by(done=True).all()
    system_week_hours = {}
    system_month_hours = {}
    for i in range(30):
        day = date.today() - timedelta(days=i)
        day_str = str(day)
        day_total = sum(t.hours for t in all_done_tasks if str(t.created_at) == day_str)
        if i < 7:
            system_week_hours[day_str] = day_total
        if day_total > 0:
            system_month_hours[day_str] = day_total

    admin_user = User.query.filter_by(username="admin").first()
    majors = Major.query.order_by(Major.name).all()

    return render_template(
        "admin.html",
        total_users=total_users,
        total_tasks_all=total_tasks_all,
        total_done_all=total_done_all,
        users_stats=users_stats,
        majors={m.name: {"courses": [c.name for c in m.courses]} for m in majors},
        theme=admin_user.theme,
        system_week_hours=system_week_hours,
        system_month_hours=system_month_hours,
    )


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)
