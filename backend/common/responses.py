"""قالب یکسان پاسخ‌های API: {ok: true, data} یا {ok: false, error}"""

from rest_framework import status as http
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def ok(data, status=http.HTTP_200_OK):
    return Response({"ok": True, "data": data}, status=status)


def fail(error: str, status=http.HTTP_400_BAD_REQUEST):
    return Response({"ok": False, "error": error}, status=status)


def first_error_message(detail) -> str:
    """اولین پیام خطای قابل‌فهم را از جزئیات خطای DRF بیرون می‌کشد."""
    if isinstance(detail, dict):
        for value in detail.values():
            msg = first_error_message(value)
            if msg:
                return msg
    elif isinstance(detail, list):
        for item in detail:
            msg = first_error_message(item)
            if msg:
                return msg
    elif detail:
        return str(detail)
    return ""


def api_exception_handler(exc, context):
    """همه‌ی خطاهای DRF (اعتبارسنجی، ۴۰۴، مجوز و ...) را به قالب یکسان تبدیل می‌کند."""
    response = drf_exception_handler(exc, context)
    if response is None:
        # خطای پیش‌بینی‌نشده — جنگو خودش ۵۰۰ لاگ می‌کند
        return None
    message = first_error_message(response.data) or "خطای نامشخص"
    return Response({"ok": False, "error": message}, status=response.status_code)
