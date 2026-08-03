"""JSON-locale helpers used by templates and request handlers."""

import json
from pathlib import Path

from flask import session

SUPPORTED_LANGS = ("fa", "en")
DEFAULT_LANG = "fa"
_locale_cache = {}
_locale_dir = Path(__file__).resolve().parents[2] / "locales"


def get_lang():
    return session.get("lang", DEFAULT_LANG)


def load_locale(lang):
    if lang not in _locale_cache:
        with (_locale_dir / f"{lang}.json").open(encoding="utf-8") as locale_file:
            _locale_cache[lang] = json.load(locale_file)
    return _locale_cache[lang]


def t(key, **kwargs):
    value = load_locale(get_lang())
    for part in key.split("."):
        value = value.get(part, key) if isinstance(value, dict) else key
    return value.format(**kwargs) if isinstance(value, str) and kwargs else value


def inject_i18n():
    from translator import is_available_cached as translator_available

    locale = load_locale(get_lang())
    return {"t": t, "lang": get_lang(), "dir": locale.get("dir", "rtl"), "supported_langs": SUPPORTED_LANGS, "translator_available": translator_available()}
