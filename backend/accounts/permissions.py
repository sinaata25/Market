"""لایه‌ی DRF روی جدول نقش‌ها — کلاس‌های مجوز و میکسین‌های ویو

منطق واقعیِ «چه کسی چه کاری می‌تواند بکند» در ``accounts.roles`` است و اینجا
فقط به DRF وصل می‌شود. کدی که خودش ویو نیست (ادمین جنگو، سرویس‌ها، دستورهای
مدیریتی) باید مستقیم از ``accounts.roles`` بخواند، نه از این ماژول.

دو قاعده‌ی عمدی:

1. هیچ‌جا از ``user.has_perm`` استفاده نمی‌شود؛ برای سوپریوزر همیشه True است و
   مرز نقش‌های دیگر را بی‌معنا می‌کند. مبنا همان توابع صریح ``accounts.roles``
   است.
2. ساخت و ارتقای نقش هرگز به داده‌ی ارسالی کاربر اعتماد نمی‌کند؛ هر تغییر نقش
   از ``roles.can_change_role`` رد می‌شود.
"""

from rest_framework.permissions import BasePermission

from .roles import (
    Role,
    can_access_seo,
    can_create_role,
    can_manage_users,
    is_developer_admin,
    is_manager_admin,
    is_seo_admin,
    is_shop_admin,
)


class IsShopAdmin(BasePermission):
    """در ورودی داشبورد فروشگاه — سوپریوزر، مدیر اجرایی و مدیر عادی"""

    message = "دسترسی مدیریتی ندارید"

    def has_permission(self, request, view):
        return is_shop_admin(request.user)


class CanAccessSeoPanel(BasePermission):
    """پنل سئو — مدیر سئو، سوپریوزر، و مدیر اجرایی دارای دسترسی سئو"""

    message = "دسترسی پنل سئو ندارید"

    def has_permission(self, request, view):
        return can_access_seo(request.user)


class IsSeoAdmin(BasePermission):
    """فقط حسابِ «مدیر سئو» — برای بخش‌های مخصوص همین نقش"""

    message = "دسترسی پنل سئو ندارید"

    def has_permission(self, request, view):
        return is_seo_admin(request.user)


class IsManagerAdmin(BasePermission):
    """فقط مدیر اجرایی — برای بخش‌هایی که مخصوص همین نقش باشند"""

    message = "دسترسی مدیر اجرایی ندارید"

    def has_permission(self, request, view):
        return is_manager_admin(request.user)


class IsDeveloperAdmin(BasePermission):
    """فقط مدیر سیستم (سوپریوزر) — ناحیه‌های سطح‌سیستم"""

    message = "این بخش فقط برای مدیر سیستم (سوپریوزر) است"

    def has_permission(self, request, view):
        return is_developer_admin(request.user)


class CanManageUsers(BasePermission):
    """در ورودی بخش مدیریت کاربران — دامنه‌ی دید هر نقش را سلکتور تعیین می‌کند"""

    message = "دسترسی مدیریت کاربران ندارید"

    def has_permission(self, request, view):
        return can_manage_users(request.user)


class CanManageSeoAdmins(BasePermission):
    """مدیریت حساب‌های مدیر سئو — سوپریوزر یا مدیر اجرایی دارای دسترسی سئو"""

    message = "دسترسی مدیریت مدیران سئو ندارید"

    def has_permission(self, request, view):
        return can_create_role(request.user, Role.SEO_ADMIN)


class ShopAdminRequiredMixin:
    """پیش‌شرط همه‌ی ویوهای داشبورد فروشگاه: ورود + دسترسی داشبورد"""

    permission_classes = [IsShopAdmin]


class SeoPanelRequiredMixin:
    """پیش‌شرط همه‌ی ویوهای پنل سئو"""

    permission_classes = [CanAccessSeoPanel]


class ManagerAdminRequiredMixin:
    """پیش‌شرط ویوهای مخصوص مدیر اجرایی"""

    permission_classes = [IsManagerAdmin]


class DeveloperOnlyMixin:
    """پیش‌شرط ناحیه‌های سطح‌سیستم: ورود + سوپریوزر

    ساخت و مدیریت «مدیر اجرایی» و دادن/گرفتن دسترسی سئو فقط از این در می‌گذرد.
    """

    permission_classes = [IsDeveloperAdmin]


class UserManagementRequiredMixin:
    """پیش‌شرط ویوهای مدیریت کاربران"""

    permission_classes = [CanManageUsers]


class SeoAdminManagementRequiredMixin:
    """پیش‌شرط ویوهای مدیریت حساب‌های مدیر سئو"""

    permission_classes = [CanManageSeoAdmins]
