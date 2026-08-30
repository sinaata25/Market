"""بی‌اعتبارکردن کش فوتر در فرانت پس از تغییر مدیر

فوتر روی تقریباً همه‌ی صفحه‌ها است، پس Next آن را کش می‌کند. بعد از هر
تغییر مدیر، یک درخواست کوتاه به مسیر revalidate فرانت فرستاده می‌شود تا
همان تگ کش باطل شود. اگر متغیرهای محیطی تنظیم نشده باشند (توسعه‌ی محلی)
این کار بی‌صدا انجام نمی‌شود و کش با انقضای زمانی خودش تازه می‌گردد.
"""

from __future__ import annotations

import logging
import threading

import requests
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

FOOTER_CACHE_TAG = "footer"
REQUEST_TIMEOUT = (3, 5)


def _post_revalidation(url: str, secret: str) -> None:
    try:
        requests.post(
            url,
            json={"tag": FOOTER_CACHE_TAG},
            headers={"X-Revalidate-Secret": secret},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        # کش فرانت انقضای زمانی هم دارد؛ شکست اینجا نباید پاسخ مدیر را خراب کند
        logger.warning("footer cache revalidation request failed", exc_info=True)


def schedule_footer_revalidation(*, using: str = "default") -> None:
    url = getattr(settings, "FRONTEND_REVALIDATE_URL", "")
    secret = getattr(settings, "FRONTEND_REVALIDATE_SECRET", "")
    if not url or not secret:
        return

    def dispatch():
        thread = threading.Thread(
            target=_post_revalidation, args=(url, secret), daemon=True
        )
        thread.start()

    transaction.on_commit(dispatch, using=using, robust=True)
