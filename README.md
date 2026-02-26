<div dir="rtl">

# 📚 برنامه‌ریز مطالعه | Study Planner

یک اپلیکیشن وب برای ردیابی و مدیریت برنامه مطالعه دانشجویان، ساخته شده با Flask و PostgreSQL.
پشتیبانی کامل از **فارسی و انگلیسی** با سیستم i18n سفارشی.

> **شفافیت:** معماری دیتابیس، سیستم چندزبانه، و ریفکتورینگ کد این پروژه با کمک [Claude](https://claude.ai) (هوش مصنوعی Anthropic) انجام شده. ایده اولیه، طراحی UI، و تصمیمات محصول توسط توسعه‌دهنده گرفته شده. هوش مصنوعی به عنوان یک ابزار قدرتمند استفاده شد، نه جایگزین مهندسی.

</div>

---

<div dir="rtl">

## ✨ ویژگی‌ها

### مدیریت تسک و مطالعه
- 📝 افزودن تسک‌های درسی با سطح اولویت (مهم / متوسط / کم)
- ⏱️ ثبت ساعت مطالعه برای هر درس
- ✅ تیک زدن و پیگیری پیشرفت تسک‌ها
- ✏️ ویرایش و حذف تسک‌ها

### آمار و نمودار
- 📊 نمودار ساعت مطالعه هفتگی (bar chart)
- 📈 نمودار ساعت مطالعه ماهانه (line chart)
- 📉 آمار پیشرفت هر درس به صورت جداگانه
- 🔢 نمایش ساعت مطالعه امروز، این هفته، و این ماه

### کاربران و اجتماع
- 👥 مشاهده پروفایل و پیشرفت سایر کاربران
- 🏆 مقایسه ساعت مطالعه با همکلاسی‌ها

### امنیت و احراز هویت
- 🔐 رمز عبور با bcrypt هش می‌شود (ذخیره ایمن)
- 🛡️ محافظت از روت‌ها با decorator های login_required و admin_required
- 👮 پنل ادمین جداگانه با دسترسی محدود

### چندزبانه
- 🌐 پشتیبانی کامل از **فارسی (RTL) و انگلیسی (LTR)**
- 🔄 تغییر زبان از هر صفحه بدون از دست دادن اطلاعات
- 🤖 ترجمه خودکار نام رشته‌ها و دروس هنگام ورود (با LibreTranslate)
- 📁 سیستم locale با فایل‌های JSON قابل توسعه

### ادمین
- 👤 مدیریت کاربران (حذف، تغییر رمز)
- 🏫 مدیریت رشته‌ها و دروس (افزودن، حذف)
- 📊 آمار کلی سیستم (کاربران فعال، کل تسک‌ها، ساعت مطالعه)

### تجربه کاربری
- 🌙 تم تاریک / روشن (ذخیره در دیتابیس)
- 📱 طراحی واکنش‌گرا (موبایل و دسکتاپ)
- ⚡ انیمیشن‌های روان در UI

</div>

---

## ✨ Features

- 📝 Task management per course with priority levels (High / Medium / Low)
- ⏱️ Study hour tracking with daily, weekly, and monthly breakdowns
- 📊 Interactive charts (weekly bar + monthly line) powered by Chart.js
- 👥 Social view — see other users' progress and study hours
- 🔐 Secure hashed passwords (Werkzeug / bcrypt)
- 🌙 Dark / Light theme toggle, saved per user
- 🌐 Full **Persian ↔ English** i18n with RTL/LTR layout switching
- 🤖 Auto-translate major/course names via LibreTranslate
- 🛡️ Admin panel — user management, majors, courses, system stats
- 🗄️ PostgreSQL + SQLAlchemy ORM (auto-seeded on first run)

---

<div dir="rtl">

## 🏗️ تکنولوژی‌ها

| لایه        | تکنولوژی                        |
|-------------|----------------------------------|
| بک‌اند      | Python 3.10+ / Flask 3.0         |
| دیتابیس     | PostgreSQL 14+ / SQLAlchemy 2.0  |
| فرانت‌اند   | Bootstrap 5 / Chart.js           |
| ترجمه خودکار| LibreTranslate (self-hosted)     |
| i18n        | سیستم JSON locale سفارشی         |
| استقرار     | Gunicorn                         |

</div>

## 🏗️ Tech Stack

| Layer       | Technology                      |
|-------------|----------------------------------|
| Backend     | Python 3.10+ / Flask 3.0        |
| Database    | PostgreSQL 14+ / SQLAlchemy 2.0 |
| Frontend    | Bootstrap 5 / Chart.js          |
| Translation | LibreTranslate (self-hosted)    |
| i18n        | Custom JSON locale system       |
| Deployment  | Gunicorn                        |

---

<div dir="rtl">

## 🚀 راه‌اندازی صفر تا صد

### پیش‌نیازها

قبل از شروع مطمئن شو این‌ها نصب هستن:

- [Python 3.10+](https://www.python.org/downloads/)
- [PostgreSQL 14+](https://www.postgresql.org/download/) + pgAdmin (اختیاری)
- Git

---

### مرحله ۱ — دریافت کد

```bash
git clone https://github.com/Hosseinamiri850/study_planner.git
cd study_planner
```

---

### مرحله ۲ — نصب وابستگی‌ها

```bash
pip install -r requirements.txt
```

خروجی موفق این‌ها رو نصب می‌کنه:
- `Flask 3.0`
- `Flask-SQLAlchemy 3.1`
- `psycopg[binary]` (درایور PostgreSQL)
- `requests` (برای LibreTranslate)
- `gunicorn` (سرور production)

---

### مرحله ۳ — ساخت دیتابیس

**روش A — با pgAdmin (گرافیکی):**
1. pgAdmin رو باز کن
2. روی `Servers` ← `PostgreSQL` کلیک راست کن
3. `Create` ← `Database` رو انتخاب کن
4. نام `study_planner` بذار و Save کن

**روش B — با خط فرمان:**
```bash
# ویندوز (PowerShell):
psql -U postgres -c "CREATE DATABASE study_planner;"

# لینوکس/مک:
createdb study_planner
```

---

### مرحله ۴ — تنظیم اتصال دیتابیس

فایل `app.py` رو باز کن و این خط رو پیدا کن:

```python
"postgresql+psycopg://postgres:postgres@localhost:5432/study_planner"
```

`postgres` دوم رو با رمز عبور PostgreSQL خودت عوض کن:

```python
"postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/study_planner"
```

یا با متغیر محیطی (روش بهتر):

```bash
# ویندوز:
set DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/study_planner

# لینوکس/مک:
export DATABASE_URL="postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/study_planner"
```

---

### مرحله ۵ — اجرا

```bash
python app.py
```

در اولین اجرا، برنامه به صورت **خودکار**:
- ✅ همه جداول دیتابیس رو می‌سازه
- ✅ اکانت ادمین پیش‌فرض می‌سازه (`admin` / `admin`)
- ✅ رشته مهندسی کامپیوتر با ۱۳ درس پیش‌فرض وارد می‌کنه

بعد مرورگر رو باز کن و برو به:
```
http://localhost:5000
```

> ⚠️ **مهم:** فوری بعد از اولین لاگین، رمز ادمین رو از پنل مدیریت تغییر بده!

---

### مرحله ۶ (اختیاری) — فعال‌سازی ترجمه خودکار

برای ترجمه خودکار فارسی↔انگلیسی هنگام افزودن رشته/درس:

```bash
# نصب LibreTranslate
pip install libretranslate

# اجرا (در یه terminal جداگانه)
libretranslate --host 0.0.0.0 --port 5001
```

یا اگه نمی‌خوای self-hosted باشه، از public instance استفاده کن — فایل `translator.py` رو باز کن و این خط رو عوض کن:

```python
LIBRETRANSLATE_URL = "https://translate.argosopentech.com"
```

بدون LibreTranslate هم برنامه کاملاً کار می‌کنه — فقط ترجمه خودکار غیرفعاله و باید هر دو فیلد فارسی و انگلیسی رو دستی پر کنی.

---

### مرحله ۷ (اختیاری) — استقرار با Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

</div>

## 🚀 Quick Start (English)

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Git

### Step 1 — Clone
```bash
git clone https://github.com/Hosseinamiri850/study_planner.git
cd study_planner
pip install -r requirements.txt
```

### Step 2 — Create Database
```sql
-- psql or pgAdmin
CREATE DATABASE study_planner;
```

### Step 3 — Configure
Edit `app.py` or set environment variable:
```bash
export DATABASE_URL="postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/study_planner"
```

### Step 4 — Run
```bash
python app.py
```
App auto-creates tables, seeds admin (`admin`/`admin`), and seeds default CS courses.

Open → [http://localhost:5000](http://localhost:5000)

### Step 5 (Optional) — Auto-translate
```bash
pip install libretranslate
libretranslate --host 0.0.0.0 --port 5001
```

---

<div dir="rtl">

## 🗃️ ساختار دیتابیس

```
users    — id, username, password (hashed), fullname, is_admin, theme, created_at
majors   — id, key (slug), name_fa, name_en
courses  — id, key (slug), name_fa, name_en, major_id
tasks    — id, user_id, course_key, description, done, priority, hours, created_at
```

رشته‌ها و دروس با **هر دو نام فارسی و انگلیسی** ذخیره می‌شن.
تسک‌ها `course_key` (یه slug زبان‌خنثی) ذخیره می‌کنن تا در هر زبانی درست نمایش داده بشن.

</div>

## 🗃️ Database Schema

```
users    — id, username, password (hashed), fullname, is_admin, theme, created_at
majors   — id, key (slug), name_fa, name_en
courses  — id, key (slug), name_fa, name_en, major_id
tasks    — id, user_id, course_key, description, done, priority, hours, created_at
```

---

<div dir="rtl">

## 📁 ساختار پروژه

```
study_planner/
├── app.py              ← بک‌اند اصلی (روت‌ها، مدل‌ها، seed)
├── translator.py       ← ماژول ترجمه LibreTranslate
├── requirements.txt
├── .gitignore
├── README.md
├── locales/
│   ├── fa.json         ← همه متن‌های فارسی UI
│   └── en.json         ← همه متن‌های انگلیسی UI
└── templates/
    ├── base.html       ← base template + JS ترجمه خودکار
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── admin.html
    └── view_user.html
```

## افزودن زبان جدید

۱. فایل `locales/en.json` رو کپی کن به `locales/xx.json`
۲. همه مقادیر رو ترجمه کن
۳. در `app.py` مقدار `"xx"` رو به `SUPPORTED_LANGS` اضافه کن

</div>

## 📁 Project Structure

```
study_planner/
├── app.py              ← Main app (routes, models, seed)
├── translator.py       ← LibreTranslate integration
├── requirements.txt
├── .gitignore
├── README.md
├── locales/
│   ├── fa.json         ← Persian UI strings
│   └── en.json         ← English UI strings
└── templates/
    ├── base.html       ← Base template + AutoTranslate JS
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── admin.html
    └── view_user.html
```

---

<div dir="rtl">

## 👤 اکانت ادمین پیش‌فرض

| فیلد        | مقدار   |
|-------------|---------|
| نام کاربری  | `admin` |
| رمز عبور   | `admin` |

> ⚠️ بلافاصله بعد از اولین لاگین رمز رو از طریق پنل مدیریت تغییر بده.

</div>

## 👤 Default Admin Credentials

| Field    | Value   |
|----------|---------|
| Username | `admin` |
| Password | `admin` |

> ⚠️ Change the admin password immediately after first login via the Admin Panel.

---

<div dir="rtl">

## 🤝 مشارکت

Pull request ها خوش‌آمد هستند. برای تغییرات بزرگ اول یه issue باز کن.

</div>

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first.

---

## 📄 License

MIT © [Hossein Amiri](https://github.com/Hosseinamiri850)
