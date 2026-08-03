> **Architecture update (P0):** the application now uses an application factory,
> blueprints, isolated models/services, and Alembic migrations. Tables are no
> longer created when the server starts.

## Development and database migrations

Copy `.env.example` to `.env` and provide your own `SECRET_KEY` and
`DATABASE_URL`. `SECRET_KEY` is required; the application will refuse to start
without it. The `.env` file is loaded for local development and must never be
committed.

Run migrations before starting the server:

```bash
flask --app app db upgrade
flask --app app seed-reference-data  # optional: bundled majors and courses
python app.py
```

For a database created by the pre-migration version of the application, take a
backup first, then record the matching baseline before upgrading:

```bash
flask --app app db stamp 20260723_01
flask --app app db upgrade
```

The second revision adds `Task.status`, `Task.estimated_hours`, an optional
`Task.course_id`, completion metadata, and the `StudySession` table. Legacy
`course_key`, `hours`, and `done` columns are retained for compatibility while
the application transitions to the normalized model.

`seed-reference-data` deliberately creates **no administrator account**. Create
users through registration, then assign administrative access using an audited
deployment/admin process. Existing databases should be backed up and stamped or
migrated according to their current Alembic state before deployment.

```text
app/
  models/       SQLAlchemy entities
  routes/       web, admin, and API blueprints
  services/     statistics and explicit seed operations
  utils/        authentication and i18n helpers
  extensions.py Flask extension instances
  config.py     environment-backed configuration
```

## REST API

The API is ready for a mobile client or a future SPA. Authentication endpoints
return a signed access token valid for 24 hours; send it with every protected
request as `Authorization: Bearer <access_token>`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/auth/register` | Create a user and return an access token |
| POST | `/api/auth/login` | Sign in and return an access token |
| GET / POST | `/api/tasks` | List or create the authenticated user's tasks |
| PUT / DELETE | `/api/tasks/:id` | Update or remove one owned task |
| GET | `/api/statistics/dashboard` | Retrieve dashboard metrics |

The browser routes continue to use session authentication and CSRF protection;
the mobile API's mutating endpoints accept bearer tokens only.

---

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
- 🔐 رمز عبور هش می‌شود (ذخیره ایمن با Werkzeug)
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
- 🔐 Secure hashed passwords (Werkzeug)
- 🌙 Dark / Light theme toggle, saved per user
- 🌐 Full **Persian ↔ English** i18n with RTL/LTR layout switching
- 🤖 Auto-translate major/course names via LibreTranslate
- 🛡️ Admin panel — user management, majors, courses, system stats
- 🗄️ PostgreSQL + SQLAlchemy ORM, schema managed by Alembic migrations

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

### مرحله ۳ — تنظیم اتصال دیتابیس

فایل `.env.example` رو به `.env` کپی کن و مقادیر خودت رو وارد کن:

```bash
cp .env.example .env
```

حداقل این متغیرها رو تنظیم کن (`.env` هرگز commit نشه):

```bash
SECRET_KEY=یک-رشته-طولانی-تصادفی-و-مخفی
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/study_planner
```

> `SECRET_KEY` الزامی است؛ برنامه بدون آن راه‌اندازی نمی‌شود.

---

### مرحله ۴ — اجرای migration و seed

برخلاف نسخه‌های قدیمی، برنامه دیگر جداول را به‌صورت خودکار **نمی‌سازد** و اکانت ادمین
پیش‌فرض **ایجاد نمی‌کند**. مراحل زیر را به‌ترتیب اجرا کن:

```bash
flask --app app db upgrade        # ساختن/به‌روزرسانی جداول از طریق Alembic
flask --app app seed-reference-data  # اختیاری: رشته و ۱۳ درس پیش‌فرض کامپیوتر
```

سپس یک ادمین بساز (برای ورود به پنل مدیریت):

```bash
flask --app app create-admin <username>
# از شما رمز عبور می‌خواهد (نمایش داده نمی‌شود) و آن را هش‌شده ذخیره می‌کند
```

> برنامه به‌صورت عمدی هیچ اکانت `admin/admin` پیش‌فرض نمی‌سازد. ادمین فقط از طریق
> دستور `create-admin` ساخته می‌شود.

---

### مرحله ۵ — اجرا

```bash
python app.py
```

مرورگر رو باز کن و برو به:
```
http://localhost:5000
```

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

> در محیط production حتماً یک `SECRET_KEY` قوی و `DATABASE_URL` مناسب را از طریق
> متغیرهای محیطی تنظیم کن و migration‌ها را قبل از اجرا اعمال کن
> (`flask --app app db upgrade`).

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
Copy `.env.example` to `.env` and set your own values:
```bash
cp .env.example .env
```
```bash
SECRET_KEY=a-long-random-secret-string
DATABASE_URL="postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/study_planner"
```
`SECRET_KEY` is required; the app refuses to start without it.

### Step 4 — Migrate, seed, and create an admin
```bash
flask --app app db upgrade            # create/update tables via Alembic
flask --app app seed-reference-data   # optional: bundled CS majors & courses
flask --app app create-admin <username>   # prompts for a password, hashes it
```
The app no longer auto-creates tables or seeds any default `admin/admin` account.
Create an admin explicitly via the `create-admin` command above.

### Step 5 — Run
```bash
python app.py
```
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
users           — id, username, password (hashed), fullname, is_admin, theme, created_at
majors          — id, key (slug), name_fa, name_en
courses         — id, key (slug), name_fa, name_en, major_id
tasks           — id, user_id, course_id, course_key, title, description, priority,
                  status, hours, estimated_hours, done, created_at, completed_at
study_sessions  — id, task_id, duration, started_at, ended_at
```

رشته‌ها و دروس با **هر دو نام فارسی و انگلیسی** ذخیره می‌شن.
تسک‌ها `course_key` (یه slug زبان‌خنثی) ذخیره می‌کنن تا در هر زبانی درست نمایش داده بشن.
ستون‌های قدیمی (`course_key`, `hours`, `done`) در کنار ستون‌های نرمال‌سازی‌شده
(`course_id`, `estimated_hours`, `status`) برای سازگاری با داده‌های قدیمی حفظ شده‌اند.

</div>

## 🗃️ Database Schema

```
users           — id, username, password (hashed), fullname, is_admin, theme, created_at
majors          — id, key (slug), name_fa, name_en
courses         — id, key (slug), name_fa, name_en, major_id
tasks           — id, user_id, course_id, course_key, title, description, priority,
                  status, hours, estimated_hours, done, created_at, completed_at
study_sessions  — id, task_id, duration, started_at, ended_at
```

Legacy columns (`course_key`, `hours`, `done`) are retained alongside the
normalized ones (`course_id`, `estimated_hours`, `status`) for compatibility
with pre-migration data. |

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

## 👤 ساخت ادمین

برنامه به‌صورت عمدی هیچ اکانت ادمین پیش‌فرضی نمی‌سازد. برای دسترسی به پنل مدیریت،
یک ادمین از طریق دستور زیر بساز:

```bash
flask --app app create-admin <username>
```

> این دستور رمز عبور را درخواست می‌کند (نمایش داده نمی‌شود)، آن را هش کرده و
> کاربر را با نقش ادمین ثبت می‌کند.

</div>

## 👤 Creating an Admin

The app deliberately creates **no default admin account**. Create one explicitly
via the CLI command before accessing the admin panel:

```bash
flask --app app create-admin <username>
```

> Prompts for a password (hidden), hashes it, and creates the user with admin role.

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
