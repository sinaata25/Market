"""SMS delivery backends used by the OTP login flow."""

import logging
from dataclasses import dataclass

import requests
from django.conf import settings

from common.utils import iran_mobile_to_e164

logger = logging.getLogger(__name__)


class SmsDeliveryError(Exception):
    """A definite/safe-to-resend failure, with provider details kept private."""


class SmsDeliveryUncertain(SmsDeliveryError):
    """The provider may have accepted the SMS; callers must not resend blindly."""


@dataclass(frozen=True)
class SmsDeliveryResult:
    provider_message_id: str = ""


def _masked_phone(phone: str) -> str:
    return f"{phone[:4]}***{phone[-2:]}" if len(phone) >= 6 else "***"


def _ambiguous_http_status(status_code: int) -> bool:
    # A gateway/server timeout or 5xx may be emitted after a downstream queue
    # accepted the message. Treat it conservatively when no idempotency key exists.
    return status_code == 408 or status_code >= 500


class ConsoleSmsBackend:
    """Local-only backend. Production selection is rejected in settings.py."""

    def send_otp(self, phone: str, code: str) -> SmsDeliveryResult:
        logger.warning("Development OTP for %s: %s", _masked_phone(phone), code)
        return SmsDeliveryResult()


class IPPanelSmsBackend:
    """Minimal client for IPPanel Edge's approved-pattern send endpoint."""

    def __init__(self, config: dict | None = None):
        self.config = config or settings.IPPANEL

    def send_otp(self, phone: str, code: str) -> SmsDeliveryResult:
        url = f"{self.config['BASE_URL'].rstrip('/')}/api/send"
        payload = {
            "sending_type": "pattern",
            "from_number": self.config["FROM_NUMBER"],
            "code": self.config["PATTERN_CODE"],
            "recipients": [iran_mobile_to_e164(phone)],
            "params": {self.config["OTP_PARAMETER"]: code},
        }

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
            logger.warning("IPPanel connect timed out for %s", _masked_phone(phone))
            raise SmsDeliveryError("IPPanel connection failed") from exc
        except requests.RequestException as exc:
            logger.warning(
                "IPPanel response was uncertain for %s: %s",
                _masked_phone(phone),
                exc.__class__.__name__,
            )
            # Read timeouts and connection drops can happen after acceptance.
            raise SmsDeliveryUncertain("IPPanel delivery is uncertain") from exc

        try:
            body = response.json()
        except ValueError as exc:
            logger.warning(
                "IPPanel returned non-JSON response (status=%s)", response.status_code
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
            response.status_code == 200
            and isinstance(meta, dict)
            and meta.get("status") is True
            and isinstance(message_ids, list)
            and bool(message_ids)
        )
        if accepted:
            return SmsDeliveryResult(provider_message_id=str(message_ids[0]))

        message_code = meta.get("message_code") if isinstance(meta, dict) else None
        logger.warning(
            "IPPanel did not confirm OTP send (status=%s, message_code=%s)",
            response.status_code,
            message_code or "unknown",
        )
        if _ambiguous_http_status(response.status_code):
            raise SmsDeliveryUncertain("IPPanel server result was uncertain")
        # An explicit negative envelope/non-200 status is a definite rejection.
        if response.status_code != 200 or (
            isinstance(meta, dict) and meta.get("status") is False
        ):
            raise SmsDeliveryError("IPPanel rejected the message")
        # A malformed HTTP-200 success might still represent an accepted send.
        raise SmsDeliveryUncertain("IPPanel delivery confirmation was malformed")


def get_sms_backend():
    if settings.OTP_SMS_BACKEND == "console":
        return ConsoleSmsBackend()
    if settings.OTP_SMS_BACKEND == "ippanel":
        return IPPanelSmsBackend()
    raise SmsDeliveryError("Unknown SMS backend")


def send_otp_sms(phone: str, code: str) -> SmsDeliveryResult:
    return get_sms_backend().send_otp(phone, code)
