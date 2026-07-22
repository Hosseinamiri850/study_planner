# Development Roadmap


# P0 - Critical


## TASK-001
## Application Factory Pattern

Priority:
P0

Goal:

Separate Flask initialization from business logic.


Files:

app.py


Expected:

Create:

app/__init__.py


---

## TASK-002

## Split Routes

Priority:

P0


Move:

authentication routes

admin routes

dashboard routes


into Flask Blueprints.



---

## TASK-003

## Database Migration

Priority:

P0


Add:

Flask-Migrate

Alembic


Remove:

automatic production table creation



---

# P1 - High


## TASK-004

Security Hardening


Actions:

- remove default credentials
- environment secrets
- CSRF
- validation



---

## TASK-005

Database Model Improvement


Create:

StudySession


Improve:

Task relationships



---

## TASK-006

REST API Layer


Create API modules.


---

# P2 - Medium


## TASK-007

Testing


Add pytest.


---

## TASK-008

Docker Support


Add:

Dockerfile

docker-compose



---

# P3 - Low


## TASK-009

Gamification


Add:

streaks

achievements



---

## TASK-010

Smart Planner


Automatic schedule generation.