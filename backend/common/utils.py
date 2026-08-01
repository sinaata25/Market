"""توابع کمکی مشترک"""

import re

from django.core.exceptions import ValidationError

_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"

_TRANSLATION = {ord(p): str(i) for i, p in enumerate(_PERSIAN_DIGITS)}
_TRANSLATION.update({ord(a): str(i) for i, a in enumerate(_ARABIC_DIGITS)})

# ``\d`` is deliberately avoided: in Python it also accepts Devanagari,
# full-width and many other Unicode digits which are invalid in an E.164 number.
IRAN_MOBILE_RE = re.compile(r"^09[0-9]{9}$", flags=re.ASCII)


def to_english_digits(value: str) -> str:
    """ارقام فارسی/عربی را به انگلیسی تبدیل می‌کند."""
    return value.translate(_TRANSLATION)


def normalize_digits(value: str) -> str:
    """ارقام را انگلیسی و فاصله‌های معمول را حذف می‌کند."""
    return re.sub(r"\s+", "", to_english_digits(value or "")).strip()


def normalize_phone(value: str) -> str:
    """شماره موبایل ایران را در قالب داخلی 09xxxxxxxxx یکسان می‌کند."""
    phone = normalize_digits(value)
    phone = phone.replace("-", "").replace("(", "").replace(")", "")
    if phone.startswith("+98"):
        phone = "0" + phone[3:]
    elif phone.startswith("0098"):
        phone = "0" + phone[4:]
    elif phone.startswith("98") and len(phone) == 12:
        phone = "0" + phone[2:]
    return phone


def is_valid_iran_mobile(value: str) -> bool:
    """شماره موبایل ایران: ۱۱ رقم و شروع با ۰۹"""
    return bool(IRAN_MOBILE_RE.match(normalize_phone(value)))


def validate_iran_mobile(value: str) -> None:
    """Django model/form validator for canonical Iranian mobile numbers."""
    if not is_valid_iran_mobile(value):
        raise ValidationError("شماره موبایل معتبر نیست")


def iran_mobile_to_e164(value: str) -> str:
    """شماره معتبر داخلی را به قالب E.164 موردنیاز IPPanel می‌برد."""
    phone = normalize_phone(value)
    if not is_valid_iran_mobile(phone):
        raise ValueError("invalid Iranian mobile number")
    return f"+98{phone[1:]}"
