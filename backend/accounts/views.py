import logging

from django.conf import settings
from django.contrib.auth import login, logout
from django.db import DatabaseError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import Throttled
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView

from carts.services import merge_guest_cart_into_user
from common.responses import fail, ok
from common.utils import (
    is_valid_iran_mobile,
    normalize_digits,
    normalize_phone,
)

from .otp import (
    InactiveOtpUser,
    InvalidOtp,
    OtpAttemptsExhausted,
    OtpRecentlySent,
    issue_otp,
    verify_otp,
)
from .sms import SmsDeliveryError
from .throttles import (
    OtpSendIpThrottle,
    OtpSendPhoneThrottle,
    OtpVerifyIpThrottle,
    OtpVerifyPhoneThrottle,
)

logger = logging.getLogger(__name__)


def user_dto(user) -> dict:
    return {
        "id": user.id,
        "phone": user.phone,
        "name": user.name or None,
        "isStaff": user.is_staff,
        "isSuperuser": user.is_superuser,
        "isManagerAdmin": user.is_manager_admin,
        "isSeoManager": user.is_seo_manager,
        "createdAt": user.date_joined.isoformat(),
    }


class CsrfProtectedSessionAuthentication(SessionAuthentication):
    """Require CSRF even before an anonymous OTP request creates a session."""

    def authenticate(self, request):
        try:
            self.enforce_csrf(request)
        except exceptions.PermissionDenied as exc:
            raise exceptions.PermissionDenied(
                "نشست امنیتی معتبر نیست؛ صفحه را تازه‌سازی و دوباره تلاش کنید"
            ) from exc

        user = getattr(request._request, "user", None)
        if not user or not user.is_active:
            return None
        return user, None


class OtpCsrfRequired(BasePermission):
    """Allow anonymous OTP access after the authentication class enforces CSRF."""

    def has_permission(self, request, view):
        return True


class PhoneSerializer(serializers.Serializer):
    phone = serializers.CharField(
        max_length=32,
        error_messages={"required": "شماره موبایل الزامی است"},
    )

    def validate_phone(self, value):
        phone = normalize_phone(value)
        if not is_valid_iran_mobile(phone):
            raise serializers.ValidationError("شماره موبایل معتبر نیست")
        return phone


class VerifyOtpSerializer(PhoneSerializer):
    code = serializers.CharField(
        max_length=16,
        error_messages={"required": "کد تأیید الزامی است"},
    )

    def validate_code(self, value):
        code = normalize_digits(value)
        expected_length = settings.SHOP["OTP_LENGTH"]
        if not code.isascii() or not code.isdigit() or len(code) != expected_length:
            raise serializers.ValidationError(
                f"کد تأیید باید {expected_length} رقم باشد"
            )
        return code


class UserDtoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    phone = serializers.CharField()
    name = serializers.CharField(allow_null=True)
    isStaff = serializers.BooleanField()
    isSuperuser = serializers.BooleanField()
    isManagerAdmin = serializers.BooleanField()
    isSeoManager = serializers.BooleanField()
    createdAt = serializers.DateTimeField()


class ErrorResponseSerializer(serializers.Serializer):
    ok = serializers.BooleanField(default=False)
    error = serializers.CharField()
    errorCode = serializers.CharField(required=False)
    data = serializers.JSONField(required=False)


class SendOtpDataSerializer(serializers.Serializer):
    sent = serializers.BooleanField()
    expiresIn = serializers.IntegerField()
    resendAfter = serializers.IntegerField()
    codeLength = serializers.IntegerField()
    deliveryStatus = serializers.ChoiceField(choices=["accepted", "unknown"])


class SendOtpResponseSerializer(serializers.Serializer):
    ok = serializers.BooleanField(default=True)
    data = SendOtpDataSerializer()


class VerifyOtpDataSerializer(serializers.Serializer):
    user = UserDtoSerializer()


class VerifyOtpResponseSerializer(serializers.Serializer):
    ok = serializers.BooleanField(default=True)
    data = VerifyOtpDataSerializer()


class CsrfDataSerializer(serializers.Serializer):
    csrfReady = serializers.BooleanField()


class CsrfResponseSerializer(serializers.Serializer):
    ok = serializers.BooleanField(default=True)
    data = CsrfDataSerializer()


class OtpConfigSerializer(serializers.Serializer):
    codeLength = serializers.IntegerField()
    expiresIn = serializers.IntegerField()
    resendAfter = serializers.IntegerField()


class MeDataSerializer(serializers.Serializer):
    user = UserDtoSerializer(allow_null=True)
    otpConfig = OtpConfigSerializer()


class MeResponseSerializer(serializers.Serializer):
    ok = serializers.BooleanField(default=True)
    data = MeDataSerializer()


class LogoutDataSerializer(serializers.Serializer):
    loggedOut = serializers.BooleanField()


class LogoutResponseSerializer(serializers.Serializer):
    ok = serializers.BooleanField(default=True)
    data = LogoutDataSerializer()


class OtpEndpointThrottled(Throttled):
    error_code = "otp_rate_limited"


class OtpThrottleMessageMixin:
    def throttled(self, request, wait):
        raise OtpEndpointThrottled(
            wait=wait,
            detail="تعداد درخواست‌ها بیش از حد مجاز است؛ کمی بعد دوباره تلاش کنید",
        )


class SendOtpView(OtpThrottleMessageMixin, APIView):
    """Generate a challenge and deliver it through the configured SMS backend."""

    authentication_classes = [CsrfProtectedSessionAuthentication]
    permission_classes = [OtpCsrfRequired]
    throttle_classes = [OtpSendIpThrottle, OtpSendPhoneThrottle]

    @extend_schema(
        request=PhoneSerializer,
        responses={
            200: SendOtpResponseSerializer,
            202: SendOtpResponseSerializer,
            400: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
            429: ErrorResponseSerializer,
            503: ErrorResponseSerializer,
        },
    )
    def post(self, request):
        serializer = PhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]

        try:
            issued = issue_otp(phone)
        except OtpRecentlySent as exc:
            return fail(
                "کد به‌تازگی ارسال شده است؛ کمی صبر کنید و دوباره تلاش کنید",
                429,
                error_code="otp_cooldown",
                data={
                    "activeChallenge": exc.active_challenge,
                    "expiresIn": exc.expires_in,
                    "resendAfter": exc.retry_after,
                    "codeLength": settings.SHOP["OTP_LENGTH"],
                },
                headers={"Retry-After": str(exc.retry_after)},
            )
        except SmsDeliveryError:
            return fail(
                "ارسال پیامک موقتاً ممکن نیست؛ لطفاً کمی بعد دوباره تلاش کنید",
                503,
                error_code="otp_delivery_failed",
            )

        return ok(
            {
                "sent": True,
                "expiresIn": issued.expires_in,
                "resendAfter": issued.resend_after,
                "codeLength": settings.SHOP["OTP_LENGTH"],
                "deliveryStatus": issued.delivery_status,
            },
            status=202 if issued.delivery_status == "unknown" else 200,
        )


class VerifyOtpView(OtpThrottleMessageMixin, APIView):
    """Atomically consume an OTP and create a Django login session."""

    authentication_classes = [CsrfProtectedSessionAuthentication]
    permission_classes = [OtpCsrfRequired]
    throttle_classes = [OtpVerifyIpThrottle, OtpVerifyPhoneThrottle]

    @extend_schema(
        request=VerifyOtpSerializer,
        responses={
            200: VerifyOtpResponseSerializer,
            400: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
            429: ErrorResponseSerializer,
            503: ErrorResponseSerializer,
        },
    )
    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        code = serializer.validated_data["code"]

        try:
            user = verify_otp(phone, code)
        except InvalidOtp:
            return fail(
                "کد تأیید نامعتبر یا منقضی شده است؛ کد جدید درخواست کنید",
                400,
                error_code="otp_invalid",
            )
        except OtpAttemptsExhausted as exc:
            return fail(
                (
                    f"این کد پس از {settings.SHOP['OTP_MAX_ATTEMPTS']} تلاش "
                    "ناموفق باطل شد؛ کد جدید درخواست کنید"
                ),
                400,
                error_code="otp_attempts_exhausted",
                data={
                    "requiresNewCode": True,
                    "resendAfter": exc.retry_after,
                },
            )
        except InactiveOtpUser:
            return fail("این حساب غیرفعال است", 403, error_code="account_inactive")

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session["auth_method"] = "otp"
        try:
            merge_guest_cart_into_user(request, user)
        except DatabaseError:
            # Authentication must remain successful even if an incidental cart
            # merge hits a transient DB race/lock. The guest token stays in the
            # session so a later login can retry the merge.
            logger.exception("Guest cart merge failed after OTP authentication")
        return ok({"user": user_dto(user)})


@method_decorator(ensure_csrf_cookie, name="get")
@method_decorator(never_cache, name="get")
class CsrfCookieView(APIView):
    """Deterministically bootstrap the CSRF cookie before login mutations."""

    authentication_classes: list = []

    @extend_schema(request=None, responses={200: CsrfResponseSerializer})
    def get(self, request):
        return ok({"csrfReady": True})


@method_decorator(ensure_csrf_cookie, name="get")
@method_decorator(never_cache, name="get")
class MeView(APIView):
    """Return the current session user and also keep the CSRF cookie available."""

    @extend_schema(request=None, responses={200: MeResponseSerializer})
    def get(self, request):
        otp_config = {
            "codeLength": settings.SHOP["OTP_LENGTH"],
            "expiresIn": settings.SHOP["OTP_TTL_SECONDS"],
            "resendAfter": settings.SHOP["OTP_RESEND_COOLDOWN_SECONDS"],
        }
        if not request.user.is_authenticated:
            return ok({"user": None, "otpConfig": otp_config})
        return ok({"user": user_dto(request.user), "otpConfig": otp_config})


class LogoutView(APIView):
    @extend_schema(
        request=None,
        responses={200: LogoutResponseSerializer, 403: ErrorResponseSerializer},
    )
    def post(self, request):
        logout(request)
        return ok({"loggedOut": True})
