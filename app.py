from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
import json
import os
from datetime import date, datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = "your-secret-key-change-this-in-production"
DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "users": {
                "admin": {
                    "password": "admin",
                    "fullname": "مدیر سیستم",
                    "is_admin": True,
                    "theme": "dark",
                    "tasks": [],
                    "created_at": str(date.today())
                }
            },
            "majors": {
                "کامپیوتر": {
                    "courses": [
                        "ساختمان داده",
                        "طراحی الگوریتم",
                        "هوش مصنوعی",
                        "نظریه زبان",
                        "مدار منطقی",
                        "معماری",
                        "سیستم عامل",
                        "شبکه های کامپیوتری",
                        "پایگاه داده",
                        "ریاضی 1",
                        "ریاضی 2",
                        "احتمال",
                        "گسسته"
                    ]
                }
            }
        }
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        # اطمینان از وجود ادمین
        if "admin" not in data["users"]:
            data["users"]["admin"] = {
                "password": "admin",
                "fullname": "مدیر سیستم",
                "is_admin": True,
                "theme": "dark",
                "tasks": [],
                "created_at": str(date.today())
            }
        # اطمینان از وجود majors
        if "majors" not in data:
            data["majors"] = {
                "کامپیوتر": {
                    "courses": [
                        "ساختمان داده",
                        "طراحی الگوریتم",
                        "هوش مصنوعی",
                        "نظریه زبان",
                        "مدار منطقی",
                        "معماری",
                        "سیستم عامل",
                        "شبکه های کامپیوتری",
                        "پایگاه داده",
                        "ریاضی 1",
                        "ریاضی 2",
                        "احتمال",
                        "گسسته"
                    ]
                }
            }
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
                # ادمین به پنل ادمین میره
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
                "tasks": [],
                "created_at": str(date.today())
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
    
    # جلوگیری از دسترسی ادمین به داشبورد معمولی
    if data["users"][current_user].get('is_admin', False):
        return redirect(url_for('admin_panel'))
    
    today = str(date.today())
    
    if request.method == "POST":
        # افزودن تسک جدید
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
        
        # تغییر وضعیت تسک
        if "toggle" in request.form:
            idx = int(request.form["toggle"])
            if 0 <= idx < len(data["users"][current_user]["tasks"]):
                data["users"][current_user]["tasks"][idx]["done"] = not data["users"][current_user]["tasks"][idx]["done"]
        
        # حذف تسک
        if "delete" in request.form:
            idx = int(request.form["delete"])
            if 0 <= idx < len(data["users"][current_user]["tasks"]):
                data["users"][current_user]["tasks"].pop(idx)
        
        # ویرایش تسک
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
        
        # افزودن رشته جدید
        if "new_major" in request.form:
            new_major = request.form.get("new_major", "").strip()
            if new_major and new_major not in data["majors"]:
                data["majors"][new_major] = {"courses": []}
        
        # افزودن درس به رشته
        if "add_course" in request.form:
            major = request.form.get("major_for_course")
            new_course = request.form.get("new_course", "").strip()
            if major in data["majors"] and new_course and new_course not in data["majors"][major]["courses"]:
                data["majors"][major]["courses"].append(new_course)
        
        # حذف درس از رشته
        if "delete_course" in request.form:
            major = request.form.get("delete_major")
            course = request.form.get("delete_course")
            if major in data["majors"] and course in data["majors"][major]["courses"]:
                data["majors"][major]["courses"].remove(course)
        
        save_data(data)
        return redirect(url_for('dashboard'))
    
    # محاسبه آمار
    user_tasks = data["users"][current_user]["tasks"]
    total_done = sum(1 for t in user_tasks if t["done"])
    total_tasks = len(user_tasks)
    
    today_hours = sum(t.get("hours", 0) for t in user_tasks if t["done"] and t.get("created_at") == today)
    
    week_hours = {}
    for i in range(7):
        day = date.today() - timedelta(days=i)
        day_str = str(day)
        day_total = sum(t.get("hours", 0) for t in user_tasks if t["done"] and t.get("created_at") == day_str)
        week_hours[day_str] = day_total
    
    total_week_hours = sum(week_hours.values())
    
    # محاسبه ساعات ماهانه
    month_hours = {}
    for i in range(30):
        day = date.today() - timedelta(days=i)
        day_str = str(day)
        day_total = sum(t.get("hours", 0) for t in user_tasks if t["done"] and t.get("created_at") == day_str)
        if day_total > 0:
            month_hours[day_str] = day_total
    
    total_month_hours = sum(month_hours.values())
    
    # جمع‌آوری همه دروس از همه رشته‌ها
    all_courses = []
    for major_name, major_data in data["majors"].items():
        for course in major_data.get("courses", []):
            if course not in all_courses:
                all_courses.append(course)
    
    # آمار دروس
    course_stats = {}
    for course in all_courses:
        tasks_in_course = [t for t in user_tasks if t.get("title") == course]
        course_stats[course] = {
            "total": len(tasks_in_course),
            "done": sum(1 for t in tasks_in_course if t["done"]),
            "hours": sum(t.get("hours", 0) for t in tasks_in_course if t["done"])
        }
    
    # لیست کاربران (بدون ادمین)
    all_users = []
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
    
    return render_template(
        "dashboard.html",
        current_user=current_user,
        fullname=data["users"][current_user]["fullname"],
        tasks=user_tasks,
        total_done=total_done,
        total_tasks=total_tasks,
        today=today,
        today_hours=today_hours,
        courses=all_courses,
        course_stats=course_stats,
        week_hours=week_hours,
        total_week_hours=total_week_hours,
        month_hours=month_hours,
        total_month_hours=total_month_hours,
        all_users=all_users,
        theme=theme,
        majors=data["majors"]
    )

@app.route("/user/<username>")
@login_required
def view_user(username):
    data = load_data()
    current_user = session["username"]
    
    if username not in data["users"]:
        flash("کاربر یافت نشد!", "error")
        return redirect(url_for('dashboard'))
    
    # جلوگیری از مشاهده ادمین
    if data["users"][username].get('is_admin', False):
        flash("کاربر یافت نشد!", "error")
        return redirect(url_for('dashboard'))
    
    user_data = data["users"][username]
    today = str(date.today())
    
    total_done = sum(1 for t in user_data["tasks"] if t["done"])
    total_tasks = len(user_data["tasks"])
    today_hours = sum(t.get("hours", 0) for t in user_data["tasks"] if t["done"] and t.get("created_at") == today)
    
    week_hours = {}
    for i in range(7):
        day = date.today() - timedelta(days=i)
        day_str = str(day)
        day_total = sum(t.get("hours", 0) for t in user_data["tasks"] if t["done"] and t.get("created_at") == day_str)
        week_hours[day_str] = day_total
    
    total_week_hours = sum(week_hours.values())
    
    # محاسبه ساعات ماهانه
    month_hours = {}
    for i in range(30):
        day = date.today() - timedelta(days=i)
        day_str = str(day)
        day_total = sum(t.get("hours", 0) for t in user_data["tasks"] if t["done"] and t.get("created_at") == day_str)
        if day_total > 0:
            month_hours[day_str] = day_total
    
    total_month_hours = sum(month_hours.values())
    
    # جمع‌آوری همه دروس
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
    
    return render_template(
        "view_user.html",
        viewed_user=username,
        fullname=user_data["fullname"],
        tasks=user_data["tasks"],
        total_done=total_done,
        total_tasks=total_tasks,
        today=today,
        today_hours=today_hours,
        courses=all_courses,
        course_stats=course_stats,
        week_hours=week_hours,
        total_week_hours=total_week_hours,
        month_hours=month_hours,
        total_month_hours=total_month_hours,
        is_own_profile=(username == current_user),
        theme=theme
    )

@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin_panel():
    data = load_data()
    today = str(date.today())
    
    if request.method == "POST":
        # حذف کاربر
        if "delete_user" in request.form:
            username = request.form.get("delete_user")
            if username != "admin" and username in data["users"]:
                del data["users"][username]
        
        # تغییر رمز کاربر
        if "change_password" in request.form:
            username = request.form.get("change_password")
            new_password = request.form.get("new_password")
            if username in data["users"] and new_password:
                data["users"][username]["password"] = new_password
        
        # حذف رشته
        if "delete_major" in request.form:
            major = request.form.get("delete_major")
            if major != "کامپیوتر" and major in data["majors"]:
                del data["majors"][major]
        
        # افزودن رشته
        if "add_major" in request.form:
            new_major = request.form.get("new_major", "").strip()
            if new_major and new_major not in data["majors"]:
                data["majors"][new_major] = {"courses": []}
        
        # افزودن درس
        if "add_course" in request.form:
            major = request.form.get("major_for_course")
            new_course = request.form.get("new_course", "").strip()
            if major in data["majors"] and new_course and new_course not in data["majors"][major]["courses"]:
                data["majors"][major]["courses"].append(new_course)
        
        # حذف درس
        if "delete_course" in request.form:
            major = request.form.get("course_major")
            course = request.form.get("delete_course")
            if major in data["majors"] and course in data["majors"][major]["courses"]:
                data["majors"][major]["courses"].remove(course)
        
        save_data(data)
        return redirect(url_for('admin_panel'))
    
    # آمار کلی
    total_users = len([u for u in data["users"].values() if not u.get('is_admin', False)])
    total_tasks_all = sum(len(u["tasks"]) for u in data["users"].values() if not u.get('is_admin', False))
    total_done_all = sum(sum(1 for t in u["tasks"] if t["done"]) for u in data["users"].values() if not u.get('is_admin', False))
    
    # آمار کاربران
    users_stats = []
    for username, user_data in data["users"].items():
        if user_data.get('is_admin', False):
            continue
        
        total_tasks = len(user_data["tasks"])
        done_tasks = sum(1 for t in user_data["tasks"] if t["done"])
        today_hours = sum(t.get("hours", 0) for t in user_data["tasks"] if t["done"] and t.get("created_at") == today)
        total_hours = sum(t.get("hours", 0) for t in user_data["tasks"] if t["done"])
        
        # محاسبه ساعات هفتگی
        week_total = 0
        for i in range(7):
            day = date.today() - timedelta(days=i)
            day_str = str(day)
            week_total += sum(t.get("hours", 0) for t in user_data["tasks"] if t["done"] and t.get("created_at") == day_str)
        
        users_stats.append({
            "username": username,
            "fullname": user_data["fullname"],
            "total_tasks": total_tasks,
            "done_tasks": done_tasks,
            "today_hours": today_hours,
            "week_hours": week_total,
            "total_hours": total_hours,
            "created_at": user_data.get("created_at", "نامشخص")
        })
    
    # آمار کلی سیستم برای نمودار
    system_week_hours = {}
    for i in range(7):
        day = date.today() - timedelta(days=i)
        day_str = str(day)
        day_total = 0
        for username, user_data in data["users"].items():
            if not user_data.get('is_admin', False):
                day_total += sum(t.get("hours", 0) for t in user_data["tasks"] if t["done"] and t.get("created_at") == day_str)
        system_week_hours[day_str] = day_total
    
    system_month_hours = {}
    for i in range(30):
        day = date.today() - timedelta(days=i)
        day_str = str(day)
        day_total = 0
        for username, user_data in data["users"].items():
            if not user_data.get('is_admin', False):
                day_total += sum(t.get("hours", 0) for t in user_data["tasks"] if t["done"] and t.get("created_at") == day_str)
        if day_total > 0:
            system_month_hours[day_str] = day_total
    
    theme = data["users"]["admin"].get("theme", "dark")
    
    return render_template(
        "admin.html",
        total_users=total_users,
        total_tasks_all=total_tasks_all,
        total_done_all=total_done_all,
        users_stats=users_stats,
        majors=data["majors"],
        theme=theme,
        system_week_hours=system_week_hours,
        system_month_hours=system_month_hours
    )

if __name__ == "__main__":
    app.run(debug=True)
