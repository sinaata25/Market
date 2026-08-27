"""مدیریت حساب‌های «مدیر سئو»

دسترسی: مدیر سیستم، یا مدیر اجرایی‌ای که سوپریوزر به او دسترسی سئو داده است
(``accounts.roles.can_create_role(user, Role.SEO_ADMIN)``). مدیر اجرایی بدون
دسترسی سئو، مدیر عادی، مدیر سئو و مشتری همگی رد می‌شوند.

ورود در این پروژه فقط با کد یکبارمصرف انجام می‌شود؛ بنابراین «اطلاعات حساب» یک
مدیر سئو همان شماره موبایل (شناسه ورود)، نام و وضعیت فعال/غیرفعال است و رمزی
برای بازنشانی وجود ندارد.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from accounts.permissions import SeoAdminManagementRequiredMixin
from common.responses import fail, ok
from common.utils import is_valid_iran_mobile, normalize_phone

User = get_user_model()


def seo_admin_dto(user) -> dict:
    return {
        "id": user.id,
        "phone": user.phone,
        "name": user.name or None,
        "isActive": user.is_active,
        "createdAt": user.date_joined.isoformat(),
    }


def seo_admins_queryset():
    return User.objects.filter(is_seo_manager=True).order_by("-date_joined")


class PhoneField(serializers.CharField):
    """شماره را نرمال می‌کند تا ۰۹۱۲... و +۹۸۹۱۲... یکسان دیده شوند"""

    def to_internal_value(self, data):
        phone = normalize_phone(super().to_internal_value(data))
        if not is_valid_iran_mobile(phone):
            raise serializers.ValidationError("شماره موبایل معتبر نیست")
        return phone


class SeoAdminCreateSerializer(serializers.Serializer):
    phone = PhoneField(
        max_length=32, error_messages={"required": "شماره موبایل الزامی است"}
    )
    name = serializers.CharField(max_length=100, allow_blank=True, default="")


class SeoAdminUpdateSerializer(serializers.Serializer):
    phone = PhoneField(max_length=32, required=False)
    name = serializers.CharField(max_length=100, allow_blank=True, required=False)
    isActive = serializers.BooleanField(required=False)


class SeoAdminListView(SeoAdminManagementRequiredMixin, APIView):
    """فهرست مدیران سئو + ساخت مدیر سئوی جدید"""

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return ok({"seoAdmins": [seo_admin_dto(u) for u in seo_admins_queryset()]})

    @extend_schema(request=SeoAdminCreateSerializer, responses={201: OpenApiTypes.OBJECT})
    def post(self, request):
        ser = SeoAdminCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = ser.validated_data["phone"]
        name = ser.validated_data["name"].strip()

        existing = User.objects.filter(phone=phone).first()
        if existing is not None:
            if existing.is_seo_manager:
                return fail("این شماره از قبل مدیر سئو است", 409)
            if existing.is_staff or existing.is_superuser:
                return fail(
                    "این شماره متعلق به مدیر فروشگاه است؛ نقش سئو با آن ناسازگار است",
                    409,
                )
            # مشتری موجود ارتقا می‌یابد تا حساب و سفارش‌هایش حفظ شود
            existing.is_seo_manager = True
            if name:
                existing.name = name
            existing.save(update_fields=["is_seo_manager", "name"])
            return ok({"seoAdmin": seo_admin_dto(existing)}, status=201)

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    phone=phone, name=name, is_seo_manager=True
                )
        except IntegrityError:
            return fail("این شماره از قبل ثبت شده است", 409)
        return ok({"seoAdmin": seo_admin_dto(user)}, status=201)


class SeoAdminDetailView(SeoAdminManagementRequiredMixin, APIView):
    """ویرایش، فعال/غیرفعال‌سازی و لغو نقش یک مدیر سئو"""

    @staticmethod
    def _get(pk: int):
        return seo_admins_queryset().filter(pk=pk).first()

    @extend_schema(request=SeoAdminUpdateSerializer, responses={200: OpenApiTypes.OBJECT})
    def patch(self, request, pk: int):
        user = self._get(pk)
        if user is None:
            return fail("مدیر سئو یافت نشد", 404)

        ser = SeoAdminUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        if not d:
            return fail("تغییری ارسال نشده است", 422)

        updated = []
        if "phone" in d and d["phone"] != user.phone:
            if User.objects.filter(phone=d["phone"]).exclude(pk=user.pk).exists():
                return fail("این شماره برای کاربر دیگری ثبت شده است", 409)
            user.phone = d["phone"]
            updated.append("phone")
        if "name" in d:
            user.name = d["name"].strip()
            updated.append("name")
        if "isActive" in d:
            user.is_active = d["isActive"]
            updated.append("is_active")

        if updated:
            try:
                user.save(update_fields=updated)
            except DjangoValidationError as exc:
                return fail(
                    next(iter(exc.message_dict.values()))[0], 422
                )
        return ok({"seoAdmin": seo_admin_dto(user)})

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def delete(self, request, pk: int):
        """لغو نقش سئو — حساب کاربر حذف نمی‌شود و به مشتری عادی برمی‌گردد"""
        user = self._get(pk)
        if user is None:
            return fail("مدیر سئو یافت نشد", 404)
        user.is_seo_manager = False
        user.save(update_fields=["is_seo_manager"])
        return ok({"revoked": True})
