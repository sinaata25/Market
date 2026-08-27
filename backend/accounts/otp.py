"""Concurrency-safe issuance and one-time verification of login challenges."""

import logging
import math
import secrets
import time
import uuid
from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.db import DatabaseError, OperationalError, connection, transaction
from django.db.models import F, Q
from django.utils import timezone

from notifications.services.sms import (
    SmsDeliveryError,
    SmsDeliveryUncertain,
    send_otp_sms,
)

from .models import Otp

logger = logging.getLogger(__name__)
User = get_user_model()


class OtpRecentlySent(Exception):
    def __init__(
        self,
        retry_after: int,
        *,
        active_challenge: bool = False,
        expires_in: int = 0,
    ):
        self.retry_after = retry_after
        self.active_challenge = active_challenge
        self.expires_in = expires_in
        super().__init__(f"retry after {retry_after} seconds")


class OtpAttemptsExhausted(Exception):
    """Every current code was consumed after too many wrong attempts."""

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__("the current OTP must be replaced")


class InvalidOtp(Exception):
    pass


class InactiveOtpUser(Exception):
    pass


@dataclass(frozen=True)
class OtpIssueResult:
    expires_in: int
    resend_after: int
    delivery_status: str


def _generate_code(length: int) -> str:
    # A non-leading-zero value also matches patterns that define code as an integer.
    lower = 10 ** (length - 1)
    return str(lower + secrets.randbelow(9 * lower))


def _seconds_until(deadline, now) -> int:
    return max(1, math.ceil((deadline - now).total_seconds()))


def _remaining_resend_cooldown(challenge: Otp, now, cooldown: int) -> int:
    deadlines = []
    if challenge.resend_blocked_until:
        deadlines.append(challenge.resend_blocked_until)
    if challenge.sent_at:
        deadlines.append(
            challenge.sent_at + timezone.timedelta(seconds=cooldown)
        )
    future_deadlines = [deadline for deadline in deadlines if deadline > now]
    return _seconds_until(max(future_deadlines), now) if future_deadlines else 0


def _with_sqlite_lock_retry(operation):
    """Retry only SQLite's transient table-lock error around short DB writes."""

    for attempt in range(6):
        try:
            return operation()
        except OperationalError as exc:
            sqlite_locked = (
                connection.vendor == "sqlite" and "locked" in str(exc).lower()
            )
            if not sqlite_locked or attempt == 5:
                raise
            # At most 310 ms total; provider I/O is never inside this retry.
            time.sleep(0.01 * (2**attempt))


def _ensure_challenge(phone: str, now) -> None:
    # get_or_create handles the unique-phone race internally. No transaction is
    # kept open after this short insert/select operation.
    Otp.objects.get_or_create(
        phone=phone,
        defaults={"code_hash": "", "expires_at": now, "used": True},
    )


def _reserve_send_once(phone: str, code_hash: str, now, token: uuid.UUID) -> None:
    otp_settings = settings.SHOP
    cooldown = otp_settings["OTP_RESEND_COOLDOWN_SECONDS"]
    available_before = now - timezone.timedelta(seconds=cooldown)

    _ensure_challenge(phone, now)

    # This compare-and-set is a single short SQL write. It works even where
    # select_for_update() is ineffective (notably development SQLite), and it
    # prevents concurrent sends for the same phone without holding a lock while
    # IPPanel is contacted. A crashed/ambiguous reservation stays protected for
    # the normal resend cooldown to avoid duplicate paid SMS messages.
    claimed = (
        Otp.objects.filter(phone=phone)
        .filter(
            Q(resend_blocked_until__isnull=True)
            | Q(resend_blocked_until__lte=now)
        )
        .filter(Q(sent_at__isnull=True) | Q(sent_at__lte=available_before))
        .filter(Q(pending_code_hash="") | Q(pending_expires_at__lte=now))
        .update(
            pending_code_hash=code_hash,
            pending_expires_at=now
            + timezone.timedelta(seconds=otp_settings["OTP_TTL_SECONDS"]),
            pending_attempts=0,
            send_token=token,
            send_started_at=now,
            resend_blocked_until=None,
        )
    )
    if claimed:
        return

    challenge = Otp.objects.get(phone=phone)
    cooldown_deadlines = []
    if challenge.resend_blocked_until:
        cooldown_deadlines.append(challenge.resend_blocked_until)
    if challenge.sent_at:
        cooldown_deadlines.append(
            challenge.sent_at + timezone.timedelta(seconds=cooldown)
        )
    if challenge.pending_code_hash and challenge.send_started_at:
        # Never replace a still-verifiable pending code. It represents a send
        # whose final provider/DB outcome was not safely finalized.
        cooldown_deadlines.append(
            max(
                challenge.send_started_at + timezone.timedelta(seconds=cooldown),
                challenge.pending_expires_at or now,
            )
        )
    future_deadlines = [
        deadline for deadline in cooldown_deadlines if deadline > now
    ]
    retry_after = (
        _seconds_until(max(future_deadlines), now) if future_deadlines else 1
    )

    challenge_expiries = []
    if challenge.code_hash and not challenge.used and challenge.expires_at > now:
        challenge_expiries.append(challenge.expires_at)
    if (
        challenge.pending_code_hash
        and challenge.pending_expires_at
        and challenge.pending_expires_at > now
    ):
        challenge_expiries.append(challenge.pending_expires_at)
    raise OtpRecentlySent(
        retry_after,
        active_challenge=bool(challenge_expiries),
        expires_in=(
            _seconds_until(max(challenge_expiries), now)
            if challenge_expiries
            else 0
        ),
    )


def _reserve_send(phone: str, code_hash: str, now, token: uuid.UUID) -> None:
    def reserve():
        # A retention job may delete an old row in the narrow gap between
        # get_or_create and the CAS update. Recreate/retry without ever calling
        # the provider unless a reservation was actually persisted.
        for attempt in range(3):
            try:
                return _reserve_send_once(phone, code_hash, now, token)
            except Otp.DoesNotExist:
                if attempt == 2:
                    raise

    _with_sqlite_lock_retry(reserve)


def _release_send(phone: str, token: uuid.UUID) -> None:
    """Remove only this caller's failed pending send, preserving the old OTP."""

    def release():
        with transaction.atomic():
            challenge = (
                Otp.objects.select_for_update()
                .filter(phone=phone, send_token=token)
                .first()
            )
            if challenge is None:
                return
            if not challenge.code_hash and challenge.sent_at is None:
                challenge.delete()
                return
            challenge.pending_code_hash = ""
            challenge.pending_expires_at = None
            challenge.pending_attempts = 0
            challenge.send_token = None
            challenge.send_started_at = None
            challenge.save(
                update_fields=[
                    "pending_code_hash",
                    "pending_expires_at",
                    "pending_attempts",
                    "send_token",
                    "send_started_at",
                ]
            )

    _with_sqlite_lock_retry(release)


def _safe_release_send(phone: str, token: uuid.UUID) -> None:
    try:
        _release_send(phone, token)
    except DatabaseError:
        # Preserve the original provider error. A leftover pending reservation
        # fails safe by blocking duplicate sends for the cooldown period.
        logger.exception("Could not release failed OTP send reservation")


def _finalize_send(
    phone: str,
    token: uuid.UUID,
    *,
    delivery_status: str,
    provider_message_id: str,
) -> None:
    # Promote the already-persisted pending hash atomically. If the database
    # becomes unavailable here, the pending hash remains usable by verify_otp().
    def finalize():
        return Otp.objects.filter(phone=phone, send_token=token).update(
            code_hash=F("pending_code_hash"),
            expires_at=F("pending_expires_at"),
            attempts=F("pending_attempts"),
            used=False,
            sent_at=F("send_started_at"),
            provider_message_id=provider_message_id,
            delivery_status=delivery_status,
            pending_code_hash="",
            pending_expires_at=None,
            pending_attempts=0,
            send_token=None,
            send_started_at=None,
        )

    updated = _with_sqlite_lock_retry(finalize)
    if not updated:
        raise SmsDeliveryError("OTP send reservation was no longer current")


def issue_otp(phone: str) -> OtpIssueResult:
    """Reserve, deliver and finalize an OTP without network I/O in a DB lock."""

    otp_settings = settings.SHOP
    now = timezone.now()
    code = _generate_code(otp_settings["OTP_LENGTH"])
    code_hash = make_password(code)
    token = uuid.uuid4()
    _reserve_send(phone, code_hash, now, token)

    try:
        delivery = send_otp_sms(phone, code)
    except SmsDeliveryUncertain:
        # A response timeout/drop may happen after IPPanel accepted the SMS. Keep
        # this exact code valid and enforce cooldown; never blindly retry it.
        delivery_status = "unknown"
        provider_message_id = ""
    except SmsDeliveryError:
        _safe_release_send(phone, token)
        raise
    except Exception:
        _safe_release_send(phone, token)
        raise
    else:
        delivery_status = "accepted"
        provider_message_id = delivery.provider_message_id

    try:
        _finalize_send(
            phone,
            token,
            delivery_status=delivery_status,
            provider_message_id=provider_message_id,
        )
    except (DatabaseError, SmsDeliveryError):
        logger.exception("Could not finalize OTP delivery state")
        # Do not clear the pending state: it is intentionally verifiable and
        # cooldown-protected if the provider already accepted the request.
        delivery_status = "unknown"

    response_time = timezone.now()
    return OtpIssueResult(
        expires_in=_seconds_until(
            now
            + timezone.timedelta(seconds=otp_settings["OTP_TTL_SECONDS"]),
            response_time,
        ),
        resend_after=_seconds_until(
            now
            + timezone.timedelta(
                seconds=otp_settings["OTP_RESEND_COOLDOWN_SECONDS"]
            ),
            response_time,
        ),
        delivery_status=delivery_status,
    )


def _clear_pending(challenge: Otp) -> None:
    challenge.pending_code_hash = ""
    challenge.pending_expires_at = None
    challenge.pending_attempts = 0
    challenge.send_token = None
    challenge.send_started_at = None


def verify_otp(phone: str, code: str):
    """Consume a valid active/pending challenge exactly once."""

    otp_settings = settings.SHOP
    max_attempts = otp_settings["OTP_MAX_ATTEMPTS"]
    outcome = "invalid"
    retry_after = 0
    user = None

    with transaction.atomic():
        now = timezone.now()
        challenge = Otp.objects.select_for_update().filter(phone=phone).first()
        if challenge is None:
            outcome = "invalid"
        else:
            update_fields = set()

            active_valid = bool(
                challenge.code_hash
                and not challenge.used
                and challenge.expires_at > now
            )
            pending_valid = bool(
                challenge.pending_code_hash
                and challenge.pending_expires_at
                and challenge.pending_expires_at > now
            )

            if not active_valid and not pending_valid:
                if not challenge.used:
                    challenge.used = True
                    update_fields.add("used")
                if (
                    challenge.pending_expires_at
                    and challenge.pending_expires_at <= now
                ):
                    _clear_pending(challenge)
                    update_fields.update(
                        {
                            "pending_code_hash",
                            "pending_expires_at",
                            "pending_attempts",
                            "send_token",
                            "send_started_at",
                        }
                    )
                outcome = "invalid"
            else:
                matched_pending = pending_valid and check_password(
                    code, challenge.pending_code_hash
                )
                matched_active = active_valid and check_password(
                    code, challenge.code_hash
                )

                if not matched_pending and not matched_active:
                    if active_valid:
                        challenge.attempts += 1
                        update_fields.add("attempts")
                        if challenge.attempts >= max_attempts:
                            challenge.used = True
                            update_fields.add("used")

                    if pending_valid:
                        challenge.pending_attempts += 1
                        update_fields.add("pending_attempts")
                        if challenge.pending_attempts >= max_attempts:
                            # Preserve the provider cooldown before clearing the
                            # token, so a concurrent finalizer cannot resurrect
                            # the exhausted pending code or trigger a duplicate SMS.
                            if challenge.send_started_at:
                                pending_cooldown = (
                                    challenge.send_started_at
                                    + timezone.timedelta(
                                        seconds=otp_settings[
                                            "OTP_RESEND_COOLDOWN_SECONDS"
                                        ]
                                    )
                                )
                                if (
                                    challenge.resend_blocked_until is None
                                    or challenge.resend_blocked_until
                                    < pending_cooldown
                                ):
                                    challenge.resend_blocked_until = pending_cooldown
                                    update_fields.add("resend_blocked_until")
                            _clear_pending(challenge)
                            update_fields.update(
                                {
                                    "pending_code_hash",
                                    "pending_expires_at",
                                    "pending_attempts",
                                    "send_token",
                                    "send_started_at",
                                }
                            )

                    active_remaining = active_valid and not challenge.used
                    pending_remaining = bool(challenge.pending_code_hash)
                    if not active_remaining and not pending_remaining:
                        challenge.used = True
                        update_fields.add("used")
                        retry_after = _remaining_resend_cooldown(
                            challenge,
                            now,
                            otp_settings["OTP_RESEND_COOLDOWN_SECONDS"],
                        )
                        outcome = "exhausted"
                    else:
                        outcome = "invalid"
                else:
                    if matched_pending:
                        challenge.expires_at = challenge.pending_expires_at
                        challenge.sent_at = challenge.send_started_at or now
                        # The pending reservation has no committed provider
                        # metadata. Do not retain an older send's outbox ID
                        # or accepted status on the newly consumed code.
                        challenge.delivery_status = "unknown"
                        challenge.provider_message_id = ""
                        challenge.code_hash = ""
                        _clear_pending(challenge)
                        update_fields.update(
                            {
                                "sent_at",
                                "expires_at",
                                "delivery_status",
                                "provider_message_id",
                                "code_hash",
                                "pending_code_hash",
                                "pending_expires_at",
                                "pending_attempts",
                                "send_token",
                                "send_started_at",
                            }
                        )
                    elif challenge.pending_code_hash or challenge.send_token:
                        # A successful login revokes every outstanding code
                        # for the phone. A concurrent finalizer then fails its
                        # token CAS and cannot resurrect a second OTP.
                        _clear_pending(challenge)
                        update_fields.update(
                            {
                                "pending_code_hash",
                                "pending_expires_at",
                                "pending_attempts",
                                "send_token",
                                "send_started_at",
                            }
                        )
                    # If a reserve UPDATE was waiting on this row lock,
                    # PostgreSQL rechecks this marker and refuses it. Keep
                    # sent_at as the real provider request timestamp.
                    challenge.resend_blocked_until = now + timezone.timedelta(
                        seconds=otp_settings["OTP_RESEND_COOLDOWN_SECONDS"]
                    )
                    challenge.used = True
                    challenge.attempts = 0
                    update_fields.update(
                        {
                            "used",
                            "attempts",
                            "resend_blocked_until",
                        }
                    )

                    try:
                        user = User.objects.get(phone=phone)
                    except User.DoesNotExist:
                        user = User.objects.create_user(phone=phone)
                    outcome = "success" if user.is_active else "inactive"

            if update_fields:
                challenge.save(update_fields=sorted(update_fields))

    # Raise after the transaction so counters/consumption are never rolled back.
    if outcome == "exhausted":
        raise OtpAttemptsExhausted(retry_after)
    if outcome == "inactive":
        raise InactiveOtpUser
    if outcome != "success" or user is None:
        raise InvalidOtp
    return user
