"""Tests for the Redis cache layer (TASK-025).

No live Redis in CI: a fake client is injected as `_cache_client` on the app
config. The fake records calls so tests can assert hits/misses/invalidations
exactly. The Redis-down path uses a fake whose methods raise.
"""

import json
from collections import defaultdict

import pytest

from app.repositories import CourseRepo, MajorRepo
from app.services.statistics import all_courses_list, majors_for_template
from app.utils.caching import (
    KEY_COURSES_ALL,
    KEY_MAJORS_TEMPLATE,
    cache_delete,
    cache_get,
    cache_set,
    reset_cache_client,
)


class FakeRedis:
    """Minimal stand-in for redis.Redis with the surface the cache uses."""

    def __init__(self):
        self.store = {}
        self.calls = defaultdict(int)

    def get(self, key):
        self.calls["get"] += 1
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.calls["set"] += 1
        self.store[key] = value

    def delete(self, *keys):
        self.calls["delete"] += 1
        removed = 0
        for key in keys:
            if self.store.pop(key, None) is not None:
                removed += 1
        return removed


class DeadRedis:
    """Simulates an unreachable Redis — every operation raises."""

    def get(self, key):
        raise ConnectionError("redis down")

    def set(self, key, value, ex=None):
        raise ConnectionError("redis down")

    def delete(self, *keys):
        raise ConnectionError("redis down")


@pytest.fixture
def fake_cache(app):
    client = FakeRedis()
    app.config["_cache_client"] = client
    yield client
    reset_cache_client()


@pytest.fixture
def dead_cache(app):
    app.config["_cache_client"] = DeadRedis()
    yield
    reset_cache_client()


class TestCacheHelpers:
    def test_no_redis_url_is_passthrough(self, app):
        # TestConfig sets no REDIS_URL and injects no client.
        hit, value = cache_get(KEY_COURSES_ALL)
        assert hit is False and value is None
        cache_set(KEY_COURSES_ALL, [1], 60)  # must not raise
        cache_delete(KEY_COURSES_ALL)  # must not raise

    def test_set_and_get_roundtrip(self, app, fake_cache):
        payload = [{"key": "a", "name": "A"}]
        cache_set(KEY_COURSES_ALL, payload, 120)
        hit, value = cache_get(KEY_COURSES_ALL)
        assert hit is True
        assert value == payload
        assert fake_cache.store[KEY_COURSES_ALL] == json.dumps(payload)

    def test_miss_returns_not_hit(self, app, fake_cache):
        hit, value = cache_get("missing:key")
        assert hit is False and value is None

    def test_corrupt_entry_treated_as_miss(self, app, fake_cache):
        fake_cache.store[KEY_COURSES_ALL] = "{not json"
        hit, value = cache_get(KEY_COURSES_ALL)
        assert hit is False and value is None

    def test_dead_redis_reads_as_miss(self, app, dead_cache):
        hit, value = cache_get(KEY_COURSES_ALL)
        assert hit is False and value is None

    def test_dead_redis_writes_do_not_crash(self, app, dead_cache):
        cache_set(KEY_COURSES_ALL, [], 60)
        cache_delete(KEY_COURSES_ALL)


class TestCachedReadModels:
    def test_all_courses_list_caches_second_call(self, app, fake_cache, create_course):
        create_course(key="algo", name_en="Algorithms")
        first = all_courses_list()
        second = all_courses_list()
        assert first == second
        gets = fake_cache.calls["get"]
        assert gets >= 2  # both calls consulted the cache
        # Only one DB-backed fill: a single `set` after the first call.
        assert fake_cache.calls["set"] == 1

    def test_invalidate_on_course_create_refetches(self, app, fake_cache, create_major):
        create_major(key="cs")
        all_courses_list()  # fills cache
        cached_before = fake_cache.store.get(KEY_COURSES_ALL)
        assert cached_before is not None
        CourseRepo.create(key="new_course", name_fa="n", name_en="New", major_id=1)
        assert KEY_COURSES_ALL not in fake_cache.store
        rows = all_courses_list()
        assert any(row["key"] == "new_course" for row in rows)

    def test_majors_template_invalidated_by_major_write(self, app, fake_cache):
        majors_for_template()  # fills cache
        assert KEY_MAJORS_TEMPLATE in fake_cache.store
        MajorRepo.create(key="physics", name_fa="فیزیک", name_en="Physics")
        assert KEY_MAJORS_TEMPLATE not in fake_cache.store
        fresh = majors_for_template()
        assert any(major["key"] == "physics" for major in fresh)

    def test_language_neutral_rows_cached(self, app, fake_cache, create_major, create_course):
        major = create_major(name_fa="فارسی نام", name_en="English Name")
        create_course(major=major, name_fa="درس فارسی", name_en="Course English")
        with app.test_request_context():
            session_lang = __import__("flask").session
            session_lang["lang"] = "en"
            en_view = all_courses_list()[0]
            template_view = majors_for_template()[0]
        raw = json.loads(fake_cache.store[KEY_COURSES_ALL])
        # The cached rows carry both languages; nothing request-scoped baked in.
        assert raw[0]["name_fa"] == "درس فارسی"
        assert raw[0]["name_en"] == "Course English"
        assert en_view["name"] == "Course English"
        assert template_view["name"] == "English Name"

    def test_seeder_commit_invalidates(self, app, fake_cache):
        from app.services.seed import seed_reference_data

        seed_reference_data()
        assert KEY_COURSES_ALL not in fake_cache.store
        assert KEY_MAJORS_TEMPLATE not in fake_cache.store


class TestGracefulDegradationRouteLevel:
    def test_dashboard_renders_with_dead_redis(self, dead_cache, login_client):
        response = login_client.get("/dashboard")
        assert response.status_code == 200

    def test_admin_panel_renders_with_dead_redis(self, dead_cache, admin_client):
        response = admin_client.get("/admin")
        assert response.status_code == 200


@pytest.fixture
def login_client(client, create_user):
    user = create_user(username="cacheuser", password="testpass123")
    with client.session_transaction() as sess:
        sess["username"] = user.username
    return client


@pytest.fixture
def admin_client(client, create_user):
    user = create_user(username="cacheadmin", password="testpass123", is_admin=True)
    with client.session_transaction() as sess:
        sess["username"] = user.username
    return client
