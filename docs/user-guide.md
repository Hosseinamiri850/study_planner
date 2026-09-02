# Study Planner — User Guide

This guide is for people using Study Planner — no programming knowledge needed. It explains how to create an account, plan your courses and tasks, time your study sessions, and read your statistics.

---

## Contents

1. [Getting started](#1-getting-started)
2. [Logging in and out](#2-logging-in-and-out)
3. [The dashboard](#3-the-dashboard)
4. [Tasks: create, edit, complete, delete](#4-tasks-create-edit-complete-delete)
5. [Courses and organizing your work](#5-courses-and-organizing-your-work)
6. [Study sessions and the timer](#6-study-sessions-and-the-timer)
7. [Understanding your statistics](#7-understanding-your-statistics)
8. [Your profile and settings](#8-your-profile-and-settings)
9. [Language and theme](#9-language-and-theme)
10. [For administrators](#10-for-administrators)
11. [Troubleshooting](#11-troubleshooting)
12. [Tips for getting the most out of Study Planner](#12-tips-for-getting-the-most-out-of-study-planner)

---

## 1. Getting started

### Creating your account

1. Open Study Planner in your browser.
2. Click **Register** (or go to the registration page your school/organization gave you).
3. Fill in three fields:
   - **Username** — 3–80 characters; letters, numbers, and underscores only.
   - **Password** — at least 8 characters.
   - **Full name** — how your name appears to others (for example on the class overview).
4. Click the register button. If everything is valid you are taken to the login page with a success message.

If registration fails, the page shows a red message explaining why — usually the username is already taken, or the password is shorter than 8 characters. Fix the highlighted field and try again. Your other inputs are kept, so you only need to correct what went wrong.

### First login

After registering, log in with the username and password you chose. You land on your **dashboard** — your home base for everything else in this guide.

---

## 2. Logging in and out

### Logging in

1. Go to the login page.
2. Enter your username and password.
3. Click **Log in**.

If you see *"Invalid username or password"*, check for typos (and that Caps Lock is off). For your security the app does not reveal which of the two was wrong.

### Staying logged in

Once you log in, you stay logged in for about a month on that browser — you can close the tab, restart the browser, or reboot your computer and come straight back to your dashboard. Only logging out (or a password change) ends that.

If you are ever returned to the login page unexpectedly, just log in again; your tasks and statistics are stored on the server and nothing is lost.

### Logging out

Click **Logout** (in the top navigation). You are returned to the login page. Logging out twice in a row is harmless.

> If you share a computer with others, always log out when you finish studying. Logging out on one device does **not** log you out on other devices — each browser keeps its own session.

---

## 3. The dashboard

The dashboard is the first thing you see after logging in. From top to bottom:

- **Header with your name** — plus the language switch (فارسی / English) and the theme toggle (dark/light moon-sun button).
- **Statistics cards** — study hours for today, this week, and this month, plus task counts (see section 7).
- **Charts** — a weekly bar chart and a monthly line chart of your study hours.
- **Your task list** — every task you created, grouped by course, with buttons to start a timer, edit, complete, or delete.
- **New-task form** — the panel where you add tasks (see section 4).
- **Classmates panel** — a friendly comparison of every user's task counts and today's study hours. This is read-only: others can see your totals and you can see theirs.

Everything on the dashboard updates as soon as you take an action — no manual refresh needed.

---

## 4. Tasks: create, edit, complete, delete

A **task** is one piece of study work tied to a course — for example, "Chapter 4 exercises" in Mathematics.

### Creating a task

1. In the **new task** panel, pick the **course** from the dropdown.
2. Optionally type a **description** (what exactly you need to do).
3. Choose a **priority**: high, medium, or low.
4. Enter the **estimated hours** — your best guess at how long it will take (0–24 hours).
5. Click **Add**. The task appears in your list immediately.

### Completing a task

Tick the checkbox (or press the complete button) on a task when you finish it. Completed tasks stay visible so you can see your progress; you can untick one if you finished it by mistake.

### Editing a task

Press the **edit** button on a task. You can change its course, description, priority, and estimated hours. Save your changes — the row updates instantly.

### Deleting a task

Press **delete** and confirm. Deletion is permanent and removes the task's recorded study sessions with it, so double-check before confirming.

---

## 5. Courses and organizing your work

Every task belongs to a **course** (Mathematics, Physics, …). Courses are provided by your organization's administrators and are shared by everyone — that is why the course list shows each course in both Persian and English.

- Your tasks are grouped under their course on the dashboard, and the **per-course progress cards** show how many tasks each course has, how many are done, and how many hours you have studied for it.
- You cannot create or rename courses yourself — ask an administrator if a course you need is missing (see section 10 for what admins can do).
- **Majors** group related courses together (for example, all Computer Science courses). Majors matter mostly to administrators; as a regular user you simply pick a course from the list.

> Tip: keep one task per concrete piece of work ("Read chapter 5", "Problem set 3") rather than one giant task for the whole course. The statistics become much more meaningful that way.

---

## 6. Study sessions and the timer

This is the heart of the app: **the hours you log come from real study sessions, not guesses.**

### Starting a session

1. Find the task you are about to work on.
2. Press **Start** on that task's row.
3. A live timer appears on the task — it counts up as you study.

The timer keeps running if you navigate around the app. If you **reload the page** (or close and reopen the browser), the timer comes back automatically with the correct elapsed time — nothing is lost.

### Stopping a session

Press **Stop** on the same task when you finish. The session is saved with its duration, and your statistics update immediately: today's hours, the weekly chart, the monthly chart, and the course progress card.

### Rules worth knowing

- **One running session per task.** If a session is already running for a task, starting another shows *"A session is already running for this task."* Stop the current one first.
- **Sessions are per task, not global.** You can study two different tasks at once (for example, reading one book while an exercise set "cooks") — each task runs its own timer.
- **Zero-length sessions are fine.** Start and immediately stop? The session is recorded with zero duration and simply does not change your totals.
- **Long sessions are fine too.** Forgot to stop a session yesterday? Stopping it now records the full elapsed time under today's date.
- If you try to stop a session that was already stopped, you get a gentle *"No active session to stop."* message — nothing breaks.

---

## 7. Understanding your statistics

All statistics are computed from your actual study sessions.

| Statistic | What it means |
| --- | --- |
| **Today's hours** | Total time you studied (across all tasks) so far today. |
| **This week** | The last 7 days, shown as a bar chart — one bar per day. |
| **This month** | The last 30 days, shown as a line chart. |
| **Total tasks / done** | How many tasks you have created and how many are completed. |
| **Per-course cards** | For each course: total tasks, completed tasks, and hours studied for that course. |

A few things to keep in mind:

- Hours come **only from sessions you actually ran** — a task marked complete with no sessions adds zero hours. If you studied offline, estimate afterwards by starting a short session, or simply accept that offline work is not counted.
- Day boundaries follow **the server's date** (the same date your tasks use), so "today" is consistent between the task list and the charts.
- The classmates panel shows *today's hours only* — a snapshot of who is studying right now, not a leaderboard.

---

## 8. Your profile and settings

Open **Profile** from the navigation. Here you can:

- **Change your display name** (full name). This is what other users see in the classmates panel.
- **Switch your theme** — dark or light. Your choice is saved to your account and follows you to any device after login.
- **Change your password** — enter your current password, then the new one (at least 8 characters).

### About password changes

Changing your password **logs you out everywhere**: all other devices and browsers that were signed in as you lose their sessions and must log in again with the new password. This is deliberate — if someone else had your old password, it stops working the moment you change it.

If you change your password and find yourself logged out, that is the expected behavior — just log in with the new password.

---

## 9. Language and theme

### Switching language

Use the **فارسی / English** switch in the header. The whole interface — labels, buttons, messages, and charts — switches instantly, and page direction flips between right-to-left (Persian) and left-to-right (English). Your course and major names display in the selected language too.

The language choice is remembered per browser. Your account's stored preference is applied when you log in.

### Theme

The moon/sun toggle switches between dark and light. Like the language, it is remembered: for guests in the browser, for logged-in users in their account profile.

---

## 10. For administrators

Everything below requires an **administrator account**. Administrators are created by the people running the server — you cannot make yourself one. If you believe you need admin access, contact your server administrator.

Regular users do **not** see any of these controls, and the server double-checks every admin action — hiding the buttons for normal users is backed up by real server-side permission checks.

Admins get an extra **Admin** page in the navigation with:

### Managing majors

- **Create a major** — give it a Persian name and an English name (both are required; the English name also becomes the major's internal key).
- **Rename a major** — update either name.
- **Delete a major** — ask for confirmation first. Deleting a major affects how its courses are organized, so use with care.

### Managing courses

- **Create a course** — pick the major it belongs to, then enter Persian and English names.
- **Rename a course** or **move it** to a different major.
- **Delete a course** — with confirmation. Tasks that referenced the course keep working (they keep their course label), but new tasks can no longer select it.

### A note on the auto-translation feature

When a new major or course is created and the optional translation service is enabled, the missing language's name is filled in automatically. If the service is offline, the admin simply fills both names by hand — nothing breaks.

---

## 11. Troubleshooting

| Problem | What it means / what to do |
| --- | --- |
| *"Invalid username or password"* at login | Check typos and Caps Lock. Reset via your administrator if you forgot the password. |
| *"Username is already in use"* at registration | Pick a different username. |
| *"Username must be 3–80 letters, numbers, or underscores; password must be at least 8 characters."* | Shorten/fix the username or lengthen the password. |
| Page says *"A session is already running for this task."* | Stop the current session on that task before starting a new one. |
| Page says *"No active session to stop."* | The session was already stopped (maybe in another tab). Refresh the page to see current state. |
| *"Administrator privileges required."* | You tried an admin action without being an admin. Regular accounts cannot do this. |
| *"estimated_hours must be between 0 and 24..."* | Task hours must be a number from 0 to 24. |
| Statistics look empty after a fresh login | Statistics come from study sessions. Run a session (section 6) and they will fill in. |
| Timer did not come back after reload | The timer restores automatically; if it did not, refresh once more. If a task still shows Start while you were studying, the session ended elsewhere — your past hours are still saved. |
| Persian text looks mirrored/wrong direction | That is RTL rendering working correctly. If it looks broken, check that your browser is up to date. |
| Buttons look unstyled or the page looks broken | Hard-refresh the page (Ctrl+Shift+R / Cmd+Shift+R). If it persists, the server may be restarting — try again in a minute. |

---

## 12. Tips for getting the most out of Study Planner

1. **Start the timer before every study block, stop it after.** The entire statistics system is powered by this one habit.
2. **Split big assignments into small tasks.** "Study for final" is demotivating; "Chapter 5 exercises — 2h" gives you a finish line.
3. **Use priorities honestly.** High-priority tasks help you decide what to open first when time is short.
4. **Check the weekly chart on Sundays.** Spot the empty days before they become empty weeks.
5. **Use the classmates panel for accountability, not competition.** Consistent daily hours beat occasional marathons.
6. **Dark theme at night, light theme in daylight** — your eyes will thank you, and the preference follows your account across devices.
7. **Log out on shared computers** — your session lasts about a month otherwise.
8. **If you finish work offline**, either start a brief session to log approximate time or accept the gap; a partial, honest record is still a useful record.

---

*Enjoy your studying — and may your weekly chart always be climbing.*
