"""مدیریت حساب‌های «مدیر اجرایی» — فقط سوپریوزر (نقش توسعه‌دهنده)

ساخت نقش ممتاز عمداً فقط از این مسیر می‌گذرد: خودِ مدیر اجرایی هیچ‌جا نمی‌تواند
نقش بسازد یا ارتقا بدهد. مثل مدیر سئو، ورود این حساب‌ها هم با کد یکبارمصرفِ
همان شماره موبایل انجام می‌شود و رمزی برای بازنشانی وجود ندارد.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from accounts.permissions import DeveloperOnlyMixin
from common.responses import fail, ok

from .views_seo_admins import PhoneField

User = get_user_model()


def manager_dto(user) -> dict:
    return {
        "id": user.id,
        "phone": user.phone,
        "name": user.name or None,
        "isActive": user.is_active,
        "createdAt": user.date_joined.isoformat(),
    }


def managers_queryset():
    return User.objects.filter(is_manager_admin=True).order_by("-date_joined")


class ManagerCreateSerializer(serializers.Serializer):
    phone = PhoneField(
        max_length=32, error_messages={"required": "شماره موبایل الزامی است"}
    )
    name = serializers.CharField(max_length=100, allow_blank=True, default="")


class ManagerUpdateSerializer(serializers.Serializer):
    phone = PhoneField(max_length=32, required=False)
    name = serializers.CharField(max_length=100, allow_blank=True, required=False)
    isActive = serializers.BooleanField(required=False)


class ManagerListView(DeveloperOnlyMixin, APIView):
    """فهرست مدیران اجرایی + ساخت مدیر اجرایی جدید"""

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return ok({"managers": [manager_dto(u) for u in managers_queryset()]})

    @extend_schema(
        request=ManagerCreateSerializer, responses={201: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        ser = ManagerCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        phone = ser.validated_data["phone"]
        name = ser.validated_data["name"].strip()

        existing = User.objects.filter(phone=phone).first()
        if existing is not None:
            if existing.is_manager_admin:
                return fail("این شماره از قبل مدیر اجرایی است", 409)
            if existing.is_superuser:
                return fail(
                    "این شماره متعلق به مدیر سیستم است؛ نقش اجرایی با آن ناسازگار است",
                    409,
                )
            if existing.is_seo_manager:
                return fail(
                    "این شماره متعلق به مدیر سئو است؛ ابتدا نقش سئو را لغو کنید",
                    409,
                )
            # کارمند یا مشتری موجود ارتقا می‌یابد تا حسابش حفظ شود
            existing.is_manager_admin = True
            existing.is_staff = True
            if name:
                existing.name = name
            existing.save(
                update_fields=["is_manager_admin", "is_staff", "name"]
            )
            return ok({"manager": manager_dto(existing)}, status=201)

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    phone=phone,
                    name=name,
                    is_staff=True,
                    is_manager_admin=True,
                )
        except IntegrityError:
            return fail("این شماره از قبل ثبت شده است", 409)
        return ok({"manager": manager_dto(user)}, status=201)


class ManagerDetailView(DeveloperOnlyMixin, APIView):
    """ویرایش، فعال/غیرفعال‌سازی و لغو نقش یک مدیر اجرایی"""

    @staticmethod
    def _get(pk: int):
        return managers_queryset().filter(pk=pk).first()

    @extend_schema(
        request=ManagerUpdateSerializer, responses={200: OpenApiTypes.OBJECT}
    )
    def patch(self, request, pk: int):
        user = self._get(pk)
        if user is None:
            return fail("مدیر اجرایی یافت نشد", 404)

        ser = ManagerUpdateSerializer(data=request.data)
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
                return fail(next(iter(exc.message_dict.values()))[0], 422)
        return ok({"manager": manager_dto(user)})

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def delete(self, request, pk: int):
        """لغو نقش اجرایی — حساب حذف نمی‌شود و به مشتری عادی برمی‌گردد"""
        user = self._get(pk)
        if user is None:
            return fail("مدیر اجرایی یافت نشد", 404)
        user.is_manager_admin = False
        user.is_staff = False
        user.save(update_fields=["is_manager_admin", "is_staff"])
        return ok({"revoked": True})
