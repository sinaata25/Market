"""ادمین جنگو = ناحیه‌ی توسعه‌دهنده/سیستمی

اینجا جدول کاربران (با ``is_staff``/``is_superuser``/گروه‌ها)، رکوردهای OTP و
پیکربندی سطح‌پایین در دسترس است؛ یعنی دقیقاً همان چیزهایی که «مدیر اجرایی»
نباید ببیند. پیش‌فرض جنگو در را روی هر کاربر ``is_staff`` باز می‌گذارد، پس
عمداً به ``is_developer_admin`` محدود می‌شود تا مدیر اجرایی نتواند از این مسیر
دسترسی ممتاز بگیرد.
"""

from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig

from accounts.permissions import is_developer_admin


class DeveloperAdminSite(AdminSite):
    def has_permission(self, request):
        return is_developer_admin(request.user)


class DeveloperAdminConfig(AdminConfig):
    default_site = "config.admin.DeveloperAdminSite"
