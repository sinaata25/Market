"""اعتبارسنجی مشترک مقادیر فوتر — لینک، شماره، ایمیل و متن ساده

قاعده‌ی HTML همان قاعده‌ی ``staticpages``: محتوای فوتر متن ساده است و هیچ
تگی پذیرفته نمی‌شود، پس هیچ رشته‌ای بدون sanitize به فروشگاه نمی‌رسد.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from django.core.validators import validate_email as django_validate_email
from django.core.exceptions import ValidationError as DjangoValidationError

from common.utils import to_english_digits

HTML_TAG_RE = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")
PHONE_RE = re.compile(r"^\+?[0-9][0-9() \-]{5,24}$")
CONTROL_CHARACTERS = tuple(chr(code) for code in range(32) if chr(code) not in "\n\r\t")


def contains_html(value: str) -> bool:
    return bool(HTML_TAG_RE.search(value))


def contains_control_characters(value: str) -> bool:
    return any(character in value for character in CONTROL_CHARACTERS)


def is_internal_url(value: str) -> bool:
    """مسیر داخلی فروشگاه — با / شروع می‌شود اما // نیست (که یعنی بیرونی)"""
    return value.startswith("/") and not value.startswith("//")


def is_external_url(value: str) -> bool:
    if not value.lower().startswith(("http://", "https://")):
        return False
    try:
        parsed = urlsplit(value)
    except (UnicodeError, ValueError):
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_safe_url(value: str) -> bool:
    """تنها دو شکل مجاز: مسیر داخلی (/...) یا نشانی مطلق http(s)"""
    return is_internal_url(value) or is_external_url(value)


def is_valid_phone(value: str) -> bool:
    normalized = to_english_digits(value)
    if not PHONE_RE.fullmatch(normalized):
        return False
    digits = [character for character in normalized if character.isdigit()]
    if not 7 <= len(digits) <= 15:
        return False

    depth = 0
    for character in normalized:
        if character == "(":
            depth += 1
            if depth > 1:
                return False
        elif character == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def is_valid_email(value: str) -> bool:
    try:
        django_validate_email(value)
    except DjangoValidationError:
        return False
    return True


def phone_href(value: str) -> str:
    """شماره‌ی نمایشی را به مقصد قابل شماره‌گیری tel: تبدیل می‌کند"""
    normalized = to_english_digits(value).strip()
    plus = "+" if normalized.startswith("+") else ""
    digits = "".join(character for character in normalized if character.isdigit())
    return f"tel:{plus}{digits}" if digits else ""
