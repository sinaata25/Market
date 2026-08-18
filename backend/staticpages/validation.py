from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError

from .definitions import default_content, field_value, fields_for_page


PHONE_RE = re.compile(r"^\+?[0-9][0-9() \-]{5,24}$")
HTML_TAG_RE = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")
DIGIT_TRANSLATION = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"
)


def _structure_errors(value: Any, expected: Any, path: str = "content") -> list[str]:
    if isinstance(expected, dict):
        if not isinstance(value, dict):
            return [f"{path} باید یک شیء باشد"]
        expected_keys = set(expected)
        actual_keys = set(value)
        if expected_keys != actual_keys:
            return [f"ساختار {path} با ساختار ثابت صفحه مطابقت ندارد"]
        errors: list[str] = []
        for key in expected:
            errors.extend(_structure_errors(value[key], expected[key], f"{path}.{key}"))
        return errors

    if isinstance(expected, list):
        if not isinstance(value, list) or len(value) != len(expected):
            return [f"تعداد موارد {path} قابل تغییر نیست"]
        errors = []
        for index, item in enumerate(expected):
            errors.extend(_structure_errors(value[index], item, f"{path}.{index}"))
        return errors

    if not isinstance(value, str):
        return [f"{path} باید متن باشد"]
    return []


def _is_safe_link(value: str) -> bool:
    if value == "#":
        return True
    try:
        parsed = urlsplit(value)
    except (UnicodeError, ValueError):
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _phone_is_valid(value: str) -> bool:
    if not PHONE_RE.fullmatch(value):
        return False
    digits = "".join(character for character in value if character.isdigit())
    if not 7 <= len(digits) <= 15:
        return False

    depth = 0
    for character in value:
        if character == "(":
            depth += 1
            if depth > 1:
                return False
        elif character == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _normalized_digits(value: str) -> str:
    translated = value.translate(DIGIT_TRANSLATION)
    return "".join(character for character in translated if character.isdigit())


def content_errors(key: str, content: Any) -> dict[str, str]:
    try:
        expected = default_content(key)
    except KeyError:
        return {"key": "شناسه صفحه پشتیبانی نمی‌شود"}

    structure = _structure_errors(content, expected)
    if structure:
        return {"content": structure[0]}

    errors: dict[str, str] = {}
    for field in fields_for_page(key):
        value = field_value(content, field)
        if field.required and not value.strip():
            errors[field.id] = "این فیلد الزامی است"
            continue
        if len(value) > field.max_length:
            errors[field.id] = f"حداکثر {field.max_length} نویسه مجاز است"
            continue
        if HTML_TAG_RE.search(value):
            errors[field.id] = (
                "ورود HTML مجاز نیست؛ محتوا را به‌صورت متن ساده وارد کنید"
            )
        elif field.path[-1] == "phoneNumber" and not _phone_is_valid(value):
            errors[field.id] = "شماره تماس معتبر نیست"
        elif field.path[-1] == "onlineUrl" and not _is_safe_link(value):
            errors[field.id] = "پیوند باید # یا یک نشانی بیرونی معتبر http/https باشد"
        elif any(
            ord(character) < 32 and character not in "\n\r\t"
            for character in value
        ):
            errors[field.id] = "متن دارای نویسه کنترلی نامعتبر است"

    if key == "contact" and not errors.get("ways.0.phoneNumber"):
        display_number = content["ways"][0]["label"]
        dial_number = content["ways"][0]["phoneNumber"]
        if _normalized_digits(display_number) != _normalized_digits(dial_number):
            errors["ways.0.label"] = (
                "رقم‌های شماره نمایشی باید با شماره قابل شماره‌گیری یکسان باشند"
            )
    return errors


def validate_content(key: str, content: Any) -> None:
    errors = content_errors(key, content)
    if errors:
        raise ValidationError(errors)
