"""Small, dependency-free validation rules shared by browser controllers and APIs."""

import re


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,80}$")
VALID_PRIORITIES = {"low", "medium", "high"}


def valid_username(value):
    return bool(USERNAME_PATTERN.fullmatch(value or ""))


def valid_password(value):
    return len(value or "") >= 8


def valid_priority(value):
    return value in VALID_PRIORITIES


def positive_hours(value):
    try:
        hours = float(value)
    except (TypeError, ValueError):
        return None
    return hours if 0 <= hours <= 24 else None
