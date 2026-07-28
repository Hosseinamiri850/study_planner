# System Design


## Current System

_Updated 2026-07: the "Future System" layering below is implemented, not just
planned. `app/routes/api.py` is a working REST API (JSON + Bearer auth) that
sits alongside the server-rendered browser routes and shares the same
services/models layer. The server-rendered frontend is still the only client
in production use — no SPA or mobile app consumes the API yet._

A Flask application with a factory pattern, blueprint-separated routes
(web, admin, api), a service layer, and a normalized PostgreSQL schema
managed by Alembic migrations.


## Future System


Frontend

|
|
REST API

|
|
Service Layer

|
|
Database Layer



---

# Components


## Authentication

Responsible for:

- users
- sessions
- permissions



## Task Management

Responsible for:

- courses
- tasks
- completion tracking



## Study Tracking

Responsible for:

- study sessions
- statistics
- productivity metrics



## Analytics

Responsible for:

- dashboards
- progress
- trends



---

# Future Scalability


Possible future clients:

- Web SPA
- Mobile applications
- Browser extension


Therefore:

Business logic should not depend directly on templates.