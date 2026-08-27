"""Order-domain side effects that must run only after a successful commit."""

from functools import partial

from django.db import transaction

from notifications.services.sms import (
    send_new_order_admin_sms,
    send_order_status_changed_sms,
)


def schedule_new_order_admin_sms(order) -> None:
    """Register one immutable new-order notification event for commit."""

    full_name = str(order.full_name or "").strip()
    display_name = str(order.user.name or "").strip()
    customer_name = full_name or display_name or order.user.phone
    transaction.on_commit(
        partial(
            send_new_order_admin_sms,
            order_id=order.pk,
            order_number=order.code,
            customer_name=customer_name,
            order_total=order.total_price,
        ),
        robust=True,
    )


def schedule_order_status_changed_sms(order, previous_status: str) -> bool:
    """Register a customer SMS only for a real persisted status transition."""

    if previous_status == order.status:
        return False
    transaction.on_commit(
        partial(
            send_order_status_changed_sms,
            order_id=order.pk,
            owner_id=order.user_id,
            order_number=order.code,
            order_status=order.get_status_display(),
        ),
        robust=True,
    )
    return True
