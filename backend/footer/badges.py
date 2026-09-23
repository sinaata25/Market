"""Strict image-and-link validation for footer certifications; no HTML embeds."""

from pathlib import Path
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from PIL import Image

from catalog.validators import validate_category_icon
from .images import image_upload_error


def validate_badge_url(value: str) -> None:
    decoded = unquote(value)
    if any(ord(char) < 32 or ord(char) == 127 for char in decoded) or any(
        char in decoded for char in "\\<>"
    ):
        raise ValidationError("نشانی نماد معتبر و ایمن نیست")
    URLValidator(schemes=["https", "http"], message="نشانی کامل http یا https وارد کنید")(value)
    try:
        parsed = urlsplit(value)
        parsed.port  # Reject malformed/out-of-range ports.
    except ValueError as exc:
        raise ValidationError("نشانی نماد معتبر نیست") from exc
    if parsed.username is not None or parsed.password is not None:
        raise ValidationError("نام کاربری و رمز عبور در نشانی مجاز نیست")


def validate_badge_image(file) -> None:
    if not file:
        raise ValidationError("تصویر نماد را انتخاب کنید")
    extension = Path(file.name).suffix.lower()
    if extension == ".svg":
        # Reuse the project's existing SVG element/attribute allowlist, 5 MiB limit.
        validate_category_icon(file)
        return
    formats = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}
    if extension not in formats:
        raise ValidationError("فرمت تصویر باید PNG، JPG، WebP یا SVG ایمن باشد")
    try:
        error = image_upload_error(file)
        if error:
            raise ValidationError(error)
        if Image.open(file).format != formats[extension]:
            raise ValidationError("فرمت واقعی تصویر با پسوند فایل یکسان نیست")
    except Image.DecompressionBombError as exc:
        raise ValidationError("ابعاد تصویر بیش از حد مجاز است") from exc
    finally:
        file.seek(0)
