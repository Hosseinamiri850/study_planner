"""
translator.py — LibreTranslate translation module.

LibreTranslate is a free, open-source translation service.
It can be self-hosted, or a public instance can be used.

Self-hosted install:
    pip install libretranslate
    libretranslate --host 0.0.0.0 --port 5001

Public instance (free, requires an API key):
    https://libretranslate.com
Public instance (no key):
    https://translate.argosopentech.com
"""

import logging
import os
import re
import time

import requests

logger = logging.getLogger(__name__)

# ─── Settings ────────────────────────────────────────────────────────────────

# Self-hosted: "http://localhost:5001"
# Public instance: "https://translate.argosopentech.com"
LIBRETRANSLATE_URL = os.environ.get(
    "LIBRETRANSLATE_URL",
    "http://localhost:5001"
)

# Leave empty for most public instances; libretranslate.com needs an API key.
LIBRETRANSLATE_API_KEY = os.environ.get("LIBRETRANSLATE_API_KEY", "")

# Request timeout (seconds).
REQUEST_TIMEOUT = 5


# ─── Language detection ────────────────────────────────────────────────────

def detect_language(text: str) -> str:
    """
    Detect whether text is Persian or English.
    Uses Unicode ranges — no API call needed.
    """
    persian_chars = len(re.findall(r'[؀-ۿ]', text))
    latin_chars   = len(re.findall(r'[a-zA-Z]',        text))

    if persian_chars > latin_chars:
        return "fa"
    elif latin_chars > persian_chars:
        return "en"
    else:
        # On a tie, decide by the first meaningful character.
        for ch in text:
            if '؀' <= ch <= 'ۿ':
                return "fa"
            if ch.isalpha():
                return "en"
        return "en"


# ─── Translation ──────────────────────────────────────────────────────────

def translate(text: str, source: str, target: str) -> str | None:
    """
    Translate text via LibreTranslate.

    Args:
        text:   input text
        source: source language ('fa' or 'en')
        target: target language ('fa' or 'en')

    Returns:
        Translated text, or None on error.
    """
    if not text or not text.strip():
        return ""

    if source == target:
        return text

    # LibreTranslate uses "fa" for Persian.
    payload = {
        "q":      text.strip(),
        "source": source,
        "target": target,
        "format": "text",
    }
    if LIBRETRANSLATE_API_KEY:
        payload["api_key"] = LIBRETRANSLATE_API_KEY

    try:
        resp = requests.post(
            f"{LIBRETRANSLATE_URL}/translate",
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json().get("translatedText", "").strip()

    except requests.exceptions.ConnectionError:
        logger.warning("LibreTranslate unavailable: %s", LIBRETRANSLATE_URL)
        return None
    except requests.exceptions.Timeout:
        logger.warning("LibreTranslate timeout")
        return None
    except Exception as e:
        logger.error("Translation error: %s", e)
        return None


def auto_translate(text: str) -> dict:
    """
    Auto-detect language and translate to the other one.

    Args:
        text: input text (Persian or English)

    Returns:
        {'fa': '...', 'en': '...', 'detected': 'fa'/'en', 'success': bool}
    """
    detected = detect_language(text)
    target   = "en" if detected == "fa" else "fa"

    translated = translate(text, source=detected, target=target)

    if translated:
        return {
            "fa":       text      if detected == "fa" else translated,
            "en":       text      if detected == "en" else translated,
            "detected": detected,
            "success":  True,
        }
    else:
        # On failure, fill both fields with the original text.
        return {
            "fa":       text,
            "en":       text,
            "detected": detected,
            "success":  False,
        }


def is_available() -> bool:
    """Check whether LibreTranslate is reachable."""
    try:
        resp = requests.get(
            f"{LIBRETRANSLATE_URL}/languages",
            timeout=2
        )
        return resp.status_code == 200
    except Exception:
        return False


# ─── Availability cache ────────────────────────────────────────────────────
# `is_available()` makes a blocking HTTP request; invoking it from the context
# processor (which runs on every request) means every page load pays up to
# 2s of latency. This TTL cache holds the value so the network is hit only
# once per TTL window. Backed by Redis when REDIS_URL is set (shared across
# workers), by an in-process dict otherwise.
_AVAILABILITY_TTL = 60  # seconds
_availability_cache = {"value": None, "expires_at": 0.0}


def is_available_cached() -> bool:
    """TTL-cached version of `is_available()`.

    Suitable for the `inject_i18n` context processor, so per-render blocking
    network calls are avoided. The `/api/translator-status` route still uses
    `is_available()` directly for a live answer.
    """
    # Import lazily: this module must stay importable outside app context
    # (tests stub it directly).
    from flask import current_app

    try:
        from app.utils.caching import KEY_TRANSLATOR_AVAILABLE, cache_get, cache_set

        if current_app.config.get("REDIS_URL"):
            hit, value = cache_get(KEY_TRANSLATOR_AVAILABLE)
            if hit:
                return value
            value = is_available()
            cache_set(KEY_TRANSLATOR_AVAILABLE, value, _AVAILABILITY_TTL)
            return value
    except RuntimeError:
        pass  # no app context — fall through to in-process cache
    now = time.monotonic()
    if _availability_cache["value"] is not None and now < _availability_cache["expires_at"]:
        return _availability_cache["value"]
    value = is_available()
    _availability_cache["value"] = value
    _availability_cache["expires_at"] = now + _AVAILABILITY_TTL
    return value


def reset_availability_cache() -> None:
    """Clear the cache — for tests. Safe without app context."""
    _availability_cache["value"] = None
    _availability_cache["expires_at"] = 0.0
    try:
        from app.utils.caching import KEY_TRANSLATOR_AVAILABLE, cache_delete

        cache_delete(KEY_TRANSLATOR_AVAILABLE)
    except RuntimeError:  # no app context
        pass
