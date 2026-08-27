import os
import uuid
from datetime import timedelta
from io import StringIO
from queue import Queue
from threading import Barrier, Event, Thread
from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.management import call_command
from django.db import DatabaseError, close_old_connections, connection
from django.test import (
    SimpleTestCase,
    TestCase,
    TransactionTestCase,
    override_settings,
)
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from carts.models import Cart
from config.settings import env_bool, env_float

from .models import Otp
from common.utils import iran_mobile_to_e164, is_valid_iran_mobile

from .otp import (
    InvalidOtp,
    OtpAttemptsExhausted,
    OtpRecentlySent,
    _finalize_send,
    _reserve_send,
    issue_otp,
    verify_otp,
)
from notifications.services.sms import (
    ConsoleSmsBackend,
    IPPanelSmsBackend,
    SmsDeliveryError,
    SmsDeliveryResult,
    SmsDeliveryUncertain,
    send_otp_sms,
)
from .throttles import OtpSendIpThrottle

User = get_user_model()

TEST_SHOP = {
    "OTP_LENGTH": 4,
    "OTP_TTL_SECONDS": 300,
    "OTP_RESEND_COOLDOWN_SECONDS": 60,
    "OTP_MAX_ATTEMPTS": 5,
    "OTP_RETENTION_DAYS": 7,
    "SHIPPING_PRICE": 60_000,
    "FREE_SHIPPING_THRESHOLD": 2_000_000,
}

FAST_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

IPPANEL_CONFIG = {
    "BASE_URL": "https://edge.ippanel.com/v1",
    "API_KEY": "test-api-key",
    "FROM_NUMBER": "+983000505",
    "OTP_PATTERN_CODE": "b9f8d6co8e5z6de",
    "NEW_ORDER_PATTERN_CODE": "3v0og6lgz3ixp8i",
    "ORDER_STATUS_PATTERN_CODE": "fivdiyj4psxj94k",
    "CONNECT_TIMEOUT": 3.0,
    "READ_TIMEOUT": 10.0,
}


def accepted_response(message_id=1123594208):
    response = Mock(status_code=200)
    response.json.return_value = {
        "data": {"message_outbox_ids": [message_id]},
        "meta": {"status": True, "message_code": "200-1"},
    }
    return response


class IPPanelSmsBackendTests(SimpleTestCase):
    def test_console_backend_never_logs_the_otp_value(self):
        with self.assertLogs("notifications.services.sms", level="WARNING") as logs:
            ConsoleSmsBackend().send_pattern(
                "09121234567",
                "b9f8d6co8e5z6de",
                {"otp_code": "7294"},
                sms_type="otp",
            )

        self.assertNotIn("7294", " ".join(logs.output))

    @override_settings(IPPANEL=IPPANEL_CONFIG)
    @patch("notifications.services.sms.get_sms_backend")
    def test_otp_uses_the_configured_pattern_and_exact_variable(self, get_backend):
        backend = get_backend.return_value
        backend.send_pattern.return_value = SmsDeliveryResult("42")

        result = send_otp_sms("09121234567", "7294")

        self.assertEqual(result.provider_message_id, "42")
        backend.send_pattern.assert_called_once_with(
            "09121234567",
            "b9f8d6co8e5z6de",
            {"otp_code": "7294"},
            sms_type="otp",
        )

    @patch("notifications.services.sms.requests.post")
    def test_sends_the_documented_pattern_payload(self, post):
        post.return_value = accepted_response()

        result = IPPanelSmsBackend(IPPANEL_CONFIG).send_pattern(
            "09121234567",
            "approved-pattern",
            {"code": "1234"},
            sms_type="otp",
        )

        self.assertEqual(result.provider_message_id, "1123594208")
        post.assert_called_once_with(
            "https://edge.ippanel.com/v1/api/send",
            headers={
                "Authorization": "test-api-key",
                "Content-Type": "application/json",
            },
            json={
                "sending_type": "pattern",
                "from_number": "+983000505",
                "code": "approved-pattern",
                "recipients": ["+989121234567"],
                "params": {"code": "1234"},
            },
            allow_redirects=False,
            timeout=(3.0, 10.0),
        )

    @patch("notifications.services.sms.requests.post")
    def test_rejects_an_unsuccessful_provider_envelope(self, post):
        response = Mock(status_code=422)
        response.json.return_value = {
            "data": None,
            "meta": {"status": False, "message_code": "400-2"},
        }
        post.return_value = response

        with self.assertRaises(SmsDeliveryError):
            IPPanelSmsBackend(IPPANEL_CONFIG).send_pattern(
                "09121234567",
                "approved-pattern",
                {"code": "1234"},
                sms_type="otp",
            )

    @patch("notifications.services.sms.requests.post")
    def test_server_error_is_delivery_ambiguous(self, post):
        response = Mock(status_code=503)
        response.json.return_value = {
            "data": None,
            "meta": {"status": False, "message_code": "500-1"},
        }
        post.return_value = response

        with self.assertRaises(SmsDeliveryUncertain):
            IPPanelSmsBackend(IPPANEL_CONFIG).send_pattern(
                "09121234567",
                "approved-pattern",
                {"code": "1234"},
                sms_type="otp",
            )

    @patch("notifications.services.sms.requests.post")
    def test_rejects_a_malformed_success_response(self, post):
        response = Mock(status_code=200)
        response.json.return_value = {"data": {}, "meta": {"status": True}}
        post.return_value = response

        with self.assertRaises(SmsDeliveryUncertain):
            IPPanelSmsBackend(IPPANEL_CONFIG).send_pattern(
                "09121234567",
                "approved-pattern",
                {"code": "1234"},
                sms_type="otp",
            )

    @patch("notifications.services.sms.requests.post", side_effect=requests.Timeout)
    def test_timeout_is_not_retried(self, post):
        with self.assertRaises(SmsDeliveryUncertain):
            IPPanelSmsBackend(IPPANEL_CONFIG).send_pattern(
                "09121234567",
                "approved-pattern",
                {"code": "1234"},
                sms_type="otp",
            )
        self.assertEqual(post.call_count, 1)

    @patch(
        "notifications.services.sms.requests.post",
        side_effect=requests.ConnectTimeout,
    )
    def test_connect_timeout_is_a_definite_failure(self, post):
        with self.assertRaises(SmsDeliveryError) as caught:
            IPPanelSmsBackend(IPPANEL_CONFIG).send_pattern(
                "09121234567",
                "approved-pattern",
                {"code": "1234"},
                sms_type="otp",
            )
        self.assertNotIsInstance(caught.exception, SmsDeliveryUncertain)
        self.assertEqual(post.call_count, 1)

    @override_settings(IPPANEL=IPPANEL_CONFIG)
    @patch(
        "notifications.services.sms.requests.post",
        side_effect=requests.Timeout,
    )
    def test_network_failure_logs_neither_otp_nor_api_key(self, _post):
        otp = "7294"
        with (
            self.assertLogs("notifications.services.sms", level="WARNING") as logs,
            self.assertRaises(SmsDeliveryUncertain),
        ):
            send_otp_sms("09121234567", otp)

        output = " ".join(logs.output)
        self.assertNotIn(otp, output)
        self.assertNotIn(IPPANEL_CONFIG["API_KEY"], output)
        self.assertIn(IPPANEL_CONFIG["OTP_PATTERN_CODE"], output)


class PhoneNormalizationTests(SimpleTestCase):
    def test_rejects_non_ascii_unicode_digit_sets(self):
        devanagari = "09१२३४५६७८९"
        full_width = "09１２３４５６７８９"
        self.assertFalse(is_valid_iran_mobile(devanagari))
        self.assertFalse(is_valid_iran_mobile(full_width))
        with self.assertRaises(ValueError):
            iran_mobile_to_e164(devanagari)

    def test_default_ip_identity_ignores_spoofed_forwarded_for(self):
        factory = APIRequestFactory()
        first = factory.get(
            "/api/auth/me",
            REMOTE_ADDR="10.0.0.8",
            HTTP_X_FORWARDED_FOR="198.51.100.10",
        )
        second = factory.get(
            "/api/auth/me",
            REMOTE_ADDR="10.0.0.8",
            HTTP_X_FORWARDED_FOR="203.0.113.99",
        )
        throttle = OtpSendIpThrottle()
        first_key = throttle.get_cache_key(first, None)
        self.assertEqual(first_key, throttle.get_cache_key(second, None))
        self.assertNotIn("10.0.0.8", first_key)


class SettingsParserTests(SimpleTestCase):
    @patch.dict(os.environ, {"OTP_TEST_BOOL": "ture"})
    def test_invalid_boolean_configuration_fails_closed(self):
        with self.assertRaises(ImproperlyConfigured):
            env_bool("OTP_TEST_BOOL")

    @patch.dict(os.environ, {"OTP_TEST_FLOAT": "NaN"})
    def test_non_finite_timeout_configuration_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            env_float("OTP_TEST_FLOAT", 3.0)


@override_settings(SHOP=TEST_SHOP, PASSWORD_HASHERS=FAST_HASHERS)
class OtpServiceTests(TestCase):
    phone = "09121234567"

    @patch("accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42"))
    def test_issue_stores_only_a_hash(self, send_sms):
        issued = issue_otp(self.phone)
        code = send_sms.call_args.args[1]
        challenge = Otp.objects.get(phone=self.phone)

        self.assertEqual(len(code), 4)
        self.assertTrue(code.isdigit())
        self.assertNotEqual(challenge.code_hash, code)
        self.assertTrue(check_password(code, challenge.code_hash))
        self.assertEqual(challenge.provider_message_id, "42")
        self.assertEqual(issued.expires_in, 300)
        self.assertEqual(issued.resend_after, 60)
        self.assertEqual(issued.delivery_status, "accepted")
        self.assertEqual(challenge.delivery_status, "accepted")
        self.assertNotIn("code", [field.name for field in Otp._meta.fields])

    @patch("accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42"))
    def test_provider_call_is_outside_the_service_transaction(self, send_sms):
        baseline_depth = len(connection.atomic_blocks)

        def assert_transaction_depth(_phone, _code):
            self.assertEqual(len(connection.atomic_blocks), baseline_depth)
            return SmsDeliveryResult("42")

        send_sms.side_effect = assert_transaction_depth
        issue_otp(self.phone)

    @patch("accounts.otp._reserve_send_once")
    def test_reservation_retries_if_retention_deleted_the_row(self, reserve_once):
        reserve_once.side_effect = [Otp.DoesNotExist, None]

        _reserve_send(self.phone, "hash", timezone.now(), uuid.uuid4())

        self.assertEqual(reserve_once.call_count, 2)

    def test_exhausting_a_pending_code_prevents_finalizer_resurrection(self):
        token = uuid.uuid4()
        correct_code = "1234"
        _reserve_send(
            self.phone,
            make_password(correct_code),
            timezone.now(),
            token,
        )

        for _ in range(TEST_SHOP["OTP_MAX_ATTEMPTS"] - 1):
            with self.assertRaises(InvalidOtp):
                verify_otp(self.phone, "9999")
        with self.assertRaises(OtpAttemptsExhausted):
            verify_otp(self.phone, "9999")

        challenge = Otp.objects.get(phone=self.phone)
        self.assertEqual(challenge.pending_code_hash, "")
        self.assertEqual(challenge.pending_attempts, 0)
        self.assertIsNone(challenge.send_token)
        self.assertGreater(challenge.resend_blocked_until, timezone.now())
        with self.assertRaises(SmsDeliveryError):
            _finalize_send(
                self.phone,
                token,
                delivery_status="accepted",
                provider_message_id="42",
            )
        with self.assertRaises(InvalidOtp):
            verify_otp(self.phone, correct_code)

    @patch("accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42"))
    def test_cooldown_blocks_a_second_delivery(self, send_sms):
        issue_otp(self.phone)
        with self.assertRaises(OtpRecentlySent) as caught:
            issue_otp(self.phone)

        self.assertGreater(caught.exception.retry_after, 0)
        self.assertLessEqual(caught.exception.retry_after, 60)
        self.assertEqual(send_sms.call_count, 1)

    def test_failed_resend_preserves_the_previous_challenge(self):
        with patch(
            "accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("old-id")
        ) as first_send:
            issue_otp(self.phone)
            old_code = first_send.call_args.args[1]

        challenge = Otp.objects.get(phone=self.phone)
        old_hash = challenge.code_hash
        wrong_code = "0000" if old_code != "0000" else "1111"
        with self.assertRaises(InvalidOtp):
            verify_otp(self.phone, wrong_code)
        challenge.refresh_from_db()
        self.assertEqual(challenge.attempts, 1)
        challenge.sent_at = timezone.now() - timedelta(seconds=61)
        challenge.save(update_fields=["sent_at"])

        with patch(
            "accounts.otp.send_otp_sms", side_effect=SmsDeliveryError("down")
        ):
            with self.assertRaises(SmsDeliveryError):
                issue_otp(self.phone)

        challenge.refresh_from_db()
        self.assertEqual(challenge.code_hash, old_hash)
        self.assertEqual(challenge.provider_message_id, "old-id")
        self.assertFalse(challenge.used)
        self.assertEqual(challenge.attempts, 1)
        self.assertEqual(challenge.pending_code_hash, "")
        self.assertEqual(challenge.pending_attempts, 0)
        self.assertIsNone(challenge.send_token)
        self.assertTrue(check_password(old_code, challenge.code_hash))

    def test_ambiguous_delivery_keeps_the_new_code_valid_and_cooldown_active(self):
        with patch(
            "accounts.otp.send_otp_sms",
            side_effect=SmsDeliveryUncertain("read timeout"),
        ) as send_sms:
            issued = issue_otp(self.phone)
            code = send_sms.call_args.args[1]

        challenge = Otp.objects.get(phone=self.phone)
        self.assertEqual(issued.delivery_status, "unknown")
        self.assertEqual(challenge.delivery_status, "unknown")
        self.assertTrue(check_password(code, challenge.code_hash))
        with self.assertRaises(OtpRecentlySent):
            issue_otp(self.phone)
        self.assertEqual(verify_otp(self.phone, code).phone, self.phone)

    def test_pending_code_survives_a_post_delivery_database_failure(self):
        with patch(
            "accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42")
        ) as send_sms, patch(
            "accounts.otp._finalize_send",
            side_effect=DatabaseError("database unavailable"),
        ):
            issued = issue_otp(self.phone)
            code = send_sms.call_args.args[1]

        self.assertEqual(issued.delivery_status, "unknown")
        challenge = Otp.objects.get(phone=self.phone)
        self.assertTrue(check_password(code, challenge.pending_code_hash))
        self.assertEqual(challenge.pending_attempts, 0)
        self.assertIsNotNone(challenge.send_token)
        wrong_code = "0000" if code != "0000" else "1111"
        with self.assertRaises(InvalidOtp):
            verify_otp(self.phone, wrong_code)
        challenge.refresh_from_db()
        self.assertEqual(challenge.pending_attempts, 1)
        self.assertEqual(verify_otp(self.phone, code).phone, self.phone)

    def test_pending_resend_has_attempts_independent_from_the_old_code(self):
        with patch(
            "accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("old")
        ) as first_send:
            issue_otp(self.phone)
            old_code = first_send.call_args.args[1]

        old_wrong = "9999" if old_code != "9999" else "8888"
        for _ in range(TEST_SHOP["OTP_MAX_ATTEMPTS"] - 1):
            with self.assertRaises(InvalidOtp):
                verify_otp(self.phone, old_wrong)
        Otp.objects.filter(phone=self.phone).update(
            sent_at=timezone.now() - timedelta(seconds=61)
        )

        new_code = None

        def fail_old_generation_while_new_send_is_pending(phone, code):
            nonlocal new_code
            new_code = code
            wrong_code = next(
                candidate
                for candidate in ("0000", "1111", "2222")
                if candidate not in {old_code, code}
            )
            with self.assertRaises(InvalidOtp):
                verify_otp(phone, wrong_code)
            challenge = Otp.objects.get(phone=phone)
            self.assertTrue(challenge.used)
            self.assertEqual(
                challenge.attempts, TEST_SHOP["OTP_MAX_ATTEMPTS"]
            )
            self.assertEqual(challenge.pending_attempts, 1)
            return SmsDeliveryResult("new")

        with patch(
            "accounts.otp.send_otp_sms",
            side_effect=fail_old_generation_while_new_send_is_pending,
        ):
            issue_otp(self.phone)

        challenge = Otp.objects.get(phone=self.phone)
        self.assertFalse(challenge.used)
        self.assertEqual(challenge.attempts, 1)
        self.assertEqual(challenge.pending_attempts, 0)
        self.assertEqual(verify_otp(self.phone, new_code).phone, self.phone)

    def test_a_valid_pending_code_cannot_be_overwritten(self):
        with patch(
            "accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42")
        ) as first_send, patch(
            "accounts.otp._finalize_send",
            side_effect=DatabaseError("database unavailable"),
        ):
            issue_otp(self.phone)
            pending_code = first_send.call_args.args[1]

        Otp.objects.filter(phone=self.phone).update(
            send_started_at=timezone.now() - timedelta(seconds=61)
        )
        with patch(
            "accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("43")
        ) as replacement_send:
            with self.assertRaises(OtpRecentlySent) as caught:
                issue_otp(self.phone)

        self.assertTrue(caught.exception.active_challenge)
        self.assertGreater(caught.exception.expires_in, 0)
        replacement_send.assert_not_called()
        self.assertEqual(verify_otp(self.phone, pending_code).phone, self.phone)

    def test_verification_during_resend_prevents_a_second_code_resurrection(self):
        with patch(
            "accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("old")
        ) as first_send:
            issue_otp(self.phone)
            old_code = first_send.call_args.args[1]

        Otp.objects.filter(phone=self.phone).update(
            sent_at=timezone.now() - timedelta(seconds=61)
        )
        replacement_code = None

        def verify_while_provider_is_processing(phone, code):
            nonlocal replacement_code
            replacement_code = code
            self.assertEqual(verify_otp(phone, old_code).phone, self.phone)
            return SmsDeliveryResult("new")

        with patch(
            "accounts.otp.send_otp_sms",
            side_effect=verify_while_provider_is_processing,
        ):
            issued = issue_otp(self.phone)

        self.assertEqual(issued.delivery_status, "unknown")
        challenge = Otp.objects.get(phone=self.phone)
        self.assertTrue(challenge.used)
        self.assertEqual(challenge.delivery_status, "accepted")
        self.assertEqual(challenge.provider_message_id, "old")
        self.assertEqual(challenge.pending_code_hash, "")
        self.assertIsNone(challenge.send_token)
        self.assertGreater(
            challenge.resend_blocked_until,
            timezone.now(),
        )
        with self.assertRaises(InvalidOtp):
            verify_otp(self.phone, replacement_code)

    def test_pending_code_consumption_does_not_retain_old_provider_metadata(self):
        consumed_code = None

        def verify_pending_while_provider_is_processing(phone, code):
            nonlocal consumed_code
            consumed_code = code
            self.assertEqual(verify_otp(phone, code).phone, self.phone)
            return SmsDeliveryResult("new")

        with patch(
            "accounts.otp.send_otp_sms",
            side_effect=verify_pending_while_provider_is_processing,
        ):
            issued = issue_otp(self.phone)

        self.assertEqual(issued.delivery_status, "unknown")
        challenge = Otp.objects.get(phone=self.phone)
        self.assertTrue(challenge.used)
        self.assertEqual(challenge.delivery_status, "unknown")
        self.assertEqual(challenge.provider_message_id, "")
        self.assertEqual(challenge.pending_code_hash, "")
        self.assertIsNone(challenge.send_token)
        self.assertGreater(challenge.sent_at, timezone.now() - timedelta(seconds=5))
        with self.assertRaises(InvalidOtp):
            verify_otp(self.phone, consumed_code)

    def test_successful_resend_replaces_the_previous_code(self):
        with patch(
            "accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("first")
        ) as first_send:
            issue_otp(self.phone)
            first_code = first_send.call_args.args[1]

        Otp.objects.filter(phone=self.phone).update(
            sent_at=timezone.now() - timedelta(seconds=61)
        )
        with patch(
            "accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("second")
        ) as second_send:
            issue_otp(self.phone)
            second_code = second_send.call_args.args[1]

        if first_code == second_code:  # practically impossible; keep the test deterministic
            self.skipTest("secure generator produced the same code twice")
        with self.assertRaises(InvalidOtp):
            verify_otp(self.phone, first_code)
        self.assertEqual(verify_otp(self.phone, second_code).phone, self.phone)

    @patch("accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42"))
    def test_valid_code_is_single_use_and_creates_unusable_password_user(self, send_sms):
        issue_otp(self.phone)
        code = send_sms.call_args.args[1]

        user = verify_otp(self.phone, code)

        self.assertEqual(user.phone, self.phone)
        self.assertFalse(user.has_usable_password())
        self.assertTrue(Otp.objects.get(phone=self.phone).used)
        with self.assertRaises(InvalidOtp):
            verify_otp(self.phone, code)
        with self.assertRaises(OtpRecentlySent) as caught:
            issue_otp(self.phone)
        self.assertFalse(caught.exception.active_challenge)
        self.assertEqual(send_sms.call_count, 1)

    @patch("accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42"))
    def test_fifth_wrong_attempt_consumes_only_the_current_code(self, send_sms):
        issue_otp(self.phone)
        correct_code = send_sms.call_args.args[1]
        wrong_code = "9999" if correct_code != "9999" else "8888"

        for _ in range(TEST_SHOP["OTP_MAX_ATTEMPTS"] - 1):
            with self.assertRaises(InvalidOtp):
                verify_otp(self.phone, wrong_code)
        with self.assertRaises(OtpAttemptsExhausted):
            verify_otp(self.phone, wrong_code)

        challenge = Otp.objects.get(phone=self.phone)
        self.assertEqual(challenge.attempts, TEST_SHOP["OTP_MAX_ATTEMPTS"])
        self.assertTrue(challenge.used)
        with self.assertRaises(InvalidOtp):
            verify_otp(self.phone, correct_code)

    @patch("accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42"))
    def test_four_wrong_attempts_still_allow_the_correct_code(self, send_sms):
        issue_otp(self.phone)
        correct_code = send_sms.call_args.args[1]
        wrong_code = "9999" if correct_code != "9999" else "8888"

        for _ in range(TEST_SHOP["OTP_MAX_ATTEMPTS"] - 1):
            with self.assertRaises(InvalidOtp):
                verify_otp(self.phone, wrong_code)

        self.assertEqual(verify_otp(self.phone, correct_code).phone, self.phone)

    def test_exhausted_code_can_be_replaced_after_normal_send_cooldown(self):
        with patch(
            "accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("first")
        ) as first_send:
            issue_otp(self.phone)
            first_code = first_send.call_args.args[1]

        wrong_code = "9999" if first_code != "9999" else "8888"
        for _ in range(TEST_SHOP["OTP_MAX_ATTEMPTS"] - 1):
            with self.assertRaises(InvalidOtp):
                verify_otp(self.phone, wrong_code)
        with self.assertRaises(OtpAttemptsExhausted) as exhausted:
            verify_otp(self.phone, wrong_code)
        self.assertGreater(exhausted.exception.retry_after, 0)

        with self.assertRaises(OtpRecentlySent):
            issue_otp(self.phone)

        Otp.objects.filter(phone=self.phone).update(
            sent_at=timezone.now() - timedelta(seconds=61)
        )
        with patch(
            "accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("second")
        ) as second_send:
            issue_otp(self.phone)
            second_code = second_send.call_args.args[1]

        challenge = Otp.objects.get(phone=self.phone)
        self.assertFalse(challenge.used)
        self.assertEqual(challenge.attempts, 0)
        self.assertEqual(verify_otp(self.phone, second_code).phone, self.phone)

    def test_exhausted_code_can_be_replaced_immediately_after_cooldown(self):
        with patch(
            "accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("first")
        ) as first_send:
            issue_otp(self.phone)
            first_code = first_send.call_args.args[1]

        Otp.objects.filter(phone=self.phone).update(
            sent_at=timezone.now() - timedelta(seconds=61)
        )
        wrong_code = "9999" if first_code != "9999" else "8888"
        for _ in range(TEST_SHOP["OTP_MAX_ATTEMPTS"] - 1):
            with self.assertRaises(InvalidOtp):
                verify_otp(self.phone, wrong_code)
        with self.assertRaises(OtpAttemptsExhausted) as exhausted:
            verify_otp(self.phone, wrong_code)
        self.assertEqual(exhausted.exception.retry_after, 0)

        with patch(
            "accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("second")
        ) as second_send:
            issue_otp(self.phone)
            second_code = second_send.call_args.args[1]

        self.assertEqual(verify_otp(self.phone, second_code).phone, self.phone)

    def test_successful_resend_resets_failed_attempts(self):
        with patch(
            "accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("first")
        ):
            issue_otp(self.phone)
        with self.assertRaises(InvalidOtp):
            verify_otp(self.phone, "0000")

        self.assertEqual(Otp.objects.get(phone=self.phone).attempts, 1)

        Otp.objects.filter(phone=self.phone).update(
            sent_at=timezone.now() - timedelta(seconds=61)
        )
        with patch(
            "accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("second")
        ):
            issue_otp(self.phone)

        self.assertEqual(Otp.objects.get(phone=self.phone).attempts, 0)

    @patch("accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42"))
    def test_expired_code_is_rejected_and_consumed(self, send_sms):
        issue_otp(self.phone)
        code = send_sms.call_args.args[1]
        Otp.objects.filter(phone=self.phone).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        with self.assertRaises(InvalidOtp):
            verify_otp(self.phone, code)
        self.assertTrue(Otp.objects.get(phone=self.phone).used)

    @patch("accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42"))
    def test_retention_command_deletes_only_old_inactive_rows(self, _send_sms):
        issue_otp(self.phone)
        Otp.objects.filter(phone=self.phone).update(
            sent_at=timezone.now() - timedelta(days=8),
            expires_at=timezone.now() - timedelta(days=8),
            used=True,
        )
        output = StringIO()
        call_command("purge_otps", stdout=output)
        self.assertFalse(Otp.objects.exists())
        self.assertIn("Deleted 1", output.getvalue())

    def test_retention_command_deletes_stale_pending_rows(self):
        with patch(
            "accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42")
        ), patch(
            "accounts.otp._finalize_send",
            side_effect=DatabaseError("database unavailable"),
        ):
            issue_otp(self.phone)

        old = timezone.now() - timedelta(days=8)
        Otp.objects.filter(phone=self.phone).update(
            pending_expires_at=old,
            send_started_at=old,
        )
        call_command("purge_otps", stdout=StringIO())

        self.assertFalse(Otp.objects.exists())


class UserPhoneCanonicalizationTests(TestCase):
    def test_direct_save_normalizes_phone_and_manager_lookup_is_canonical(self):
        user = User(phone="۰۹۱۲ ۱۲۳ ۴۵۶۷")
        user.set_unusable_password()
        user.save()
        self.assertEqual(user.phone, "09121234567")

        found, created = User.objects.get_or_create(phone="+98 912 123 4567")
        self.assertFalse(created)
        self.assertEqual(found.pk, user.pk)

    def test_direct_save_rejects_non_ascii_digit_sets(self):
        user = User(phone="09१२३४५६७८९")
        user.set_unusable_password()
        with self.assertRaises(ValidationError):
            user.save()


@override_settings(SHOP=TEST_SHOP, PASSWORD_HASHERS=FAST_HASHERS)
class OtpConcurrencyTests(TransactionTestCase):
    def _run_issue(self, phone: str, errors: Queue):
        close_old_connections()
        try:
            issue_otp(phone)
        except Exception as exc:
            errors.put(exc)
        finally:
            close_old_connections()

    def test_different_phone_provider_calls_overlap_without_a_database_lock(self):
        provider_barrier = Barrier(2)
        errors = Queue()

        def slow_delivery(_phone, _code):
            self.assertFalse(connection.in_atomic_block)
            provider_barrier.wait(timeout=3)
            return SmsDeliveryResult("42")

        with patch("accounts.otp.send_otp_sms", side_effect=slow_delivery):
            threads = [
                Thread(target=self._run_issue, args=(phone, errors))
                for phone in ("09121234567", "09121234568")
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertTrue(errors.empty(), list(errors.queue))
        self.assertEqual(Otp.objects.count(), 2)

    def test_same_phone_compare_and_set_allows_only_one_provider_call(self):
        provider_entered = Event()
        release_provider = Event()
        first_errors = Queue()
        second_errors = Queue()

        def slow_delivery(_phone, _code):
            provider_entered.set()
            release_provider.wait(timeout=3)
            return SmsDeliveryResult("42")

        with patch("accounts.otp.send_otp_sms", side_effect=slow_delivery) as send_sms:
            first = Thread(
                target=self._run_issue,
                args=("09121234567", first_errors),
            )
            first.start()
            self.assertTrue(provider_entered.wait(timeout=3))

            second = Thread(
                target=self._run_issue,
                args=("09121234567", second_errors),
            )
            second.start()
            second.join(timeout=3)
            release_provider.set()
            first.join(timeout=3)

        self.assertTrue(first_errors.empty(), list(first_errors.queue))
        self.assertFalse(second_errors.empty())
        self.assertIsInstance(second_errors.get(), OtpRecentlySent)
        self.assertEqual(send_sms.call_count, 1)


@override_settings(SHOP=TEST_SHOP, PASSWORD_HASHERS=FAST_HASHERS)
class OtpApiTests(TestCase):
    phone = "09121234567"

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf_headers(self):
        response = self.client.get("/api/auth/csrf")
        self.assertEqual(response.status_code, 200)
        token = self.client.cookies["csrftoken"].value
        return {"HTTP_X_CSRFTOKEN": token}

    def test_me_exposes_public_otp_ui_configuration_before_login(self):
        response = self.client.get("/api/auth/me")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["data"]["user"])
        self.assertEqual(
            response.data["data"]["otpConfig"],
            {"codeLength": 4, "expiresIn": 300, "resendAfter": 60},
        )

    @patch("accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42"))
    def test_send_requires_csrf_and_never_exposes_the_code(self, send_sms):
        denied = self.client.post(
            "/api/auth/otp/send", {"phone": self.phone}, format="json"
        )
        self.assertEqual(denied.status_code, 403)

        response = self.client.post(
            "/api/auth/otp/send",
            {"phone": "۰۹۱۲ ۱۲۳ ۴۵۶۷"},
            format="json",
            **self.csrf_headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["ok"])
        self.assertEqual(response.data["data"]["codeLength"], 4)
        self.assertEqual(response.data["data"]["deliveryStatus"], "accepted")
        self.assertNotIn("code", response.data["data"])
        self.assertNotIn("devCode", response.data["data"])
        self.assertNotIn("bypass", response.data["data"])
        self.assertEqual(Otp.objects.get().phone, self.phone)
        self.assertEqual(send_sms.call_args.args[0], self.phone)

    @patch("accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42"))
    def test_cooldown_returns_retry_after(self, send_sms):
        headers = self.csrf_headers()
        first = self.client.post(
            "/api/auth/otp/send", {"phone": self.phone}, format="json", **headers
        )
        second = self.client.post(
            "/api/auth/otp/send", {"phone": self.phone}, format="json", **headers
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertIn("Retry-After", second.headers)
        self.assertEqual(second.data["errorCode"], "otp_cooldown")
        self.assertTrue(second.data["data"]["activeChallenge"])
        self.assertEqual(second.data["data"]["codeLength"], 4)
        self.assertGreater(second.data["data"]["expiresIn"], 0)
        self.assertEqual(send_sms.call_count, 1)

    @patch("accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42"))
    def test_phone_throttle_limits_repeated_send_requests(self, send_sms):
        headers = self.csrf_headers()
        responses = [
            self.client.post(
                "/api/auth/otp/send",
                {"phone": self.phone},
                format="json",
                **headers,
            )
            for _ in range(6)
        ]

        self.assertEqual(responses[-1].status_code, 429)
        self.assertIn("تعداد درخواست‌ها", responses[-1].data["error"])
        self.assertEqual(responses[-1].data["errorCode"], "otp_rate_limited")
        self.assertIn("Retry-After", responses[-1].headers)
        self.assertEqual(send_sms.call_count, 1)

    @patch("accounts.otp.send_otp_sms", side_effect=SmsDeliveryError("down"))
    def test_provider_failure_is_sanitized_and_leaves_no_challenge(self, _send_sms):
        response = self.client.post(
            "/api/auth/otp/send",
            {"phone": self.phone},
            format="json",
            **self.csrf_headers(),
        )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.data["ok"])
        self.assertEqual(response.data["errorCode"], "otp_delivery_failed")
        self.assertNotIn("IPPanel", response.data["error"])
        self.assertFalse(Otp.objects.exists())

    def test_rate_limit_cache_failure_returns_503_without_sending(self):
        headers = self.csrf_headers()
        with patch(
            "accounts.throttles.cache.add",
            side_effect=ConnectionError("redis unavailable"),
        ), patch("accounts.otp.send_otp_sms") as send_sms:
            response = self.client.post(
                "/api/auth/otp/send",
                {"phone": self.phone},
                format="json",
                **headers,
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.data["errorCode"],
            "otp_rate_limit_unavailable",
        )
        send_sms.assert_not_called()
        self.assertFalse(Otp.objects.exists())

    @patch(
        "accounts.otp.send_otp_sms",
        side_effect=SmsDeliveryUncertain("read timeout"),
    )
    def test_ambiguous_delivery_returns_202_and_code_remains_usable(self, send_sms):
        headers = self.csrf_headers()
        response = self.client.post(
            "/api/auth/otp/send",
            {"phone": self.phone},
            format="json",
            **headers,
        )
        code = send_sms.call_args.args[1]

        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.data["ok"])
        self.assertEqual(response.data["data"]["deliveryStatus"], "unknown")
        verified = self.client.post(
            "/api/auth/otp/verify",
            {"phone": self.phone, "code": code},
            format="json",
            **headers,
        )
        self.assertEqual(verified.status_code, 200)

    @patch("accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42"))
    @patch(
        "accounts.otp._finalize_send",
        side_effect=DatabaseError("database unavailable"),
    )
    def test_post_delivery_finalize_failure_returns_202(self, _finalize, send_sms):
        headers = self.csrf_headers()
        response = self.client.post(
            "/api/auth/otp/send",
            {"phone": self.phone},
            format="json",
            **headers,
        )
        code = send_sms.call_args.args[1]

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["data"]["deliveryStatus"], "unknown")
        verified = self.client.post(
            "/api/auth/otp/verify",
            {"phone": self.phone, "code": code},
            format="json",
            **headers,
        )
        self.assertEqual(verified.status_code, 200)

    @patch("accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42"))
    def test_verify_creates_a_session_and_me_returns_the_user(self, send_sms):
        headers = self.csrf_headers()
        sent = self.client.post(
            "/api/auth/otp/send", {"phone": self.phone}, format="json", **headers
        )
        self.assertEqual(sent.status_code, 200)
        code = send_sms.call_args.args[1]

        verified = self.client.post(
            "/api/auth/otp/verify",
            {"phone": self.phone, "code": code},
            format="json",
            **headers,
        )
        me = self.client.get("/api/auth/me")

        self.assertEqual(verified.status_code, 200)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["data"]["user"]["phone"], self.phone)
        self.assertEqual(
            me.data["data"]["otpConfig"],
            {"codeLength": 4, "expiresIn": 300, "resendAfter": 60},
        )
        self.assertIn("sessionid", self.client.cookies)
        self.assertEqual(self.client.session["auth_method"], "otp")

    @patch("accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42"))
    def test_verify_keeps_and_assigns_the_guest_cart(self, send_sms):
        guest_cart = Cart.objects.create()
        session = self.client.session
        session["cart_token"] = str(guest_cart.token)
        session.save()
        headers = self.csrf_headers()
        self.client.post(
            "/api/auth/otp/send", {"phone": self.phone}, format="json", **headers
        )
        code = send_sms.call_args.args[1]

        response = self.client.post(
            "/api/auth/otp/verify",
            {"phone": self.phone, "code": code},
            format="json",
            **headers,
        )

        self.assertEqual(response.status_code, 200)
        guest_cart.refresh_from_db()
        self.assertEqual(guest_cart.user.phone, self.phone)

    @patch("accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42"))
    @patch(
        "accounts.views.merge_guest_cart_into_user",
        side_effect=DatabaseError("locked"),
    )
    def test_cart_merge_failure_does_not_consume_login_result(self, _merge, send_sms):
        headers = self.csrf_headers()
        self.client.post(
            "/api/auth/otp/send", {"phone": self.phone}, format="json", **headers
        )
        code = send_sms.call_args.args[1]

        response = self.client.post(
            "/api/auth/otp/verify",
            {"phone": self.phone, "code": code},
            format="json",
            **headers,
        )
        me = self.client.get("/api/auth/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(me.data["data"]["user"]["phone"], self.phone)
        self.assertTrue(Otp.objects.get(phone=self.phone).used)

    @patch("accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42"))
    def test_fifth_wrong_verification_requires_a_new_code(self, send_sms):
        headers = self.csrf_headers()
        self.client.post(
            "/api/auth/otp/send", {"phone": self.phone}, format="json", **headers
        )
        correct_code = send_sms.call_args.args[1]
        wrong_code = "0000" if correct_code != "0000" else "1111"

        responses = [
            self.client.post(
                "/api/auth/otp/verify",
                {"phone": self.phone, "code": wrong_code},
                format="json",
                **headers,
            )
            for _ in range(TEST_SHOP["OTP_MAX_ATTEMPTS"])
        ]

        self.assertEqual(responses[-1].status_code, 400)
        self.assertEqual(
            responses[-1].data["errorCode"], "otp_attempts_exhausted"
        )
        self.assertTrue(responses[-1].data["data"]["requiresNewCode"])
        self.assertGreater(responses[-1].data["data"]["resendAfter"], 0)
        self.assertNotIn("Retry-After", responses[-1].headers)
        self.assertTrue(Otp.objects.get(phone=self.phone).used)

    @patch("accounts.otp.send_otp_sms", return_value=SmsDeliveryResult("42"))
    def test_inactive_user_cannot_log_in(self, send_sms):
        User.objects.create_user(phone=self.phone, is_active=False)
        headers = self.csrf_headers()
        self.client.post(
            "/api/auth/otp/send", {"phone": self.phone}, format="json", **headers
        )
        code = send_sms.call_args.args[1]

        response = self.client.post(
            "/api/auth/otp/verify",
            {"phone": self.phone, "code": code},
            format="json",
            **headers,
        )

        self.assertEqual(response.status_code, 403)
        self.assertNotIn("sessionid", self.client.cookies)
        self.assertTrue(Otp.objects.get(phone=self.phone).used)
