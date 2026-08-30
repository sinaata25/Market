"""اعتبارسنجی تصویرهای آپلودی فوتر (لوگو و آیتم‌های تصویری)"""

from PIL import Image, UnidentifiedImageError

MAX_FOOTER_IMAGE_SIZE = 2 * 1024 * 1024
MAX_FOOTER_IMAGE_PIXELS = 16_777_216


def image_upload_error(file) -> str | None:
    """پیام خطا اگر فایل تصویر معتبری نباشد، وگرنه None"""
    if file is None:
        return "فایل تصویر ارسال نشده است"
    if file.size > MAX_FOOTER_IMAGE_SIZE:
        return "حجم تصویر حداکثر ۲ مگابایت باشد"
    try:
        image = Image.open(file)
        width, height = image.size
        image.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        return "فایل ارسال‌شده تصویر معتبر نیست"
    finally:
        file.seek(0)
    if width * height > MAX_FOOTER_IMAGE_PIXELS:
        return "ابعاد تصویر بیش از حد مجاز است"
    return None
