from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify, send_file
import json
import os
from datetime import datetime, timedelta
from functools import wraps
import io
import shutil

app = Flask(__name__)
app.secret_key = "your-secret-key-change-this-in-production-2026"
DATA_FILE = "data.json"

def get_current_datetime():
    """تاریخ و ساعت فعلی"""
    return datetime.now()

def get_current_date():
    """تاریخ امروز"""
    return datetime.now().date()

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "users": {
                "admin": {
                    "password": "admin",
                    "fullname": "مدیر سیستم",
                    "is_admin": True,
                    "theme": "dark",
                    "can_view_others": True,
                    "tasks": [],
                    "created_at": str(get_current_date())
                }
            },
            "majors": {
                "کامپیوتر": {
                    "courses": [
                        "ساختمان داده", "طراحی الگوریتم", "هوش مصنوعی",
                        "نظریه زبان", "مدار منطقی", "معماری",
                        "سیستم عامل", "شبکه های کامپیوتری", "پایگاه داده",
                        "ریاضی 1", "ریاضی 2", "احتمال", "گسسته"
                    ]
                }
            }
        }
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if "admin" not in data.get("users", {}):
            if "users" not in data:
                data["users"] = {}
            data["users"]["admin"] = {
                "password": "admin",
                "fullname": "مدیر سیستم",
                "is_admin": True,
                "theme": "dark",
                "can_view_others": True,
                "tasks": [],
                "created_at": str(get_current_date())
            }
        for username, user_data in data.get("users", {}).items():
            if "can_view_others" not in user_data:
                user_data["can_view_others"] = True
        if "majors" not in data:
            data["majors"] = {"کامپیوتر": {"courses": ["ساختمان داده"]}}
        return data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        data = load_data()
        if not data["users"].get(session['username'], {}).get('is_admin', False):
            flash("دسترسی غیرمجاز!", "error")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def home():
    if 'username' in session:
        data = load_data()
        if data["users"].get(session['username'], {}).get('is_admin', False):
            return redirect(url_for('admin_panel'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        data = load_data()
        if username in data["users"]:
            if data["users"][username]["password"] == password:
                session["username"] = username
                if data["users"][username].get('is_admin', False):
                    return redirect(url_for('admin_panel'))
                return redirect(url_for('dashboard'))
            else:
                flash("رمز عبور اشتباه است!", "error")
        else:
            flash("کاربر یافت نشد!", "error")
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
        data = load_data()
        if username in data["users"]:
            flash("این نام کاربری قبلاً ثبت شده است!", "error")
        else:
            data["users"][username] = {
                "password": password,
                "fullname": fullname,
                "is_admin": False,
                "theme": "dark",
                "can_view_others": True,
                "tasks": [],
                "created_at": str(get_current_date())
            }
            save_data(data)
            flash("ثبت‌نام با موفقیت انجام شد! وارد شوید.", "success")
            return redirect(url_for('login'))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route("/toggle-theme", methods=["POST"])
@login_required
def toggle_theme():
    data = load_data()
    current_user = session["username"]
    current_theme = data["users"][current_user].get("theme", "dark")
    data["users"][current_user]["theme"] = "light" if current_theme == "dark" else "dark"
    save_data(data)
    return jsonify({"theme": data["users"][current_user]["theme"]})

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    data = load_data()
    current_user = session["username"]
    if data["users"][current_user].get('is_admin', False):
        return redirect(url_for('admin_panel'))
    today = str(get_current_date())
    current_datetime = get_current_datetime()
    
    if request.method == "POST":
        if "new_task" in request.form:
            course = request.form.get("course")
            priority = request.form.get("priority", "medium")
            hours = request.form.get("task_hours", "0")
            description = request.form.get("description", "").strip()
            try:
                hours = float(hours)
            except:
                hours = 0
            if course:
                data["users"][current_user]["tasks"].append({
                    "title": course,
                    "description": description,
                    "done": False,
                    "priority": priority,
                    "hours": hours,
                    "created_at": today
                })
        if "toggle" in request.form:
            idx = int(request.form["toggle"])
            if 0 <= idx < len(data["users"][current_user]["tasks"]):
                data["users"][current_user]["tasks"][idx]["done"] = not data["users"][current_user]["tasks"][idx]["done"]
        if "delete" in request.form:
            idx = int(request.form["delete"])
            if 0 <= idx < len(data["users"][current_user]["tasks"]):
                data["users"][current_user]["tasks"].pop(idx)
        if "edit_idx" in request.form:
            idx = int(request.form["edit_idx"])
            new_course = request.form.get("edit_course")
            new_priority = request.form.get("edit_priority")
            new_hours = request.form.get("edit_hours", "0")
            new_description = request.form.get("edit_description", "")
            try:
                new_hours = float(new_hours)
            except:
                new_hours = 0
            if 0 <= idx < len(data["users"][current_user]["tasks"]) and new_course:
                data["users"][current_user]["tasks"][idx]["title"] = new_course
                data["users"][current_user]["tasks"][idx]["priority"] = new_priority
                data["users"][current_user]["tasks"][idx]["hours"] = new_hours
                data["users"][current_user]["tasks"][idx]["description"] = new_description
        if "new_major" in request.form:
            new_major = request.form.get("new_major", "").strip()
            if new_major and new_major not in data["majors"]:
                data["majors"][new_major] = {"courses": []}
        if "add_course" in request.form:
            major = request.form.get("major_for_course")
            new_course = request.form.get("new_course", "").strip()
            if major in data["majors"] and new_course and new_course not in data["majors"][major]["courses"]:
                data["majors"][major]["courses"].append(new_course)
        if "delete_course" in request.form:
            major = request.form.get("delete_major")
            course = request.form.get("delete_course")
            if major in data["majors"] and course in data["majors"][major]["courses"]:
                data["majors"][major]["courses"].remove(course)
        save_data(data)
        return redirect(url_for('dashboard'))
    
    user_tasks = data["users"][current_user]["tasks"]
    total_done = sum(1 for t in user_tasks if t["done"])
    total_tasks = len(user_tasks)
    today_hours = sum(t.get("hours", 0) for t in user_tasks if t["done"] and t.get("created_at") == today)
    
    week_hours = {}
    for i in range(7):
        day = get_current_date() - timedelta(days=i)
        day_str = str(day)
        day_total = sum(t.get("hours", 0) for t in user_tasks if t["done"] and t.get("created_at") == day_str)
        week_hours[day_str] = day_total
    total_week_hours = sum(week_hours.values())
    
    month_hours = {}
    for i in range(30):
        day = get_current_date() - timedelta(days=i)
        day_str = str(day)
        day_total = sum(t.get("hours", 0) for t in user_tasks if t["done"] and t.get("created_at") == day_str)
        if day_total > 0:
            month_hours[day_str] = day_total
    total_month_hours = sum(month_hours.values())
    
    all_courses = []
    for major_name, major_data in data["majors"].items():
        for course in major_data.get("courses", []):
            if course not in all_courses:
                all_courses.append(course)
    
    course_stats = {}
    for course in all_courses:
        tasks_in_course = [t for t in user_tasks if t.get("title") == course]
        course_stats[course] = {
            "total": len(tasks_in_course),
            "done": sum(1 for t in tasks_in_course if t["done"]),
            "hours": sum(t.get("hours", 0) for t in tasks_in_course if t["done"])
        }
    
    all_users = []
    can_view = data["users"][current_user].get("can_view_others", True)
    if can_view:
        for username, user_data in data["users"].items():
            if user_data.get('is_admin', False):
                continue
            user_total_tasks = len(user_data["tasks"])
            user_done_tasks = sum(1 for t in user_data["tasks"] if t["done"])
            user_today_hours = sum(t.get("hours", 0) for t in user_data["tasks"] if t["done"] and t.get("created_at") == today)
            all_users.append({
                "username": username,
                "fullname": user_data["fullname"],
                "total_tasks": user_total_tasks,
                "done_tasks": user_done_tasks,
                "today_hours": user_today_hours,
                "is_current": username == current_user
            })
    
    theme = data["users"][current_user].get("theme", "dark")
    return render_template("dashboard.html", current_user=current_user, fullname=data["users"][current_user]["fullname"],
        tasks=user_tasks, total_done=total_done, total_tasks=total_tasks, today=today, current_datetime=current_datetime,
        today_hours=today_hours, courses=all_courses, course_stats=course_stats, week_hours=week_hours,
        total_week_hours=total_week_hours, month_hours=month_hours, total_month_hours=total_month_hours,
        all_users=all_users, can_view_others=can_view, theme=theme, majors=data["majors"])

@app.route("/user/<username>")
@login_required
def view_user(username):
    data = load_data()
    current_user = session["username"]
    if not data["users"][current_user].get("can_view_others", True) and username != current_user:
        flash("شما دسترسی مشاهده پروفایل دیگران را ندارید!", "error")
        return redirect(url_for('dashboard'))
    if username not in data["users"]:
        flash("کاربر یافت نشد!", "error")
        return redirect(url_for('dashboard'))
    if data["users"][username].get('is_admin', False):
        flash("کاربر یافت نشد!", "error")
        return redirect(url_for('dashboard'))
    
    user_data = data["users"][username]
    today = str(get_current_date())
    total_done = sum(1 for t in user_data["tasks"] if t["done"])
    total_tasks = len(user_data["tasks"])
    today_hours = sum(t.get("hours", 0) for t in user_data["tasks"] if t["done"] and t.get("created_at") == today)
    
    week_hours = {}
    for i in range(7):
        day = get_current_date() - timedelta(days=i)
        day_str = str(day)
        day_total = sum(t.get("hours", 0) for t in user_data["tasks"] if t["done"] and t.get("created_at") == day_str)
        week_hours[day_str] = day_total
    total_week_hours = sum(week_hours.values())
    
    month_hours = {}
    for i in range(30):
        day = get_current_date() - timedelta(days=i)
        day_str = str(day)
        day_total = sum(t.get("hours", 0) for t in user_data["tasks"] if t["done"] and t.get("created_at") == day_str)
        if day_total > 0:
            month_hours[day_str] = day_total
    total_month_hours = sum(month_hours.values())
    
    all_courses = []
    for major_name, major_data in data["majors"].items():
        for course in major_data.get("courses", []):
            if course not in all_courses:
                all_courses.append(course)
    
    course_stats = {}
    for course in all_courses:
        tasks_in_course = [t for t in user_data["tasks"] if t.get("title") == course]
        course_stats[course] = {
            "total": len(tasks_in_course),
            "done": sum(1 for t in tasks_in_course if t["done"]),
            "hours": sum(t.get("hours", 0) for t in tasks_in_course if t["done"])
        }
    
    theme = data["users"][current_user].get("theme", "dark")
    return render_template("view_user.html", viewed_user=username, fullname=user_data["fullname"], tasks=user_data["tasks"],
        total_done=total_done, total_tasks=total_tasks, today=today, today_hours=today_hours, courses=all_courses,
        course_stats=course_stats, week_hours=week_hours, total_week_hours=total_week_hours, month_hours=month_hours,
        total_month_hours=total_month_hours, is_own_profile=(username == current_user), theme=theme)

@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin_panel():
    data = load_data()
    today = str(get_current_date())
    current_datetime = get_current_datetime()
    
    if request.method == "POST":
        if "delete_user" in request.form:
            username = request.form.get("delete_user")
            if username != "admin" and username in data["users"]:
                del data["users"][username]
        if "change_password" in request.form:
            username = request.form.get("change_password")
            new_password = request.form.get("new_password")
            if username in data["users"] and new_password:
                data["users"][username]["password"] = new_password
        if "toggle_view_permission" in request.form:
            username = request.form.get("toggle_view_permission")
            if username in data["users"] and username != "admin":
                current_permission = data["users"][username].get("can_view_others", True)
                data["users"][username]["can_view_others"] = not current_permission
        if "delete_major" in request.form:
            major = request.form.get("delete_major")
            if major != "کامپیوتر" and major in data["majors"]:
                del data["majors"][major]
        if "add_major" in request.form:
            new_major = request.form.get("new_major", "").strip()
            if new_major and new_major not in data["majors"]:
                data["majors"][new_major] = {"courses": []}
        if "add_course" in request.form:
            major = request.form.get("major_for_course")
            new_course = request.form.get("new_course", "").strip()
            if major in data["majors"] and new_course and new_course not in data["majors"][major]["courses"]:
                data["majors"][major]["courses"].append(new_course)
        if "delete_course" in request.form:
            major = request.form.get("course_major")
            course = request.form.get("delete_course")
            if major in data["majors"] and course in data["majors"][major]["courses"]:
                data["majors"][major]["courses"].remove(course)
        save_data(data)
        return redirect(url_for('admin_panel'))
    
    total_users = len([u for u in data["users"].values() if not u.get('is_admin', False)])
    total_tasks_all = sum(len(u["tasks"]) for u in data["users"].values() if not u.get('is_admin', False))
    total_done_all = sum(sum(1 for t in u["tasks"] if t["done"]) for u in data["users"].values() if not u.get('is_admin', False))
    
    users_stats = []
    for username, user_data in data["users"].items():
        if user_data.get('is_admin', False):
            continue
        total_tasks = len(user_data["tasks"])
        done_tasks = sum(1 for t in user_data["tasks"] if t["done"])
        today_hours = sum(t.get("hours", 0) for t in user_data["tasks"] if t["done"] and t.get("created_at") == today)
        total_hours = sum(t.get("hours", 0) for t in user_data["tasks"] if t["done"])
        week_total = 0
        for i in range(7):
            day = get_current_date() - timedelta(days=i)
            day_str = str(day)
            week_total += sum(t.get("hours", 0) for t in user_data["tasks"] if t["done"] and t.get("created_at") == day_str)
        users_stats.append({
            "username": username, "fullname": user_data["fullname"], "total_tasks": total_tasks,
            "done_tasks": done_tasks, "today_hours": today_hours, "week_hours": week_total,
            "total_hours": total_hours, "created_at": user_data.get("created_at", "نامشخص"),
            "can_view_others": user_data.get("can_view_others", True)
        })
    
    system_week_hours = {}
    for i in range(7):
        day = get_current_date() - timedelta(days=i)
        day_str = str(day)
        day_total = sum(sum(t.get("hours", 0) for t in u["tasks"] if t["done"] and t.get("created_at") == day_str)
                       for u in data["users"].values() if not u.get('is_admin', False))
        system_week_hours[day_str] = day_total
    
    system_month_hours = {}
    for i in range(30):
        day = get_current_date() - timedelta(days=i)
        day_str = str(day)
        day_total = sum(sum(t.get("hours", 0) for t in u["tasks"] if t["done"] and t.get("created_at") == day_str)
                       for u in data["users"].values() if not u.get('is_admin', False))
        if day_total > 0:
            system_month_hours[day_str] = day_total
    
    theme = data["users"]["admin"].get("theme", "dark")
    return render_template("admin.html", total_users=total_users, total_tasks_all=total_tasks_all,
        total_done_all=total_done_all, users_stats=users_stats, majors=data["majors"], theme=theme,
        system_week_hours=system_week_hours, system_month_hours=system_month_hours, current_datetime=current_datetime)

@app.route("/admin/export")
@admin_required
def export_data():
    data = load_data()
    filename = f"study_planner_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_str = json.dumps(data, indent=4, ensure_ascii=False)
    mem_file = io.BytesIO(json_str.encode('utf-8'))
    mem_file.seek(0)
    return send_file(mem_file, mimetype='application/json', as_attachment=True, download_name=filename)

@app.route("/admin/import", methods=["POST"])
@admin_required
def import_data():
    if 'json_file' not in request.files:
        flash("فایلی انتخاب نشده است!", "error")
        return redirect(url_for('admin_panel'))
    file = request.files['json_file']
    if file.filename == '' or not file.filename.endswith('.json'):
        flash("فقط فایل‌های JSON قابل قبول هستند!", "error")
        return redirect(url_for('admin_panel'))
    try:
        file_content = file.read().decode('utf-8')
        new_data = json.loads(file_content)
        if "users" not in new_data or "majors" not in new_data:
            flash("ساختار فایل نامعتبر است!", "error")
            return redirect(url_for('admin_panel'))
        backup_name = f"data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        if os.path.exists(DATA_FILE):
            shutil.copy(DATA_FILE, backup_name)
        save_data(new_data)
        flash(f"داده‌ها با موفقیت ایمپورت شد! بکاپ: {backup_name}", "success")
    except Exception as e:
        flash(f"خطا در ایمپورت: {str(e)}", "error")
    return redirect(url_for('admin_panel'))

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
