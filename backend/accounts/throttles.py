"""Atomic fixed-window OTP limits, separated by request IP and phone."""

import logging
import math

from django.core.cache import cache
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import APIException
from rest_framework.throttling import SimpleRateThrottle

from common.utils import normalize_phone

logger = logging.getLogger(__name__)


def _private_ident(scope: str, ident: str) -> str:
    """Keep enumerable phone/IP values out of shared cache keys."""

    return salted_hmac(
        "accounts.otp-throttle",
        f"{scope}:{ident}",
        algorithm="sha256",
    ).hexdigest()


class OtpRateLimitUnavailable(APIException):
    status_code = 503
    default_detail = "سامانه کنترل درخواست موقتاً در دسترس نیست؛ کمی بعد تلاش کنید"
    default_code = "otp_rate_limit_unavailable"
    error_code = "otp_rate_limit_unavailable"


class _AtomicFixedWindowThrottle(SimpleRateThrottle):
    """Use cache.add/incr instead of DRF's race-prone history get/set pair."""

    def allow_request(self, request, view):
        if self.rate is None:
            return True
        cache_key = self.get_cache_key(request, view)
        if cache_key is None:
            return True

        now = self.timer()
        bucket = int(now // self.duration)
        bucket_end = (bucket + 1) * self.duration
        self._retry_after = max(1, math.ceil(bucket_end - now))
        key = f"{cache_key}:{bucket}"
        timeout = self._retry_after + 1

        try:
            if cache.add(key, 1, timeout=timeout):
                count = 1
            else:
                try:
                    count = cache.incr(key)
                except ValueError:
                    # The key expired between add() and incr(); retry once safely.
                    if cache.add(key, 1, timeout=timeout):
                        count = 1
                    else:
                        count = cache.incr(key)
        except Exception as exc:
            # SMS is cost-sensitive: fail closed if the shared limiter is down.
            logger.exception("OTP rate-limit cache is unavailable")
            raise OtpRateLimitUnavailable from exc
        return count <= self.num_requests

    def wait(self):
        return getattr(self, "_retry_after", None)


class _IpThrottle(_AtomicFixedWindowThrottle):
    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {
            "scope": self.scope,
            "ident": _private_ident(self.scope, ident),
        }


class _PhoneThrottle(_AtomicFixedWindowThrottle):
    def get_cache_key(self, request, view):
        data = request.data
        raw_phone = data.get("phone", "") if hasattr(data, "get") else ""
        phone = normalize_phone(str(raw_phone))
        return self.cache_format % {
            "scope": self.scope,
            "ident": _private_ident(self.scope, phone),
        }


class OtpSendIpThrottle(_IpThrottle):
    scope = "otp_send_ip"


class OtpSendPhoneThrottle(_PhoneThrottle):
    scope = "otp_send_phone"


class OtpVerifyIpThrottle(_IpThrottle):
    scope = "otp_verify_ip"


class OtpVerifyPhoneThrottle(_PhoneThrottle):
    scope = "otp_verify_phone"
