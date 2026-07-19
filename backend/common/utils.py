"""توابع کمکی مشترک"""

import re

_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"

_TRANSLATION = {ord(p): str(i) for i, p in enumerate(_PERSIAN_DIGITS)}
_TRANSLATION.update({ord(a): str(i) for i, a in enumerate(_ARABIC_DIGITS)})

IRAN_MOBILE_RE = re.compile(r"^09\d{9}$")


def to_english_digits(value: str) -> str:
    """ارقام فارسی/عربی را به انگلیسی تبدیل می‌کند."""
    return value.translate(_TRANSLATION)


def normalize_phone(value: str) -> str:
    return to_english_digits(value or "").replace(" ", "").strip()


def is_valid_iran_mobile(value: str) -> bool:
    """شماره موبایل ایران: ۱۱ رقم و شروع با ۰۹"""
    return bool(IRAN_MOBILE_RE.match(normalize_phone(value)))
