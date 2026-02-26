from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
from datetime import date, timedelta
from functools import wraps
from translator import auto_translate, detect_language, is_available as translator_available

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-in-production")

# ─── Database ────────────────────────────────────────────────────────────────
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/study_planner"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# ─── i18n ────────────────────────────────────────────────────────────────────
SUPPORTED_LANGS = ["fa", "en"]
DEFAULT_LANG = "fa"
_locale_cache: dict = {}

def load_locale(lang: str) -> dict:
    if lang not in _locale_cache:
        path = os.path.join(os.path.dirname(__file__), "locales", f"{lang}.json")
        with open(path, "r", encoding="utf-8") as f:
            _locale_cache[lang] = json.load(f)
    return _locale_cache[lang]

def get_lang() -> str:
    return session.get("lang", DEFAULT_LANG)

def t(key: str, **kwargs) -> str:
    """
    ترجمه یک کلید با فرمت 'section.key'
    مثال: t('auth.login_btn')  یا  t('dashboard.greeting', name='Ali')
    """
    locale = load_locale(get_lang())
    parts = key.split(".")
    value = locale
    for part in parts:
        value = value.get(part, key) if isinstance(value, dict) else key
    if isinstance(value, str) and kwargs:
        value = value.format(**kwargs)
    return value

# تزریق t و lang به همه templateها
@app.context_processor
def inject_i18n():
    lang = get_lang()
    locale = load_locale(lang)
    return {
        "t": t,
        "lang": lang,
        "dir": locale.get("dir", "rtl"),
        "supported_langs": SUPPORTED_LANGS,
        "translator_available": translator_available(),
    }

@app.route("/set-lang/<lang>")
def set_lang(lang):
    if lang in SUPPORTED_LANGS:
        session["lang"] = lang
    return redirect(request.referrer or url_for("home"))


# ─── Models ───────────────────────────────────────────────────────────────────

class User(db.Model):
    __tablename__ = "users"
    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password   = db.Column(db.String(255), nullable=False)
    fullname   = db.Column(db.String(150), nullable=False)
    is_admin   = db.Column(db.Boolean, default=False, nullable=False)
    theme      = db.Column(db.String(10), default="dark", nullable=False)
    created_at = db.Column(db.Date, default=date.today, nullable=False)
    tasks      = db.relationship("Task", back_populates="user",
                                 cascade="all, delete-orphan", lazy="dynamic")


class Major(db.Model):
    __tablename__ = "majors"
    id      = db.Column(db.Integer, primary_key=True)
    # کلید slug انگلیسی — مثلاً "computer_science"
    key     = db.Column(db.String(100), unique=True, nullable=False)
    # نام فارسی و انگلیسی برای نمایش
    name_fa = db.Column(db.String(150), nullable=False)
    name_en = db.Column(db.String(150), nullable=False)
    courses = db.relationship("Course", back_populates="major",
                              cascade="all, delete-orphan", lazy="dynamic")

    def display_name(self):
        return self.name_fa if get_lang() == "fa" else self.name_en


class Course(db.Model):
    __tablename__ = "courses"
    id       = db.Column(db.Integer, primary_key=True)
    key      = db.Column(db.String(100), nullable=False)   # slug انگلیسی
    name_fa  = db.Column(db.String(150), nullable=False)
    name_en  = db.Column(db.String(150), nullable=False)
    major_id = db.Column(db.Integer, db.ForeignKey("majors.id"), nullable=False)
    major    = db.relationship("Major", back_populates="courses")

    __table_args__ = (db.UniqueConstraint("key", "major_id", name="uq_course_major"),)

    def display_name(self):
        return self.name_fa if get_lang() == "fa" else self.name_en


class Task(db.Model):
    __tablename__ = "tasks"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # کلید درس (course.key) برای نگهداری مستقل از زبان
    course_key  = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default="")
    done        = db.Column(db.Boolean, default=False, nullable=False)
    priority    = db.Column(db.String(10), default="medium", nullable=False)
    hours       = db.Column(db.Float, default=0.0, nullable=False)
    created_at  = db.Column(db.Date, default=date.today, nullable=False)
    user        = db.relationship("User", back_populates="tasks")

    def display_title(self):
        """نام درس رو بر اساس زبان جاری برمی‌گردونه"""
        course = Course.query.filter_by(key=self.course_key).first()
        if course:
            return course.display_name()
        return self.course_key


# ─── Seed Data ────────────────────────────────────────────────────────────────

DEFAULT_DATA = {
    "majors": [
        {
            "key": "computer_science",
            "name_fa": "مهندسی کامپیوتر",
            "name_en": "Computer Science",
            "courses": [
                {"key": "data_structures",        "name_fa": "ساختمان داده",        "name_en": "Data Structures"},
                {"key": "algorithms",             "name_fa": "طراحی الگوریتم",      "name_en": "Algorithm Design"},
                {"key": "artificial_intelligence","name_fa": "هوش مصنوعی",          "name_en": "Artificial Intelligence"},
                {"key": "theory_of_languages",    "name_fa": "نظریه زبان",          "name_en": "Theory of Languages"},
                {"key": "logic_circuits",         "name_fa": "مدار منطقی",          "name_en": "Logic Circuits"},
                {"key": "computer_architecture",  "name_fa": "معماری کامپیوتر",     "name_en": "Computer Architecture"},
                {"key": "operating_systems",      "name_fa": "سیستم عامل",          "name_en": "Operating Systems"},
                {"key": "computer_networks",      "name_fa": "شبکه‌های کامپیوتری",  "name_en": "Computer Networks"},
                {"key": "database",               "name_fa": "پایگاه داده",         "name_en": "Database"},
                {"key": "math1",                  "name_fa": "ریاضی ۱",             "name_en": "Mathematics 1"},
                {"key": "math2",                  "name_fa": "ریاضی ۲",             "name_en": "Mathematics 2"},
                {"key": "probability",            "name_fa": "احتمال",              "name_en": "Probability"},
                {"key": "discrete_math",          "name_fa": "ریاضی گسسته",         "name_en": "Discrete Mathematics"},
            ]
        }
    ]
}

def seed_db():
    """داده‌های اولیه رو اگه وجود نداشتن وارد می‌کنه"""
    db.create_all()

    # ادمین پیش‌فرض
    if not User.query.filter_by(username="admin").first():
        db.session.add(User(
            username="admin",
            password=generate_password_hash("admin"),
            fullname="Admin",
            is_admin=True,
            theme="dark"
        ))

    # رشته‌ها و دروس پیش‌فرض
    for major_data in DEFAULT_DATA["majors"]:
        major = Major.query.filter_by(key=major_data["key"]).first()
        if not major:
            major = Major(key=major_data["key"],
                          name_fa=major_data["name_fa"],
                          name_en=major_data["name_en"])
            db.session.add(major)
            db.session.flush()

        for course_data in major_data["courses"]:
            if not Course.query.filter_by(key=course_data["key"], major_id=major.id).first():
                db.session.add(Course(
                    key=course_data["key"],
                    name_fa=course_data["name_fa"],
                    name_en=course_data["name_en"],
                    major_id=major.id
                ))

    db.session.commit()


# ─── Decorators ───────────────────────────────────────────────────────────────

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
            flash(t("admin.unauthorized"), "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_user_stats(user):
    today     = date.today()
    today_str = str(today)
    tasks     = user.tasks.all()

    total_tasks  = len(tasks)
    total_done   = sum(1 for t in tasks if t.done)
    today_hours  = sum(t.hours for t in tasks if t.done and str(t.created_at) == today_str)

    week_hours = {}
    for i in range(7):
        d = today - timedelta(days=i)
        ds = str(d)
        week_hours[ds] = sum(t.hours for t in tasks if t.done and str(t.created_at) == ds)
    total_week_hours = sum(week_hours.values())

    month_hours = {}
    for i in range(30):
        d = today - timedelta(days=i)
        ds = str(d)
        v = sum(t.hours for t in tasks if t.done and str(t.created_at) == ds)
        if v > 0:
            month_hours[ds] = v
    total_month_hours = sum(month_hours.values())

    return dict(
        tasks=tasks, total_tasks=total_tasks, total_done=total_done,
        today_hours=today_hours,
        week_hours=week_hours, total_week_hours=total_week_hours,
        month_hours=month_hours, total_month_hours=total_month_hours,
    )

def all_courses_list():
    """لیست همه دروس با display_name بر اساس زبان جاری"""
    courses = Course.query.join(Major).order_by(Major.name_en, Course.name_en).all()
    seen, result = set(), []
    for c in courses:
        if c.key not in seen:
            seen.add(c.key)
            result.append({"key": c.key, "name": c.display_name()})
    return result

def course_stats(tasks, courses):
    stats = {}
    for c in courses:
        ct = [tk for tk in tasks if tk.course_key == c["key"]]
        stats[c["key"]] = {
            "name":  c["name"],
            "total": len(ct),
            "done":  sum(1 for tk in ct if tk.done),
            "hours": sum(tk.hours for tk in ct if tk.done),
        }
    return stats

def majors_for_template():
    majors = Major.query.order_by(Major.name_en).all()
    return [
        {
            "key":     m.key,
            "name":    m.display_name(),
            "courses": [{"key": c.key, "name": c.display_name()} for c in m.courses],
        }
        for m in majors
    ]


# ─── Routes ───────────────────────────────────────────────────────────────────

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
        if user and check_password_hash(user.password, password):
            session["username"] = username
            return redirect(url_for("admin_panel") if user.is_admin else url_for("dashboard"))
        flash(t("auth.invalid_credentials"), "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        fullname = request.form.get("fullname", "").strip()
        if not username or not password or not fullname:
            flash(t("auth.fill_all_fields"), "error")
            return render_template("register.html")
        if User.query.filter_by(username=username).first():
            flash(t("auth.username_taken"), "error")
        else:
            db.session.add(User(
                username=username,
                password=generate_password_hash(password),
                fullname=fullname
            ))
            db.session.commit()
            flash(t("auth.register_success"), "success")
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
        action = request.form.get("action")

        if action == "new_task":
            course_key = request.form.get("course_key")
            priority   = request.form.get("priority", "medium")
            desc       = request.form.get("description", "").strip()
            try:
                hours = float(request.form.get("task_hours", "0"))
            except ValueError:
                hours = 0.0
            if course_key:
                db.session.add(Task(
                    user_id=user.id, course_key=course_key,
                    description=desc, priority=priority, hours=hours
                ))

        elif action == "toggle":
            task = db.session.get(Task, int(request.form.get("task_id", 0)))
            if task and task.user_id == user.id:
                task.done = not task.done

        elif action == "delete":
            task = db.session.get(Task, int(request.form.get("task_id", 0)))
            if task and task.user_id == user.id:
                db.session.delete(task)

        elif action == "edit":
            task = db.session.get(Task, int(request.form.get("task_id", 0)))
            if task and task.user_id == user.id:
                new_key = request.form.get("course_key")
                if new_key:
                    task.course_key  = new_key
                    task.priority    = request.form.get("priority", task.priority)
                    task.description = request.form.get("description", "")
                    try:
                        task.hours = float(request.form.get("task_hours", "0"))
                    except ValueError:
                        pass

        elif action == "add_major":
            name_fa = request.form.get("name_fa", "").strip()
            name_en = request.form.get("name_en", "").strip()
            if name_fa and name_en:
                key = name_en.lower().replace(" ", "_")
                if not Major.query.filter_by(key=key).first():
                    db.session.add(Major(key=key, name_fa=name_fa, name_en=name_en))

        elif action == "add_course":
            major_key = request.form.get("major_key")
            name_fa   = request.form.get("name_fa", "").strip()
            name_en   = request.form.get("name_en", "").strip()
            major     = Major.query.filter_by(key=major_key).first()
            if major and name_fa and name_en:
                key = name_en.lower().replace(" ", "_")
                if not Course.query.filter_by(key=key, major_id=major.id).first():
                    db.session.add(Course(key=key, name_fa=name_fa, name_en=name_en, major_id=major.id))

        elif action == "delete_course":
            course = db.session.get(Course, int(request.form.get("course_id", 0)))
            if course:
                db.session.delete(course)

        db.session.commit()
        return redirect(url_for("dashboard"))

    stats    = get_user_stats(user)
    courses  = all_courses_list()
    cstats   = course_stats(stats["tasks"], courses)
    majors   = majors_for_template()

    all_users_data = []
    for u in User.query.filter_by(is_admin=False).all():
        u_tasks = u.tasks.all()
        all_users_data.append({
            "username":    u.username,
            "fullname":    u.fullname,
            "total_tasks": len(u_tasks),
            "done_tasks":  sum(1 for tk in u_tasks if tk.done),
            "today_hours": sum(tk.hours for tk in u_tasks if tk.done and str(tk.created_at) == today),
            "is_current":  u.username == user.username,
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
        courses=courses,
        course_stats=cstats,
        week_hours=stats["week_hours"],
        total_week_hours=stats["total_week_hours"],
        month_hours=stats["month_hours"],
        total_month_hours=stats["total_month_hours"],
        all_users=all_users_data,
        theme=user.theme,
        majors=majors,
    )


@app.route("/user/<username>")
@login_required
def view_user(username):
    current = User.query.filter_by(username=session["username"]).first()
    target  = User.query.filter_by(username=username).first()
    if not target or target.is_admin:
        flash(t("admin.unauthorized"), "error")
        return redirect(url_for("dashboard"))

    today   = str(date.today())
    stats   = get_user_stats(target)
    courses = all_courses_list()
    cstats  = course_stats(stats["tasks"], courses)

    return render_template(
        "view_user.html",
        viewed_user=target.username,
        fullname=target.fullname,
        tasks=stats["tasks"],
        total_done=stats["total_done"],
        total_tasks=stats["total_tasks"],
        today=today,
        today_hours=stats["today_hours"],
        courses=courses,
        course_stats=cstats,
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
        action = request.form.get("action")

        if action == "delete_user":
            uname = request.form.get("username")
            if uname != "admin":
                u = User.query.filter_by(username=uname).first()
                if u:
                    db.session.delete(u)

        elif action == "change_password":
            u      = User.query.filter_by(username=request.form.get("username")).first()
            new_pw = request.form.get("new_password", "").strip()
            if u and new_pw:
                u.password = generate_password_hash(new_pw)

        elif action == "add_major":
            name_fa = request.form.get("name_fa", "").strip()
            name_en = request.form.get("name_en", "").strip()
            if name_fa and name_en:
                key = name_en.lower().replace(" ", "_")
                if not Major.query.filter_by(key=key).first():
                    db.session.add(Major(key=key, name_fa=name_fa, name_en=name_en))

        elif action == "delete_major":
            major = db.session.get(Major, int(request.form.get("major_id", 0)))
            if major and major.key != "computer_science":
                db.session.delete(major)

        elif action == "add_course":
            major_key = request.form.get("major_key")
            name_fa   = request.form.get("name_fa", "").strip()
            name_en   = request.form.get("name_en", "").strip()
            major     = Major.query.filter_by(key=major_key).first()
            if major and name_fa and name_en:
                key = name_en.lower().replace(" ", "_")
                if not Course.query.filter_by(key=key, major_id=major.id).first():
                    db.session.add(Course(key=key, name_fa=name_fa, name_en=name_en, major_id=major.id))

        elif action == "delete_course":
            course = db.session.get(Course, int(request.form.get("course_id", 0)))
            if course:
                db.session.delete(course)

        db.session.commit()
        return redirect(url_for("admin_panel"))

    non_admin      = User.query.filter_by(is_admin=False).all()
    total_users    = len(non_admin)
    total_tasks_all = sum(u.tasks.count() for u in non_admin)
    total_done_all  = sum(u.tasks.filter_by(done=True).count() for u in non_admin)

    users_stats = []
    week_start  = str(date.today() - timedelta(days=7))
    for u in non_admin:
        u_tasks = u.tasks.all()
        users_stats.append({
            "username":   u.username,
            "fullname":   u.fullname,
            "total_tasks": len(u_tasks),
            "done_tasks":  sum(1 for tk in u_tasks if tk.done),
            "today_hours": sum(tk.hours for tk in u_tasks if tk.done and str(tk.created_at) == today),
            "week_hours":  sum(tk.hours for tk in u_tasks if tk.done and str(tk.created_at) >= week_start),
            "total_hours": sum(tk.hours for tk in u_tasks if tk.done),
            "created_at":  str(u.created_at),
        })

    all_done = Task.query.filter_by(done=True).all()
    system_week_hours  = {}
    system_month_hours = {}
    for i in range(30):
        d  = date.today() - timedelta(days=i)
        ds = str(d)
        v  = sum(tk.hours for tk in all_done if str(tk.created_at) == ds)
        if i < 7:
            system_week_hours[ds] = v
        if v > 0:
            system_month_hours[ds] = v

    admin_user = User.query.filter_by(username="admin").first()

    return render_template(
        "admin.html",
        total_users=total_users,
        total_tasks_all=total_tasks_all,
        total_done_all=total_done_all,
        users_stats=users_stats,
        majors=majors_for_template(),
        theme=admin_user.theme,
        system_week_hours=system_week_hours,
        system_month_hours=system_month_hours,
    )



# ─── Translation API ──────────────────────────────────────────────────────────

@app.route("/api/translate", methods=["POST"])
@login_required
def api_translate():
    """
    API endpoint برای ترجمه خودکار در فرم‌ها.
    Input:  {"text": "..."}
    Output: {"fa": "...", "en": "...", "detected": "fa/en", "success": true/false}
    """
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "متن خالی است"}), 400

    result = auto_translate(text)
    return jsonify(result)


@app.route("/api/translator-status")
def api_translator_status():
    """بررسی وضعیت LibreTranslate"""
    available = translator_available()
    return jsonify({"available": available})


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    with app.app_context():
        seed_db()
    app.run(debug=True)
