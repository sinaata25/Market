"""Order lifecycle hooks which schedule notifications after commit."""

from functools import partial

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Order
from .notifications import (
    send_new_order_admin_notifications,
    send_order_status_notification,
)

_PREVIOUS_STATUS_ATTR = "_orders_previous_persisted_status"
_UNCHANGED = object()


def _notifications_enabled() -> bool:
    return bool(getattr(settings, "ORDER_SMS_ENABLED", False))


@receiver(
    pre_save,
    sender=Order,
    dispatch_uid="orders.capture_previous_status",
)
def capture_previous_status(
    sender,
    instance: Order,
    raw: bool = False,
    using: str = "default",
    update_fields=None,
    **kwargs,
) -> None:
    """Remember a status only when this save will persist a real change."""
    setattr(instance, _PREVIOUS_STATUS_ATTR, _UNCHANGED)
    if (
        raw
        or not _notifications_enabled()
        or instance._state.adding
        or (update_fields is not None and "status" not in update_fields)
    ):
        return

    previous_status = (
        sender._default_manager.using(using)
        .filter(pk=instance.pk)
        .values_list("status", flat=True)
        .first()
    )
    if previous_status is not None and previous_status != instance.status:
        setattr(instance, _PREVIOUS_STATUS_ATTR, previous_status)


@receiver(
    post_save,
    sender=Order,
    dispatch_uid="orders.schedule_sms_notifications",
)
def schedule_order_notifications(
    sender,
    instance: Order,
    created: bool,
    raw: bool = False,
    using: str = "default",
    **kwargs,
) -> None:
    """Schedule best-effort delivery only after the order transaction commits."""
    previous_status = getattr(instance, _PREVIOUS_STATUS_ATTR, _UNCHANGED)
    if hasattr(instance, _PREVIOUS_STATUS_ATTR):
        delattr(instance, _PREVIOUS_STATUS_ATTR)

    if raw or not _notifications_enabled():
        return

    if created:
        callback = partial(
            send_new_order_admin_notifications,
            instance.full_name,
            instance.code,
            customer_phone=instance.phone,
            using=using,
        )
    elif previous_status is not _UNCHANGED:
        callback = partial(
            send_order_status_notification,
            instance.phone,
            instance.code,
            instance.get_status_display(),
        )
    else:
        return

    # The callback functions isolate provider errors themselves. ``robust`` is
    # a final guard for unexpected notification bugs: an already committed
    # order must never turn into a failed API response because of SMS.
    transaction.on_commit(callback, using=using, robust=True)
