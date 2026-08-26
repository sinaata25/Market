"""نقش‌های مدیریتی — تنها منبع حقیقت برای دسترسی به پنل‌ها

سلسله‌مراتب نقش‌ها:

* «سوپریوزر» (``is_superuser``) — نقش **توسعه‌دهنده/سیستمی**: هرچه مدیر اجرایی
  می‌تواند، به‌علاوه‌ی ناحیه‌های سطح‌سیستم (ادمین جنگو، ساخت و مدیریت نقش‌های
  ممتاز). تنها نقشی که می‌تواند «مدیر اجرایی» و «مدیر سئو» بسازد.
* «مدیر اجرایی» (``is_manager_admin``) — نقش **کسب‌وکار**: کل داشبورد فروشگاه
  (سفارش‌ها، محصولات، کاربران، محتوا و ...) بدون هیچ دسترسی سطح‌سیستمی.
* «کارمند» (``is_staff`` بدون نقش دیگر) — همان دسترسی تاریخیِ داشبورد فروشگاه.
* «مدیر سئو» (``is_seo_manager``) — فقط پنل سئو، بدون داشبورد فروشگاه.

دو قاعده‌ی عمدی:

1. پنل سئو ناحیه‌ای جداست؛ سوپریوزر و مدیر اجرایی هم از آن کنار گذاشته می‌شوند.
   به همین دلیل هیچ‌جا از ``user.has_perm`` استفاده نمی‌شود (که برای سوپریوزر
   همیشه True است) و همین توابع صریح مبنا قرار می‌گیرند.
2. مدیر اجرایی هرگز نمی‌تواند نقش ممتاز بسازد یا خودش را ارتقا دهد؛ ساخت نقش‌ها
   فقط از مسیرهای ``IsDeveloperAdmin`` می‌گذرد.

ناسازگاری نقش‌ها علاوه بر این توابع، در ``User.clean``/``User.save`` و با
CheckConstraintهای دیتابیس هم تضمین می‌شود.
"""

from rest_framework.permissions import BasePermission


def _is_active_user(user) -> bool:
    """کاربر واقعی، لاگین‌شده و فعال باشد (نه ناشناس، نه غیرفعال‌شده)"""
    return bool(
        user is not None
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
    )


def is_seo_admin(user) -> bool:
    """مدیر سئو: فقط پنل سئو — سوپریوزر و staff عمداً مستثنا هستند"""
    return bool(
        _is_active_user(user)
        and user.is_seo_manager
        and not user.is_staff
        and not user.is_superuser
    )


def is_shop_admin(user) -> bool:
    """دسترسی به داشبورد فروشگاه — سوپریوزر، مدیر اجرایی و کارمند

    مدیر سئو اینجا راه ندارد.
    """
    return bool(
        _is_active_user(user) and user.is_staff and not user.is_seo_manager
    )


def is_manager_admin(user) -> bool:
    """مدیر اجرایی: کل کسب‌وکار، هیچ دسترسی سطح‌سیستمی"""
    return bool(
        _is_active_user(user)
        and user.is_manager_admin
        and user.is_staff
        and not user.is_superuser
        and not user.is_seo_manager
    )


def is_developer_admin(user) -> bool:
    """نقش توسعه‌دهنده/سیستمی — تنها نقشی که نقش‌های ممتاز را می‌سازد

    عمداً بر پایه‌ی ``is_superuser`` است: ناحیه‌های سطح‌سیستم فقط برای اوست و
    مدیر اجرایی هرگز نباید از این در رد شود.
    """
    return bool(
        _is_active_user(user) and user.is_superuser and not user.is_seo_manager
    )


class IsShopAdmin(BasePermission):
    """فقط مدیران فروشگاه — خطا با قالب یکسان {ok:false, error} برمی‌گردد"""

    message = "دسترسی مدیریتی ندارید"

    def has_permission(self, request, view):
        return is_shop_admin(request.user)


class IsSeoAdmin(BasePermission):
    """فقط «مدیر سئو» — سوپریوزر، staff و مشتری همگی رد می‌شوند"""

    message = "دسترسی پنل سئو ندارید"

    def has_permission(self, request, view):
        return is_seo_admin(request.user)


class IsManagerAdmin(BasePermission):
    """فقط مدیر اجرایی — برای بخش‌هایی که مخصوص همین نقش باشند"""

    message = "دسترسی مدیر اجرایی ندارید"

    def has_permission(self, request, view):
        return is_manager_admin(request.user)


class IsDeveloperAdmin(BasePermission):
    """فقط نقش توسعه‌دهنده (سوپریوزر) — ناحیه‌های سطح‌سیستم و ساخت نقش ممتاز"""

    message = "این بخش فقط برای مدیر سیستم (سوپریوزر) است"

    def has_permission(self, request, view):
        return is_developer_admin(request.user)


class ShopAdminRequiredMixin:
    """پیش‌شرط همه‌ی ویوهای داشبورد فروشگاه: ورود + دسترسی staff"""

    permission_classes = [IsShopAdmin]


class SeoAdminRequiredMixin:
    """پیش‌شرط همه‌ی ویوهای پنل سئو: ورود + نقش مدیر سئو"""

    permission_classes = [IsSeoAdmin]


class ManagerAdminRequiredMixin:
    """پیش‌شرط ویوهای مخصوص مدیر اجرایی"""

    permission_classes = [IsManagerAdmin]


class DeveloperOnlyMixin:
    """پیش‌شرط ناحیه‌های سطح‌سیستم: ورود + سوپریوزر

    مدیریت حساب‌های «مدیر اجرایی» و «مدیر سئو» از همین‌جا رد می‌شود؛ هیچ نقش
    دیگری — از جمله خودِ مدیر اجرایی — نمی‌تواند نقش ممتاز بسازد.
    """

    permission_classes = [IsDeveloperAdmin]
