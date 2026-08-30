"""پروکسی جست‌وجو و جست‌وجوی معکوس نشانی برای انتخابگر نقشه‌ی داشبورد

عمداً از سمت سرور صدا زده می‌شود، نه مرورگر: این‌طور می‌توان User-Agent
معتبر فرستاد (سیاست استفاده‌ی Nominatim آن را می‌خواهد و مرورگر اجازه‌ی
تنظیمش را نمی‌دهد)، سرویس‌دهنده را پشت API خودمان ایزوله کرد، و نرخ
درخواست را محدود نگه داشت.

نبود این سرویس، انتخاب موقعیت را از کار نمی‌اندازد: مدیر همچنان می‌تواند
روی نقشه کلیک کند یا مختصات را دستی وارد کند.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings

from .maps import LATITUDE_RANGE, LONGITUDE_RANGE

logger = logging.getLogger(__name__)

MAX_RESULTS = 8
MAX_QUERY_LENGTH = 200
REQUEST_TIMEOUT = (3, 8)


class GeocodingUnavailable(Exception):
    """سرویس نشانی پاسخ نداد — فراخوان باید ۵۰۳ کنترل‌شده برگرداند"""


@dataclass(frozen=True)
class GeocodeResult:
    label: str
    latitude: Decimal
    longitude: Decimal


def _request(path: str, params: dict) -> list | dict:
    base_url = settings.NOMINATIM_BASE_URL.rstrip("/")
    try:
        response = requests.get(
            f"{base_url}/{path}",
            params={"format": "jsonv2", "accept-language": "fa", **params},
            headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("geocoding request failed (%s)", path, exc_info=True)
        raise GeocodingUnavailable from exc


def _coordinate(raw: object, low: Decimal, high: Decimal) -> Decimal | None:
    try:
        value = Decimal(str(raw)).quantize(Decimal("0.000001"))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return value if low <= value <= high else None


def search(query: str) -> list[GeocodeResult]:
    """جست‌وجوی نشانی/مکان — فهرست خالی یعنی چیزی پیدا نشد"""
    query = query.strip()[:MAX_QUERY_LENGTH]
    if not query:
        return []

    payload = _request("search", {"q": query, "limit": MAX_RESULTS})
    if not isinstance(payload, list):
        raise GeocodingUnavailable

    results: list[GeocodeResult] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        latitude = _coordinate(entry.get("lat"), *LATITUDE_RANGE)
        longitude = _coordinate(entry.get("lon"), *LONGITUDE_RANGE)
        label = str(entry.get("display_name") or "").strip()
        if latitude is None or longitude is None or not label:
            continue
        results.append(GeocodeResult(label, latitude, longitude))
    return results


def reverse(latitude: Decimal, longitude: Decimal) -> str:
    """نشانی خوانا برای یک نقطه — رشته‌ی خالی یعنی نشانی‌ای پیدا نشد"""
    payload = _request("reverse", {"lat": str(latitude), "lon": str(longitude)})
    if not isinstance(payload, dict):
        raise GeocodingUnavailable
    return str(payload.get("display_name") or "").strip()
