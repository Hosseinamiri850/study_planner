from flask import Flask, render_template, request, redirect, session, flash, url_for
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
            "users": {},
            "categories": [
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
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if "categories" not in data:
            data["categories"] = [
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

@app.route("/")
def home():
    if 'username' in session:
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

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    data = load_data()
    current_user = session["username"]
    today = str(date.today())
    
    if request.method == "POST":
        # فقط کاربر خودش می‌تونه تسک اضافه کنه
        if "new_task" in request.form:
            task = request.form.get("new_task", "").strip()
            category = request.form.get("category", "سایر")
            priority = request.form.get("priority", "medium")
            hours = request.form.get("task_hours", "0")
            
            try:
                hours = float(hours)
            except:
                hours = 0
            
            if task:
                data["users"][current_user]["tasks"].append({
                    "title": task,
                    "done": False,
                    "category": category,
                    "priority": priority,
                    "hours": hours,
                    "created_at": today
                })
        
        # تغییر وضعیت تسک (فقط تسک‌های خودش)
        if "toggle" in request.form:
            idx = int(request.form["toggle"])
            if 0 <= idx < len(data["users"][current_user]["tasks"]):
                data["users"][current_user]["tasks"][idx]["done"] = not data["users"][current_user]["tasks"][idx]["done"]
        
        # حذف تسک (فقط تسک‌های خودش)
        if "delete" in request.form:
            idx = int(request.form["delete"])
            if 0 <= idx < len(data["users"][current_user]["tasks"]):
                data["users"][current_user]["tasks"].pop(idx)
        
        # ویرایش تسک (فقط تسک‌های خودش)
        if "edit_idx" in request.form:
            idx = int(request.form["edit_idx"])
            new_title = request.form.get("edit_title", "").strip()
            new_category = request.form.get("edit_category")
            new_priority = request.form.get("edit_priority")
            new_hours = request.form.get("edit_hours", "0")
            
            try:
                new_hours = float(new_hours)
            except:
                new_hours = 0
            
            if 0 <= idx < len(data["users"][current_user]["tasks"]) and new_title:
                data["users"][current_user]["tasks"][idx]["title"] = new_title
                data["users"][current_user]["tasks"][idx]["category"] = new_category
                data["users"][current_user]["tasks"][idx]["priority"] = new_priority
                data["users"][current_user]["tasks"][idx]["hours"] = new_hours
        
        save_data(data)
        return redirect(url_for('dashboard'))
    
    # محاسبه آمار کاربر فعلی
    user_tasks = data["users"][current_user]["tasks"]
    total_done = sum(1 for t in user_tasks if t["done"])
    total_tasks = len(user_tasks)
    
    # محاسبه ساعات امروز (فقط تسک‌های انجام شده امروز)
    today_hours = sum(t.get("hours", 0) for t in user_tasks if t["done"] and t.get("created_at") == today)
    
    # محاسبه ساعات هفته (تسک‌های انجام شده هفته اخیر)
    week_hours = {}
    for i in range(7):
        day = date.today() - timedelta(days=i)
        day_str = str(day)
        day_total = sum(t.get("hours", 0) for t in user_tasks if t["done"] and t.get("created_at") == day_str)
        week_hours[day_str] = day_total
    
    total_week_hours = sum(week_hours.values())
    
    # آمار دسته‌بندی‌ها
    category_stats = {}
    for cat in data["categories"]:
        tasks_in_cat = [t for t in user_tasks if t.get("category", "سایر") == cat]
        category_stats[cat] = {
            "total": len(tasks_in_cat),
            "done": sum(1 for t in tasks_in_cat if t["done"]),
            "hours": sum(t.get("hours", 0) for t in tasks_in_cat if t["done"])
        }
    
    # لیست همه کاربران (برای نمایش)
    all_users = []
    for username, user_data in data["users"].items():
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
    
    return render_template(
        "dashboard.html",
        current_user=current_user,
        fullname=data["users"][current_user]["fullname"],
        tasks=user_tasks,
        total_done=total_done,
        total_tasks=total_tasks,
        today=today,
        today_hours=today_hours,
        categories=data["categories"],
        category_stats=category_stats,
        week_hours=week_hours,
        total_week_hours=total_week_hours,
        all_users=all_users
    )

@app.route("/user/<username>")
@login_required
def view_user(username):
    data = load_data()
    current_user = session["username"]
    
    if username not in data["users"]:
        flash("کاربر یافت نشد!", "error")
        return redirect(url_for('dashboard'))
    
    user_data = data["users"][username]
    today = str(date.today())
    
    # محاسبه آمار
    total_done = sum(1 for t in user_data["tasks"] if t["done"])
    total_tasks = len(user_data["tasks"])
    today_hours = sum(t.get("hours", 0) for t in user_data["tasks"] if t["done"] and t.get("created_at") == today)
    
    # محاسبه ساعات هفته
    week_hours = {}
    for i in range(7):
        day = date.today() - timedelta(days=i)
        day_str = str(day)
        day_total = sum(t.get("hours", 0) for t in user_data["tasks"] if t["done"] and t.get("created_at") == day_str)
        week_hours[day_str] = day_total
    
    total_week_hours = sum(week_hours.values())
    
    # آمار دسته‌بندی‌ها
    category_stats = {}
    for cat in data["categories"]:
        tasks_in_cat = [t for t in user_data["tasks"] if t.get("category", "سایر") == cat]
        category_stats[cat] = {
            "total": len(tasks_in_cat),
            "done": sum(1 for t in tasks_in_cat if t["done"]),
            "hours": sum(t.get("hours", 0) for t in tasks_in_cat if t["done"])
        }
    
    return render_template(
        "view_user.html",
        viewed_user=username,
        fullname=user_data["fullname"],
        tasks=user_data["tasks"],
        total_done=total_done,
        total_tasks=total_tasks,
        today=today,
        today_hours=today_hours,
        categories=data["categories"],
        category_stats=category_stats,
        week_hours=week_hours,
        total_week_hours=total_week_hours,
        is_own_profile=(username == current_user)
    )

if __name__ == "__main__":
    app.run(debug=True)
