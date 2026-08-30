"""مقصدهای گوگل مپس و محدوده‌های مختصات فروشگاه

پیوندها همیشه از مختصات ذخیره‌شده ساخته می‌شوند، نه از نشانی متنی یا لینکی
که مدیر تایپ کرده — تا سوزن نقشه دقیقاً روی همان نقطه‌ای بیفتد که مدیر روی
نقشه انتخاب کرده است.
"""

from __future__ import annotations

from decimal import Decimal
from urllib.parse import urlencode, urlsplit

LATITUDE_RANGE = (Decimal("-90"), Decimal("90"))
LONGITUDE_RANGE = (Decimal("-180"), Decimal("180"))
ZOOM_RANGE = (1, 21)
DEFAULT_ZOOM = 15

# میزبان‌های معتبر برای پیوند اختیاری «صفحه‌ی کسب‌وکار در گوگل مپس»
_GOOGLE_MAPS_HOSTS = {"goo.gl", "maps.app.goo.gl", "maps.google.com"}
_GOOGLE_DOMAIN_PREFIX = "google."


def format_coordinate(value: Decimal) -> str:
    """۳۵.۷۰۰۰۰۰ → «35.7»؛ format(..., 'f') از نماد علمی جلوگیری می‌کند"""
    return format(value.normalize(), "f")


def coordinate_query(latitude: Decimal, longitude: Decimal) -> str:
    return f"{format_coordinate(latitude)},{format_coordinate(longitude)}"


def maps_search_url(latitude: Decimal, longitude: Decimal) -> str:
    """نمایش همان نقطه روی گوگل مپس"""
    query = urlencode(
        {"api": "1", "query": coordinate_query(latitude, longitude)}
    )
    return f"https://www.google.com/maps/search/?{query}"


def maps_directions_url(latitude: Decimal, longitude: Decimal) -> str:
    """مسیریابی تا همان نقطه — مقصد همیشه از مختصات ساخته می‌شود"""
    query = urlencode(
        {"api": "1", "destination": coordinate_query(latitude, longitude)}
    )
    return f"https://www.google.com/maps/dir/?{query}"


def is_google_maps_url(value: str) -> bool:
    """پیوند مطلق http(s) روی یکی از میزبان‌های گوگل مپس"""
    try:
        parsed = urlsplit(value)
    except (UnicodeError, ValueError):
        return False
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False

    host = parsed.hostname or ""
    if host in _GOOGLE_MAPS_HOSTS:
        return True
    # google.com/maps و دامنه‌های کشوری مثل google.de/maps
    without_www = host.removeprefix("www.")
    return without_www.startswith(_GOOGLE_DOMAIN_PREFIX) and parsed.path.startswith(
        "/maps"
    )
