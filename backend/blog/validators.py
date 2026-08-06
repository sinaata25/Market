import warnings
from io import BytesIO
from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

MAX_FEATURED_IMAGE_SIZE = 5 * 1024 * 1024
MAX_FEATURED_IMAGE_DIMENSION = 8000
MAX_FEATURED_IMAGE_PIXELS = 40_000_000
ALLOWED_FEATURED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


def validate_featured_image(value) -> None:
    """Validate bytes, dimensions, and format instead of trusting MIME metadata."""
    extension = Path(getattr(value, "name", "")).suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise ValidationError(
            "پسوند تصویر باید jpg، jpeg، png یا webp باشد.",
            code="unsupported_blog_image_extension",
        )
    try:
        original_position = value.tell()
    except (AttributeError, OSError, ValueError):
        original_position = 0

    try:
        try:
            value.seek(0)
        except (AttributeError, OSError, ValueError):
            value.open("rb")
            value.seek(0)
        data = value.read(MAX_FEATURED_IMAGE_SIZE + 1)
    finally:
        try:
            value.seek(original_position)
        except (AttributeError, OSError, ValueError):
            pass

    if not isinstance(data, bytes) or not data:
        raise ValidationError("فایل تصویر معتبر نیست.", code="invalid_blog_image")
    if len(data) > MAX_FEATURED_IMAGE_SIZE:
        raise ValidationError(
            "حجم تصویر حداکثر ۵ مگابایت باشد.", code="blog_image_too_large"
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format not in ALLOWED_FEATURED_IMAGE_FORMATS:
                    raise ValidationError(
                        "فرمت تصویر باید JPEG، PNG یا WebP باشد.",
                        code="unsupported_blog_image",
                    )
                width, height = image.size
                if (
                    width > MAX_FEATURED_IMAGE_DIMENSION
                    or height > MAX_FEATURED_IMAGE_DIMENSION
                    or width * height > MAX_FEATURED_IMAGE_PIXELS
                ):
                    raise ValidationError(
                        "ابعاد تصویر بیش از حد مجاز است.",
                        code="blog_image_dimensions",
                    )
                if getattr(image, "is_animated", False):
                    raise ValidationError(
                        "تصویر شاخص باید ثابت باشد.", code="animated_blog_image"
                    )
                image.verify()
    except ValidationError:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:
        raise ValidationError(
            "فایل ارسال‌شده تصویر معتبر نیست.", code="invalid_blog_image"
        ) from exc
