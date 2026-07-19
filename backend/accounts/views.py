import secrets

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import serializers
from rest_framework.views import APIView

from carts.services import merge_guest_cart_into_user
from common.responses import fail, ok
from common.utils import is_valid_iran_mobile, normalize_phone

from .models import Otp

User = get_user_model()
SHOP = settings.SHOP


def user_dto(user) -> dict:
    return {
        "id": user.id,
        "phone": user.phone,
        "name": user.name or None,
        "createdAt": user.date_joined.isoformat(),
    }


class SendOtpSerializer(serializers.Serializer):
    phone = serializers.CharField(error_messages={"required": "شماره موبایل الزامی است"})


class SendOtpView(APIView):
    """ارسال کد یکبارمصرف.

    نکته: سرویس پیامک هنوز متصل نیست؛ در حالت DEBUG کد در پاسخ (devCode)
    و در کنسول سرور نمایش داده می‌شود.
    """

    def post(self, request):
        ser = SendOtpSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = normalize_phone(ser.validated_data["phone"])

        if not is_valid_iran_mobile(phone):
            return fail("شماره موبایل معتبر نیست", 422)

        # محدودیت ارسال مجدد
        cooldown_start = timezone.now() - timezone.timedelta(
            seconds=SHOP["OTP_RESEND_COOLDOWN_SECONDS"]
        )
        if Otp.objects.filter(
            phone=phone, used=False, created_at__gt=cooldown_start
        ).exists():
            return fail(
                "کد به‌تازگی ارسال شده است؛ کمی صبر کنید و دوباره تلاش کنید", 429
            )

        # کدهای قبلی این شماره باطل شوند
        Otp.objects.filter(phone=phone, used=False).update(used=True)

        # کد ۵ رقمی امن (مطابق ۵ خانه‌ی فرم ورود)
        code = f"{secrets.randbelow(90000) + 10000}"
        Otp.objects.create(
            phone=phone,
            code=code,
            expires_at=timezone.now()
            + timezone.timedelta(seconds=SHOP["OTP_TTL_SECONDS"]),
        )

        # TODO: اتصال به سرویس پیامک (کاوه‌نگار، قاصدک و ...)
        print(f"📱 [OTP] کد ورود {phone}: {code}")

        data = {"sent": True, "ttl": SHOP["OTP_TTL_SECONDS"]}
        if SHOP["OTP_EXPOSE_DEV_CODE"]:
            data["devCode"] = code
        return ok(data)


class VerifyOtpSerializer(serializers.Serializer):
    phone = serializers.CharField(error_messages={"required": "شماره موبایل الزامی است"})
    code = serializers.CharField(error_messages={"required": "کد تأیید الزامی است"})


class VerifyOtpView(APIView):
    """تأیید کد و ورود/ثبت‌نام"""

    def post(self, request):
        ser = VerifyOtpSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = normalize_phone(ser.validated_data["phone"])
        code = normalize_phone(ser.validated_data["code"])

        if not is_valid_iran_mobile(phone):
            return fail("شماره موبایل معتبر نیست", 422)

        otp = Otp.objects.filter(phone=phone, used=False).first()
        if otp is None or otp.is_expired:
            return fail("کد منقضی شده است؛ کد جدید درخواست کنید", 410)
        if otp.attempts >= SHOP["OTP_MAX_ATTEMPTS"]:
            return fail("تعداد تلاش‌ها بیش از حد مجاز است؛ کد جدید درخواست کنید", 429)

        if not secrets.compare_digest(otp.code, code):
            otp.attempts += 1
            otp.save(update_fields=["attempts"])
            return fail("کد وارد شده صحیح نیست", 401)

        # کد درست است — یکبارمصرف شود
        otp.used = True
        otp.save(update_fields=["used"])

        # ورود یا ثبت‌نام
        user, _created = User.objects.get_or_create(phone=phone)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")

        # سبد مهمان به حساب کاربر منتقل می‌شود
        merge_guest_cart_into_user(request, user)

        return ok({"user": user_dto(user)})


@method_decorator(ensure_csrf_cookie, name="get")
class MeView(APIView):
    """اطلاعات کاربر جاری (null اگر لاگین نیست).

    کوکی csrftoken هم اینجا ست می‌شود تا کلاینت برای متدهای
    تغییردهنده هدر X-CSRFToken بفرستد.
    """

    def get(self, request):
        if not request.user.is_authenticated:
            return ok({"user": None})
        return ok({"user": user_dto(request.user)})


class LogoutView(APIView):
    """خروج از حساب"""

    def post(self, request):
        logout(request)
        return ok({"loggedOut": True})
