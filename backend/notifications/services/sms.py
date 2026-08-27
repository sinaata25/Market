"""Central SMS delivery service for IPPanel approved patterns."""

import logging
from dataclasses import dataclass

import requests
from django.conf import settings
from django.contrib.auth import get_user_model

from accounts.roles import Role, role_of_record
from accounts.selectors import role_filter
from common.utils import iran_mobile_to_e164

logger = logging.getLogger(__name__)

OTP_PARAMETER = "otp_code"
ORDER_NUMBER_PARAMETER = "order_number"
CUSTOMER_NAME_PARAMETER = "customer_name"
ORDER_TOTAL_PARAMETER = "order_total"
ORDER_STATUS_PARAMETER = "order_status"


class SmsDeliveryError(Exception):
    """A definite/safe-to-resend failure, with provider details kept private."""


class SmsDeliveryUncertain(SmsDeliveryError):
    """The provider may have accepted the SMS; callers must not resend blindly."""


@dataclass(frozen=True)
class SmsDeliveryResult:
    provider_message_id: str = ""


def _masked_phone(phone: str) -> str:
    value = str(phone or "")
    return f"{value[:4]}***{value[-2:]}" if len(value) >= 6 else "***"


def _ambiguous_http_status(status_code: int) -> bool:
    # A gateway/server timeout or 5xx may be emitted after a downstream queue
    # accepted the message. Treat it conservatively when no idempotency key exists.
    return status_code == 408 or status_code >= 500


class ConsoleSmsBackend:
    """Local-only backend. It deliberately never logs message parameters."""

    def send_pattern(
        self,
        phone: str,
        pattern_code: str,
        parameters: dict,
        *,
        sms_type: str,
        order_id: int | None = None,
    ) -> SmsDeliveryResult:
        recipient = iran_mobile_to_e164(phone)
        logger.warning(
            "Development SMS suppressed (type=%s, pattern=%s, recipient=%s, order_id=%s)",
            sms_type,
            pattern_code,
            _masked_phone(recipient),
            order_id or "-",
        )
        return SmsDeliveryResult()


class IPPanelSmsBackend:
    """Client for IPPanel Edge's approved-pattern send endpoint."""

    def __init__(self, config: dict | None = None):
        self.config = config or settings.IPPANEL

    def send_pattern(
        self,
        phone: str,
        pattern_code: str,
        parameters: dict,
        *,
        sms_type: str,
        order_id: int | None = None,
    ) -> SmsDeliveryResult:
        recipient = iran_mobile_to_e164(phone)
        url = f"{self.config['BASE_URL'].rstrip('/')}/api/send"
        payload = {
            "sending_type": "pattern",
            "from_number": self.config["FROM_NUMBER"],
            "code": pattern_code,
            "recipients": [recipient],
            "params": parameters,
        }
        log_context = (
            sms_type,
            pattern_code,
            _masked_phone(recipient),
            order_id or "-",
        )

        try:
            response = requests.post(
                url,
                headers={
                    # Edge requires the raw API key, without a "Bearer" prefix.
                    "Authorization": self.config["API_KEY"],
                    "Content-Type": "application/json",
                },
                json=payload,
                allow_redirects=False,
                timeout=(
                    self.config["CONNECT_TIMEOUT"],
                    self.config["READ_TIMEOUT"],
                ),
            )
        except requests.ConnectTimeout as exc:
            logger.warning(
                "IPPanel connection failed "
                "(type=%s, pattern=%s, recipient=%s, order_id=%s, "
                "error=ConnectTimeout)",
                *log_context,
            )
            raise SmsDeliveryError("IPPanel connection failed") from exc
        except requests.RequestException as exc:
            logger.warning(
                "IPPanel response uncertain "
                "(type=%s, pattern=%s, recipient=%s, order_id=%s, error=%s)",
                *log_context,
                exc.__class__.__name__,
            )
            # Read timeouts and connection drops can happen after acceptance.
            raise SmsDeliveryUncertain("IPPanel delivery is uncertain") from exc

        try:
            body = response.json()
        except ValueError as exc:
            logger.warning(
                "IPPanel returned non-JSON "
                "(type=%s, pattern=%s, recipient=%s, order_id=%s, "
                "http_status=%s)",
                *log_context,
                response.status_code,
            )
            error_type = (
                SmsDeliveryUncertain
                if 200 <= response.status_code < 300
                or _ambiguous_http_status(response.status_code)
                else SmsDeliveryError
            )
            raise error_type("IPPanel returned an invalid response") from exc

        meta = body.get("meta") if isinstance(body, dict) else None
        data = body.get("data") if isinstance(body, dict) else None
        message_ids = data.get("message_outbox_ids") if isinstance(data, dict) else None
        accepted = (
            200 <= response.status_code < 300
            and isinstance(meta, dict)
            and meta.get("status") is True
            and isinstance(message_ids, list)
            and bool(message_ids)
        )
        if accepted:
            return SmsDeliveryResult(provider_message_id=str(message_ids[0]))

        message_code = meta.get("message_code") if isinstance(meta, dict) else None
        logger.warning(
            "IPPanel rejected or did not confirm SMS "
            "(type=%s, pattern=%s, recipient=%s, order_id=%s, "
            "http_status=%s, message_code=%s)",
            *log_context,
            response.status_code,
            message_code or "unknown",
        )
        if _ambiguous_http_status(response.status_code):
            raise SmsDeliveryUncertain("IPPanel server result was uncertain")
        if not 200 <= response.status_code < 300 or (
            isinstance(meta, dict) and meta.get("status") is False
        ):
            raise SmsDeliveryError("IPPanel rejected the message")
        # A malformed HTTP success might still represent an accepted send.
        raise SmsDeliveryUncertain("IPPanel delivery confirmation was malformed")


def get_sms_backend():
    if settings.OTP_SMS_BACKEND == "console":
        return ConsoleSmsBackend()
    if settings.OTP_SMS_BACKEND == "ippanel":
        return IPPanelSmsBackend()
    raise SmsDeliveryError("Unknown SMS backend")


def send_otp_sms(phone: str, code: str) -> SmsDeliveryResult:
    """Send a login code while keeping the OTP value out of every log."""

    return get_sms_backend().send_pattern(
        phone,
        settings.IPPANEL["OTP_PATTERN_CODE"],
        {OTP_PARAMETER: code},
        sms_type="otp",
    )


def _unique_valid_recipients(phones, *, sms_type: str, order_id: int) -> list[str]:
    recipients: set[str] = set()
    for phone in phones:
        try:
            recipients.add(iran_mobile_to_e164(phone))
        except (AttributeError, TypeError, ValueError):
            logger.warning(
                "SMS recipient skipped (type=%s, order_id=%s, reason=invalid_phone)",
                sms_type,
                order_id,
            )
    return sorted(recipients)


def _send_order_pattern(
    *,
    phones,
    pattern_code: str,
    parameters: dict,
    sms_type: str,
    order_id: int,
) -> None:
    recipients = _unique_valid_recipients(
        phones,
        sms_type=sms_type,
        order_id=order_id,
    )
    if not recipients:
        return

    try:
        backend = get_sms_backend()
    except Exception as exc:
        logger.error(
            "SMS backend unavailable (type=%s, pattern=%s, order_id=%s, error=%s)",
            sms_type,
            pattern_code,
            order_id,
            exc.__class__.__name__,
        )
        return

    for recipient in recipients:
        try:
            backend.send_pattern(
                recipient,
                pattern_code,
                parameters,
                sms_type=sms_type,
                order_id=order_id,
            )
        except Exception as exc:
            # Order state is already committed. Log safely and continue so one
            # provider/recipient failure cannot affect the order or other admins.
            logger.error(
                "SMS delivery failed (type=%s, pattern=%s, recipient=%s, order_id=%s, error=%s)",
                sms_type,
                pattern_code,
                _masked_phone(recipient),
                order_id,
                exc.__class__.__name__,
            )


def send_new_order_admin_sms(
    *,
    order_id: int,
    order_number: str,
    customer_name: str,
    order_total: int,
) -> None:
    """Notify every active shop admin, explicitly excluding the SEO role."""

    User = get_user_model()
    admin_roles = {
        Role.SUPERUSER,
        Role.MANAGER_ADMIN,
        Role.REGULAR_ADMIN,
    }
    phones = (
        User.objects.filter(is_active=True)
        .filter(role_filter(admin_roles))
        .values_list("phone", flat=True)
    )
    _send_order_pattern(
        phones=phones,
        pattern_code=settings.IPPANEL["NEW_ORDER_PATTERN_CODE"],
        parameters={
            ORDER_NUMBER_PARAMETER: str(order_number),
            CUSTOMER_NAME_PARAMETER: str(customer_name),
            ORDER_TOTAL_PARAMETER: str(order_total),
        },
        sms_type="new_order_admin",
        order_id=order_id,
    )


def send_order_status_changed_sms(
    *,
    order_id: int,
    owner_id: int,
    order_number: str,
    order_status: str,
) -> None:
    """Notify the current customer owner of one committed status transition."""

    User = get_user_model()
    owner = User.objects.filter(pk=owner_id).first()
    if owner is None or Role.CUSTOMER != role_of_record(owner):
        logger.info(
            "Order status SMS skipped (order_id=%s, reason=owner_not_customer)",
            order_id,
        )
        return

    _send_order_pattern(
        phones=[owner.phone],
        pattern_code=settings.IPPANEL["ORDER_STATUS_PATTERN_CODE"],
        parameters={
            ORDER_NUMBER_PARAMETER: str(order_number),
            ORDER_STATUS_PARAMETER: str(order_status),
        },
        sms_type="order_status_changed",
        order_id=order_id,
    )
