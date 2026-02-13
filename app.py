from flask import Flask, render_template, request, redirect, jsonify
import json
import os
from datetime import date, datetime, timedelta

app = Flask(__name__)
DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "tasks": [],
            "hours": {},
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
        # اطمینان از وجود فیلدهای جدید
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

@app.route("/", methods=["GET", "POST"])
def index():
    data = load_data()
    today = str(date.today())
    
    if request.method == "POST":
        # اضافه کردن تسک جدید
        if "new_task" in request.form:
            task = request.form["new_task"]
            category = request.form.get("category", "سایر")
            priority = request.form.get("priority", "medium")
            if task.strip():
                data["tasks"].append({
                    "title": task,
                    "done": False,
                    "category": category,
                    "priority": priority,
                    "created_at": today
                })
        
        # تغییر وضعیت تسک (انجام شده/نشده)
        if "toggle" in request.form:
            idx = int(request.form["toggle"])
            if 0 <= idx < len(data["tasks"]):
                data["tasks"][idx]["done"] = not data["tasks"][idx]["done"]
        
        # حذف تسک
        if "delete" in request.form:
            idx = int(request.form["delete"])
            if 0 <= idx < len(data["tasks"]):
                data["tasks"].pop(idx)
        
        # ویرایش تسک
        if "edit_idx" in request.form:
            idx = int(request.form["edit_idx"])
            new_title = request.form.get("edit_title")
            new_category = request.form.get("edit_category")
            new_priority = request.form.get("edit_priority")
            if 0 <= idx < len(data["tasks"]) and new_title.strip():
                data["tasks"][idx]["title"] = new_title
                data["tasks"][idx]["category"] = new_category
                data["tasks"][idx]["priority"] = new_priority
        
        # ذخیره ساعت مطالعه
        if "hours" in request.form:
            hours_value = request.form["hours"]
            if hours_value:
                data["hours"][today] = float(hours_value)
        
        # اضافه کردن دسته‌بندی جدید
        if "new_category" in request.form:
            new_cat = request.form["new_category"].strip()
            if new_cat and new_cat not in data["categories"]:
                data["categories"].append(new_cat)
        
        save_data(data)
        return redirect("/")
    
    # محاسبه آمار
    total_done = sum(1 for t in data["tasks"] if t["done"])
    total_tasks = len(data["tasks"])
    
    # آمار دسته‌بندی‌ها
    category_stats = {}
    for cat in data["categories"]:
        tasks_in_cat = [t for t in data["tasks"] if t.get("category", "سایر") == cat]
        category_stats[cat] = {
            "total": len(tasks_in_cat),
            "done": sum(1 for t in tasks_in_cat if t["done"])
        }
    
    # آمار هفته اخیر
    week_hours = {}
    for i in range(7):
        day = date.today() - timedelta(days=i)
        day_str = str(day)
        week_hours[day_str] = data["hours"].get(day_str, 0)
    
    total_week_hours = sum(week_hours.values())
    
    return render_template(
        "index.html",
        tasks=data["tasks"],
        total_done=total_done,
        total_tasks=total_tasks,
        today=today,
        hours=data["hours"].get(today, ""),
        categories=data["categories"],
        category_stats=category_stats,
        week_hours=week_hours,
        total_week_hours=total_week_hours
    )

if __name__ == "__main__":
    app.run(debug=True)