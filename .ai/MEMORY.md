# Project Memory

## Project

Name:
Study Planner


## Current Status

The project is functional but requires architectural improvements.


## Important Decisions


### Backend

Keep Flask.

Do not migrate to another backend framework.


### Database

Keep PostgreSQL.

Introduce migrations.


### Frontend

Keep current frontend initially.

Prepare backend for future SPA frontend.


---

# Avoid

Do not:

- rewrite everything
- introduce unnecessary frameworks
- create premature abstractions
- break existing user data


---

# Coding Style

Prefer:

- readable code
- explicit naming
- small functions
- clear modules


Avoid:

- giant files
- duplicated logic
- hidden side effects