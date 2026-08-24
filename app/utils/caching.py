"""Thin Redis cache in front of hot read paths (TASK-025).

Design:
- No-op passthrough when `REDIS_URL` is unset — dev/test never need Redis.
- Values are JSON-serialized; callers cache plain data, not ORM entities.
- Graceful degradation: any client error logs a warning and behaves like a
  miss (or a dropped write). A dead Redis must never take the app down.
- Explicit invalidation: writers call `cache_delete` with the exact keys
  they dirty. No wildcard flushing.

The client is created lazily and cached on `current_app`, mirroring the
replica-engine pattern in `app/repositories/base.py`.
"""

import json
import logging

from flask import current_app

logger = logging.getLogger(__name__)

# Canonical cache keys shared by readers and writers.
KEY_COURSES_ALL = "courses:all"
KEY_MAJORS_TEMPLATE = "majors:template"
KEY_TRANSLATOR_AVAILABLE = "translator:available"


def _client():
    """Return a redis client for the current app, or None when caching is
    disabled (no REDIS_URL and no injected test client, or redis missing).

    An explicitly injected `_cache_client` wins over the URL check — that is
    the test seam. In production the client is built once from REDIS_URL and
    cached on the app config."""
    client = current_app.config.get("_cache_client")
    if client is not None:
        return client
    url = current_app.config.get("REDIS_URL", "")
    if not url:
        return None
    try:
        import redis  # lazy: only needed when a URL is configured
    except ImportError:
        logger.warning("REDIS_URL set but redis package not installed; caching disabled.")
        return None
    client = redis.Redis.from_url(url, decode_responses=True)
    current_app.config["_cache_client"] = client
    return client


def _key(namespace, name):
    return f"{namespace}:{name}"


def cache_get(key):
    """Fetch a cached value by key. Returns (hit, value); on miss or any
    client error returns (False, None)."""
    client = _client()
    if client is None:
        return False, None
    try:
        raw = client.get(key)
    except Exception as exc:  # noqa: BLE001 - degrade, don't crash
        logger.warning("cache_get(%s) failed, falling through to DB: %s", key, exc)
        return False, None
    if raw is None:
        return False, None
    try:
        return True, json.loads(raw)
    except (TypeError, ValueError):
        # Corrupt entry — treat as a miss; it will be overwritten on next set.
        return False, None


def cache_set(key, value, ttl):
    """Store a JSON-serializable value under key with a TTL in seconds.
    Errors are logged and swallowed — a failed cache write is harmless."""
    client = _client()
    if client is None:
        return
    try:
        client.set(key, json.dumps(value), ex=ttl)
    except Exception as exc:  # noqa: BLE001
        logger.warning("cache_set(%s) failed: %s", key, exc)


def cache_delete(*keys):
    """Invalidate one or more keys. Missing keys are not an error."""
    client = _client()
    if client is None or not keys:
        return
    try:
        client.delete(*keys)
    except Exception as exc:  # noqa: BLE001
        logger.warning("cache_delete(%s) failed: %s", keys, exc)


def cached(namespace, name, ttl):
    """Decorator for zero-argument read-model functions: wrap a callable so
    its JSON result is served from the cache when present, computed + stored
    otherwise. The function must return JSON-serializable data."""

    def decorator(fn):
        key = _key(namespace, name)

        def wrapper():
            hit, value = cache_get(key)
            if hit:
                return value
            value = fn()
            cache_set(key, value, ttl)
            return value

        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        wrapper.invalidate = lambda: cache_delete(key)
        return wrapper

    return decorator


def reset_cache_client():
    """Drop the per-app cached client — used by tests to reconfigure."""
    try:
        current_app.config.pop("_cache_client", None)
    except RuntimeError:
        pass  # no app context (unit tests calling helpers directly)
