"""Contact destinations are generated and validated here, never in the browser."""

import re
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from PIL import Image

from catalog.validators import validate_category_icon
from common.utils import to_english_digits
from footer.images import image_upload_error
from footer.validation import is_valid_email, is_valid_phone, phone_href


# Presets are suggestions, not database choices: new platforms only need a URL.
PLATFORMS = [
    ("whatsapp", "واتساپ", "phone"),
    ("telegram", "تلگرام", "username"),
    ("instagram", "اینستاگرام", "username"),
    ("phone", "تماس تلفنی", "phone"),
    ("sms", "پیامک", "phone"),
    ("email", "ایمیل", "email"),
    ("bale", "بله", "username"),
    ("eitaa", "ایتا", "username"),
    ("rubika", "روبیکا", "username"),
    ("linkedin", "لینکدین", "username"),
    ("custom", "پیوند دلخواه", "url"),
]
USERNAME_BASES = {
    "telegram": "https://t.me/",
    "instagram": "https://instagram.com/",
    "bale": "https://ble.ir/",
    "eitaa": "https://eitaa.com/",
    "rubika": "https://rubika.ir/",
    "linkedin": "https://www.linkedin.com/in/",
}
ICON_NAMES = [key for key, _, _ in PLATFORMS] + ["chat", "link"]


def normalize_phone(value: str, *, whatsapp=False) -> str:
    value = to_english_digits(value).strip()
    if not is_valid_phone(value):
        raise ValidationError("شماره تماس معتبر نیست؛ ۷ تا ۱۵ رقم وارد کنید")
    number = phone_href(value)[4:]
    if number.startswith("00"):
        number = "+" + number[2:]
    if whatsapp:
        # This storefront is Iranian; local mobile numbers have an unambiguous prefix.
        if re.fullmatch(r"09[0-9]{9}", number):
            number = "+98" + number[1:]
        digits = number.lstrip("+")
        if not re.fullmatch(r"[1-9][0-9]{6,14}", digits):
            raise ValidationError("شماره واتساپ را با کد کشور وارد کنید؛ مانند +989123456789")
        return digits
    if not 7 <= len(number.lstrip("+")) <= 15:
        raise ValidationError("شماره تماس معتبر نیست")
    return number


def safe_destination(value: str) -> str:
    decoded = unquote(value)
    if not value or any(ord(c) < 32 or ord(c) == 127 for c in decoded) or any(c in decoded for c in "\\<>"):
        raise ValidationError("نشانی مقصد معتبر و ایمن نیست")
    value = value.strip()
    try:
        parsed = urlsplit(value)
        # Accessing port rejects out-of-range and malformed numeric ports.
        parsed.port
    except ValueError as exc:
        raise ValidationError("نشانی مقصد معتبر نیست") from exc
    scheme = parsed.scheme.lower()
    if scheme in {"https", "http"}:
        URLValidator(schemes=["http", "https"])(value)
        if parsed.username is not None or parsed.password is not None:
            raise ValidationError("نام کاربری و رمز عبور در نشانی مجاز نیست")
        return value
    if parsed.netloc or parsed.fragment:
        raise ValidationError("نشانی تماس معتبر نیست")
    if scheme in {"tel", "sms"} and not parsed.query:
        return f"{scheme}:{normalize_phone(unquote(parsed.path))}"
    if scheme == "mailto" and not parsed.query and is_valid_email(unquote(parsed.path)):
        return "mailto:" + quote(unquote(parsed.path), safe="@.+-_")
    raise ValidationError("نشانی باید http، https، tel، sms یا mailto معتبر باشد")


def destination_for(button) -> str:
    if button.url.strip():
        return safe_destination(button.url)
    platform = button.platform
    if platform in {"whatsapp", "phone", "sms"}:
        try:
            phone = normalize_phone(button.phone_number, whatsapp=platform == "whatsapp")
        except ValidationError as exc:
            raise ValidationError({"phone_number": exc.messages}) from exc
        prefix = {"whatsapp": "https://wa.me/", "phone": "tel:", "sms": "sms:"}[platform]
        return prefix + phone
    if platform == "email":
        if not is_valid_email(button.email):
            raise ValidationError({"email": "یک نشانی ایمیل معتبر وارد کنید"})
        return "mailto:" + quote(button.email, safe="@.+-_")
    if platform in USERNAME_BASES:
        username = button.username.strip()
        if username.lower().startswith(("https://", "http://")):
            try:
                return safe_destination(username)
            except ValidationError as exc:
                raise ValidationError({"username": exc.messages}) from exc
        username = username.removeprefix("@")
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}", username):
            raise ValidationError({"username": "نام کاربری یا نشانی کامل معتبر وارد کنید"})
        return USERNAME_BASES[platform] + username
    raise ValidationError({"url": "برای این پلتفرم نشانی مقصد را وارد کنید"})


def validate_contact_icon(file) -> None:
    if not file:
        return
    extension = Path(file.name).suffix.lower()
    if extension in {".png", ".svg"}:
        # Reuse the existing strict SVG element/attribute allowlist and PNG validation.
        validate_category_icon(file)
        return
    if extension not in {".jpg", ".jpeg", ".webp"}:
        raise ValidationError("فرمت آیکن باید PNG، JPG، WebP یا SVG ایمن باشد")
    try:
        error = image_upload_error(file)
        if error:
            raise ValidationError(error)
        image = Image.open(file)
        expected = "WEBP" if extension == ".webp" else "JPEG"
        if image.format != expected:
            raise ValidationError("فرمت واقعی تصویر با پسوند فایل یکسان نیست")
    except Image.DecompressionBombError as exc:
        raise ValidationError("ابعاد تصویر بیش از حد مجاز است") from exc
    finally:
        file.seek(0)
