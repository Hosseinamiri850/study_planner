"""
translator.py — ماژول ترجمه با LibreTranslate

LibreTranslate یه سرویس ترجمه رایگان و open-source هست.
می‌تونه self-hosted باشه یا از public instance استفاده کنی.

نصب (self-hosted):
    pip install libretranslate
    libretranslate --host 0.0.0.0 --port 5001

یا استفاده از public instance رایگان:
    https://libretranslate.com  (نیاز به API key رایگان داره)
    https://translate.argosopentech.com (بدون key)
"""

import os
import re
import requests
import logging

logger = logging.getLogger(__name__)

# ─── تنظیمات ────────────────────────────────────────────────────────────────

# اگه self-hosted داری: "http://localhost:5001"
# اگه از public instance استفاده می‌کنی: "https://translate.argosopentech.com"
LIBRETRANSLATE_URL = os.environ.get(
    "LIBRETRANSLATE_URL",
    "http://localhost:5001"
)

# برای اکثر public instance‌ها خالی بذار، برای libretranslate.com api key لازمه
LIBRETRANSLATE_API_KEY = os.environ.get("LIBRETRANSLATE_API_KEY", "")

# timeout برای request (ثانیه)
REQUEST_TIMEOUT = 5


# ─── تشخیص زبان ────────────────────────────────────────────────────────────

def detect_language(text: str) -> str:
    """
    تشخیص اینکه متن فارسی هست یا انگلیسی.
    از Unicode range استفاده می‌کنه — بدون نیاز به API.
    """
    persian_chars = len(re.findall(r'[\u0600-\u06FF]', text))
    latin_chars   = len(re.findall(r'[a-zA-Z]',        text))

    if persian_chars > latin_chars:
        return "fa"
    elif latin_chars > persian_chars:
        return "en"
    else:
        # اگه مساوی بود، بر اساس اولین کاراکتر معنادار تصمیم بگیر
        for ch in text:
            if '\u0600' <= ch <= '\u06FF':
                return "fa"
            if ch.isalpha():
                return "en"
        return "en"


# ─── ترجمه ──────────────────────────────────────────────────────────────────

def translate(text: str, source: str, target: str) -> str | None:
    """
    ترجمه متن با LibreTranslate.
    
    Args:
        text:   متن ورودی
        source: زبان مبدأ ('fa' یا 'en')
        target: زبان مقصد ('fa' یا 'en')
    
    Returns:
        متن ترجمه شده، یا None در صورت خطا
    """
    if not text or not text.strip():
        return ""

    if source == target:
        return text

    # LibreTranslate از کد "fa" برای فارسی استفاده می‌کنه
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
        logger.warning("LibreTranslate در دسترس نیست: %s", LIBRETRANSLATE_URL)
        return None
    except requests.exceptions.Timeout:
        logger.warning("LibreTranslate timeout")
        return None
    except Exception as e:
        logger.error("خطای ترجمه: %s", e)
        return None


def auto_translate(text: str) -> dict:
    """
    تشخیص خودکار زبان و ترجمه به زبان دیگه.
    
    Args:
        text: متن ورودی (فارسی یا انگلیسی)
    
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
        # اگه ترجمه شکست خورد، هر دو فیلد رو با همون متن پر کن
        return {
            "fa":       text,
            "en":       text,
            "detected": detected,
            "success":  False,
        }


def is_available() -> bool:
    """بررسی اینکه LibreTranslate در دسترسه یا نه"""
    try:
        resp = requests.get(
            f"{LIBRETRANSLATE_URL}/languages",
            timeout=2
        )
        return resp.status_code == 200
    except Exception:
        return False
