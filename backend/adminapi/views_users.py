"""مدیریت کاربران داشبورد — فهرست، ساخت، ویرایش، تغییر نقش و حذف

قواعد دسترسی هیچ‌کدام اینجا تصمیم‌گیری نمی‌شوند؛ همه از ``accounts.roles``
می‌آیند و کوئری‌ست از ``accounts.selectors.visible_users_for`` ساخته می‌شود.
سه قاعده‌ی اصلی که این ماژول را امن نگه می‌دارد:

1. **دید قبل از سریالایز**: هر جستجو/خواندن روی کوئری‌ستِ محدودشده انجام
   می‌شود؛ رکورد نامرئی حتی از دیتابیس هم بیرون نمی‌آید.
2. **رکورد نامرئی = ۴۰۴**: وجود یا نبودِ حسابی که نباید دیده شود لو نمی‌رود.
   (۴۰۳ برای وقتی است که حساب دیده می‌شود ولی این عملیات مجاز نیست.)
3. **هیچ فیلد نقشی از ورودی مستقیم روی مدل نمی‌نشیند**: ``role``،
   ``canAccessSeo`` و ``isActive`` هرکدام از یک بررسی مجوز جدا رد می‌شوند و
   ``is_superuser``/``is_staff``/``groups``/``user_permissions`` اصلاً در
   سریالایزر وجود ندارند.

پروژه فعلاً سامانه‌ی رخدادنگاری ندارد و اینجا هم ساخته نشده است؛ اما جای
افزودنش مشخص است: هر تغییر ممتاز از یکی از این چند نقطه می‌گذرد —
``apply_role``، تغییر ``is_active``، ``delete``، و در
``views_managers`` تغییر ``can_access_seo``. اضافه‌کردن رخدادنگاری یعنی
دست‌گذاشتن روی همین چند نقطه، نه گشتن در کل پروژه.
"""

import math

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from accounts.permissions import UserManagementRequiredMixin
from accounts.roles import (
    Role,
    can_change_role,
    can_delete_user,
    can_edit_user,
    can_grant_seo_access,
    can_manage_account_state,
    can_view_admin_users,
    creatable_roles,
    manageable_roles,
    role_of_record,
)
from accounts.selectors import role_filter, visible_users_for
from common.responses import fail, ok
from common.search import SearchQueryTooLong, filter_by_search
from common.utils import is_valid_iran_mobile, normalize_phone

from .views import positive_page

User = get_user_model()

PER_PAGE = 15


# ─── DTO ─────────────────────────────────────────────────────


def user_row(user, *, orders_count: int | None = None) -> dict:
    """ردیف کاربر برای داشبورد — بدون هیچ داده‌ی احراز هویتی

    رمز، هش OTP و وضعیت داخلی ورود عمداً اینجا نیستند.
    """
    role = role_of_record(user)
    row = {
        "id": user.id,
        "phone": user.phone,
        "name": user.name or None,
        "role": role.value,
        "roleLabel": role.label,
        "isActive": user.is_active,
        "canAccessSeo": bool(user.can_access_seo),
        "dateJoined": user.date_joined.isoformat(),
    }
    if orders_count is not None:
        row["ordersCount"] = orders_count
    return row


def permissions_for(actor, target=None) -> dict:
    """کارهایی که این کاربر روی این رکورد می‌تواند بکند

    فرانت دکمه‌ها را از همین می‌سازد تا قواعد دسترسی در دو جا نوشته نشوند.
    """
    if target is None:
        return {
            "creatableRoles": sorted(role.value for role in creatable_roles(actor)),
            "visibleRoles": sorted(role.value for role in manageable_roles(actor)),
            "canViewAdmins": can_view_admin_users(actor),
            "canGrantSeoAccess": can_grant_seo_access(actor),
        }
    return {
        "canEdit": can_edit_user(actor, target),
        "canChangeRole": any(
            can_change_role(actor, target, role) for role in Role
        ),
        "canChangeState": can_manage_account_state(actor, target),
        "canDelete": can_delete_user(actor, target),
        "canGrantSeoAccess": can_grant_seo_access(actor),
    }


# ─── سریالایزرها ─────────────────────────────────────────────


class PhoneField(serializers.CharField):
    """شماره را نرمال می‌کند تا ۰۹۱۲... و +۹۸۹۱۲... یکسان دیده شوند"""

    def to_internal_value(self, data):
        phone = normalize_phone(super().to_internal_value(data))
        if not is_valid_iran_mobile(phone):
            raise serializers.ValidationError("شماره موبایل معتبر نیست")
        return phone


class UserCreateSerializer(serializers.Serializer):
    """قرارداد ساخت کاربر

    فقط همین چهار فیلد پذیرفته می‌شوند. ``is_superuser``/``is_staff``/
    ``is_manager_admin``/``groups``/``user_permissions`` عمداً وجود ندارند تا
    ارسالشان در بدنه هیچ اثری نداشته باشد؛ مجوز واقعیِ ``role`` و
    ``canAccessSeo`` در ویو بررسی می‌شود.
    """

    phone = PhoneField(
        max_length=32, error_messages={"required": "شماره موبایل الزامی است"}
    )
    name = serializers.CharField(max_length=100, allow_blank=True, default="")
    role = serializers.ChoiceField(
        choices=Role.choices,
        default=Role.CUSTOMER,
        error_messages={"invalid_choice": "نقش نامعتبر است"},
    )
    canAccessSeo = serializers.BooleanField(required=False)


class UserUpdateSerializer(serializers.Serializer):
    """قرارداد ویرایش کاربر — همان فیلدهای امنِ ساخت، همه اختیاری"""

    phone = PhoneField(max_length=32, required=False)
    name = serializers.CharField(max_length=100, allow_blank=True, required=False)
    role = serializers.ChoiceField(
        choices=Role.choices,
        required=False,
        error_messages={"invalid_choice": "نقش نامعتبر است"},
    )
    isActive = serializers.BooleanField(required=False)
    canAccessSeo = serializers.BooleanField(required=False)


# ─── اعمال نقش روی فلگ‌ها ────────────────────────────────────

#: هر نقش دقیقاً یک ترکیب فلگ دارد؛ نوشتن نقش از همین‌جا می‌گذرد تا هیچ‌جا
#: فلگ‌ها را دستی و ناقص ست نکنیم (مثلاً is_manager_admin بدون is_staff).
_ROLE_FLAGS: dict[Role, dict] = {
    Role.SUPERUSER: {
        "is_superuser": True,
        "is_staff": True,
        "is_manager_admin": False,
        "is_seo_manager": False,
    },
    Role.MANAGER_ADMIN: {
        "is_superuser": False,
        "is_staff": True,
        "is_manager_admin": True,
        "is_seo_manager": False,
    },
    Role.REGULAR_ADMIN: {
        "is_superuser": False,
        "is_staff": True,
        "is_manager_admin": False,
        "is_seo_manager": False,
    },
    Role.SEO_ADMIN: {
        "is_superuser": False,
        "is_staff": False,
        "is_manager_admin": False,
        "is_seo_manager": True,
    },
    Role.CUSTOMER: {
        "is_superuser": False,
        "is_staff": False,
        "is_manager_admin": False,
        "is_seo_manager": False,
    },
}

ROLE_FLAG_FIELDS = (
    "is_superuser",
    "is_staff",
    "is_manager_admin",
    "is_seo_manager",
    "can_access_seo",
)


def apply_role(user, role: Role) -> None:
    """فلگ‌های نقش را روی شیء کاربر می‌نشاند (بدون ذخیره)

    خروج از نقش «مدیر اجرایی» دسترسی سئوی افزوده را هم پاک می‌کند؛ وگرنه
    توانایی روی نقشی می‌ماند که تعریفش نیست (و قید دیتابیس هم رد می‌کند).
    """
    for field, value in _ROLE_FLAGS[role].items():
        setattr(user, field, value)
    if role is not Role.MANAGER_ADMIN:
        user.can_access_seo = False


# ─── ویوها ───────────────────────────────────────────────────


class AdminUserListView(UserManagementRequiredMixin, APIView):
    """فهرست کاربرانِ قابل‌مشاهده + ساخت کاربر جدید

    دامنه‌ی دید را ``visible_users_for`` تعیین می‌کند: مدیر عادی فقط مشتری،
    مدیر اجرایی مدیران عادی/مشتری‌ها (+ مدیران سئو در صورت دسترسی سئو) و
    سوپریوزر همه را. جستجو و صفحه‌بندی هم روی همان کوئری‌ست محدودشده اجرا
    می‌شوند، پس شمارش کل هم چیزی لو نمی‌دهد.
    """

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        qs = visible_users_for(request.user).annotate(
            orders_count=Count("orders")
        ).order_by("-date_joined")

        role = request.query_params.get("role")
        if role:
            if role not in Role.values:
                return fail("نقش نامعتبر است", 422)
            qs = qs.filter(role_filter({Role(role)}))

        search = request.query_params.get("search", "")
        if search:
            try:
                qs = filter_by_search(qs, search, fields=("phone", "name"))
            except SearchQueryTooLong as exc:
                return fail(str(exc), 422)

        page = positive_page(request.query_params.get("page"))
        if page is None:
            return fail("پارامتر صفحه‌بندی نامعتبر است", 422)
        total = qs.count()
        rows = qs[(page - 1) * PER_PAGE : page * PER_PAGE]

        return ok(
            {
                "users": [
                    user_row(user, orders_count=user.orders_count)
                    for user in rows
                ],
                "total": total,
                "page": page,
                "pages": math.ceil(total / PER_PAGE) or 1,
                "permissions": permissions_for(request.user),
            }
        )

    @extend_schema(request=UserCreateSerializer, responses={201: OpenApiTypes.OBJECT})
    def post(self, request):
        ser = UserCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        role = Role(data["role"])

        # مجوز ساخت این نقش — جدول §۱۱
        if role not in creatable_roles(request.user):
            return fail(f"اجازه‌ی ساخت «{role.label}» را ندارید", 403)

        seo_access = data.get("canAccessSeo", False)
        if seo_access:
            if not can_grant_seo_access(request.user):
                return fail("دادن دسترسی سئو فقط از مدیر سیستم برمی‌آید", 403)
            if role is not Role.MANAGER_ADMIN:
                return fail("دسترسی سئو فقط برای «مدیر اجرایی» تعریف می‌شود", 422)

        phone = data["phone"]
        if User.objects.filter(phone=phone).exists():
            return fail("این شماره از قبل ثبت شده است", 409)

        user = User(phone=phone, name=data["name"].strip())
        apply_role(user, role)
        user.can_access_seo = bool(seo_access)
        try:
            with transaction.atomic():
                user.set_unusable_password()  # ورود فقط با کد یکبارمصرف است
                user.save()
        except IntegrityError:
            return fail("این شماره از قبل ثبت شده است", 409)
        except DjangoValidationError as exc:
            return fail(_first_error(exc), 422)

        return ok({"user": user_row(user, orders_count=0)}, status=201)


class AdminUserDetailView(UserManagementRequiredMixin, APIView):
    """جزئیات، ویرایش، تغییر نقش، فعال/غیرفعال‌سازی و حذف یک کاربر

    ``_get`` عمداً از کوئری‌ستِ محدودشده می‌خواند: درخواست مستقیم به شناسه‌ی
    یک سوپریوزر برای مدیر اجرایی ۴۰۴ می‌گیرد، نه ۴۰۳ — تا حتی وجود آن حساب
    هم فاش نشود.
    """

    def _get(self, request, pk: int):
        return visible_users_for(request.user).filter(pk=pk).first()

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request, pk: int):
        user = self._get(request, pk)
        if user is None:
            return fail("کاربر یافت نشد", 404)
        orders_count = user.orders.count()
        return ok(
            {
                "user": user_row(user, orders_count=orders_count),
                "permissions": permissions_for(request.user, user),
            }
        )

    @extend_schema(request=UserUpdateSerializer, responses={200: OpenApiTypes.OBJECT})
    def patch(self, request, pk: int):
        user = self._get(request, pk)
        if user is None:
            return fail("کاربر یافت نشد", 404)

        ser = UserUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        if not data:
            return fail("تغییری ارسال نشده است", 422)

        # هر گروه از فیلدها مجوز مستقل خودش را دارد
        wants_profile = {"phone", "name"} & data.keys()
        if wants_profile and not can_edit_user(request.user, user):
            return fail("اجازه‌ی ویرایش این حساب را ندارید", 403)

        target_role = role_of_record(user)
        if "role" in data:
            new_role = Role(data["role"])
            if new_role is not target_role and not can_change_role(
                request.user, user, new_role
            ):
                return fail("اجازه‌ی تغییر نقش این حساب را ندارید", 403)
            target_role = new_role

        if "isActive" in data and data["isActive"] != user.is_active:
            if not can_manage_account_state(request.user, user):
                return fail("اجازه‌ی تغییر وضعیت این حساب را ندارید", 403)

        if "canAccessSeo" in data:
            if not can_grant_seo_access(request.user):
                return fail("دادن دسترسی سئو فقط از مدیر سیستم برمی‌آید", 403)
            if data["canAccessSeo"] and target_role is not Role.MANAGER_ADMIN:
                return fail("دسترسی سئو فقط برای «مدیر اجرایی» تعریف می‌شود", 422)

        if "phone" in data and data["phone"] != user.phone:
            if User.objects.filter(phone=data["phone"]).exclude(pk=user.pk).exists():
                return fail("این شماره برای کاربر دیگری ثبت شده است", 409)
            user.phone = data["phone"]
        if "name" in data:
            user.name = data["name"].strip()
        if "isActive" in data:
            user.is_active = data["isActive"]
        if "role" in data:
            apply_role(user, target_role)
        if "canAccessSeo" in data:
            user.can_access_seo = data["canAccessSeo"]

        try:
            user.save()
        except DjangoValidationError as exc:
            return fail(_first_error(exc), 422)

        return ok(
            {
                "user": user_row(user, orders_count=user.orders.count()),
                "permissions": permissions_for(request.user, user),
            }
        )

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def delete(self, request, pk: int):
        """حذف کامل حساب — فقط مدیر سیستم

        مدیر اجرایی و مدیر عادی هرگز از این در رد نمی‌شوند؛ مدیر اجرایی برای
        بستن یک حساب باید غیرفعالش کند.
        """
        user = self._get(request, pk)
        if user is None:
            return fail("کاربر یافت نشد", 404)
        if not can_delete_user(request.user, user):
            return fail("اجازه‌ی حذف این حساب را ندارید", 403)
        try:
            user.delete()
        except ProtectedError:
            return fail(
                "این حساب سابقه‌ی سفارش دارد و حذف نمی‌شود؛ آن را غیرفعال کنید",
                409,
            )
        return ok({"deleted": True})


def _first_error(exc: DjangoValidationError) -> str:
    messages = getattr(exc, "message_dict", None)
    if messages:
        return next(iter(messages.values()))[0]
    return exc.messages[0] if exc.messages else "داده نامعتبر است"
