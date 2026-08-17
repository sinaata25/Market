"""Best-effort SMS notifications for order lifecycle events."""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model

from accounts.sms import SmsDeliveryError, send_pattern_sms

logger = logging.getLogger(__name__)


def _send_safely(
    phone: str,
    pattern_code: str,
    params: dict[str, str],
    *,
    event: str,
) -> None:
    """Send one notification without allowing provider failures to escape."""
    try:
        send_pattern_sms(phone, pattern_code, params)
    except SmsDeliveryError as exc:
        # This includes uncertain delivery. Do not retry blindly because the
        # provider may already have accepted the original request.
        logger.warning(
            "Order SMS delivery failed (event=%s, recipient=***%s, error=%s)",
            event,
            phone[-2:],
            exc.__class__.__name__,
        )
    except Exception:
        # Delivery is deliberately best-effort, including unexpected errors.
        logger.exception(
            "Order SMS delivery failed (event=%s, recipient=***%s)",
            event,
            phone[-2:],
        )


def send_new_order_admin_notifications(
    customer_name: str,
    order_code: str,
    *,
    customer_phone: str = "",
    using: str = "default",
) -> None:
    """Notify every active full admin about a newly created order."""
    if not getattr(settings, "ORDER_SMS_ENABLED", False):
        return

    pattern_code = settings.IPPANEL["NEW_ORDER_PATTERN_CODE"]
    params = {
        "customer_name": customer_name.strip() or customer_phone,
        "order_code": order_code,
    }
    User = get_user_model()
    admin_phones = User.objects.using(using).filter(
        is_staff=True,
        is_active=True,
    ).values_list("phone", flat=True)

    for phone in admin_phones.iterator():
        _send_safely(
            phone,
            pattern_code,
            params,
            event="new_order",
        )


def send_order_status_notification(
    phone: str,
    order_code: str,
    status_label: str,
) -> None:
    """Notify the customer about one persisted order status transition."""
    if not getattr(settings, "ORDER_SMS_ENABLED", False):
        return

    _send_safely(
        phone,
        settings.IPPANEL["ORDER_STATUS_PATTERN_CODE"],
        {
            "order_code": order_code,
            "status": status_label,
        },
        event="status_change",
    )
