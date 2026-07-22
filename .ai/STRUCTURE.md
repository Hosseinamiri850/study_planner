# Study Planner Project Structure

## Overview

Study Planner is a Flask-based productivity application designed to help users manage courses, tasks, and study progress.

Current stack:

Backend:
- Python
- Flask
- SQLAlchemy

Database:
- PostgreSQL

Frontend:
- HTML
- CSS
- Bootstrap
- JavaScript

Visualization:
- Chart.js


---

# Current Architecture

The project currently uses a simple Flask structure.

Main responsibilities are mixed:

- application initialization
- routes
- models
- authentication
- admin logic
- database setup


This structure works for small projects but creates maintenance problems.


---

# Target Architecture


app/

__init__.py

Application factory.

extensions.py

Contains:

- database
- login manager
- migrations


models/

Database entities.


routes/

HTTP controllers.


services/

Business logic.


utils/

Reusable helpers.


config.py

Application configuration.



---

# Design Principles

1. Separation of concerns

2. Single responsibility

3. Explicit dependencies

4. Testable components

5. API readiness


---

# Database Structure


User

|
|
Task

|
|
StudySession


Future:

Course

Category

Achievement

Notification