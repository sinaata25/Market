"""سلکتورهای کاربر — «چه کسی چه کاربرانی را می‌بیند»

محدودیت دید باید *قبل از* سریالایز شدن اعمال شود، نه با فیلترکردن پاسخ در
فرانت. هر ویویی که فهرست کاربران می‌دهد باید از همین‌جا کوئری بگیرد.

جدول نقش‌های قابل‌مشاهده در ``accounts.roles.manageable_roles`` است؛ اینجا
فقط همان جدول به ``Q`` ترجمه می‌شود تا فهرست و جزئیات هرگز از هم واگرا نشوند.
"""

from django.db.models import Q

from .roles import Role, manageable_roles

#: ترجمه‌ی هر نقشِ استنتاجی به شرط دیتابیسی معادلش
#: شرط‌های اضافی (مثل ``is_superuser=False`` روی مشتری) عمدی‌اند: اگر روزی
#: رکوردی با ترکیب ناسازگار در دیتابیس بنشیند، در سطل امن‌تر می‌افتد نه بازتر.
_ROLE_FILTERS: dict[Role, Q] = {
    Role.SUPERUSER: Q(is_superuser=True),
    Role.SEO_ADMIN: Q(is_superuser=False, is_seo_manager=True),
    Role.MANAGER_ADMIN: Q(
        is_superuser=False,
        is_seo_manager=False,
        is_manager_admin=True,
        is_staff=True,
    ),
    Role.REGULAR_ADMIN: Q(
        is_superuser=False,
        is_seo_manager=False,
        is_manager_admin=False,
        is_staff=True,
    ),
    Role.CUSTOMER: Q(
        is_superuser=False,
        is_seo_manager=False,
        is_manager_admin=False,
        is_staff=False,
    ),
}


def role_filter(roles) -> Q:
    """شرط «نقشِ رکورد یکی از این‌هاست»؛ مجموعه‌ی خالی یعنی هیچ رکوردی"""
    condition = Q(pk__in=[])
    for role in roles:
        condition |= _ROLE_FILTERS[role]
    return condition


def visible_users_for(actor, queryset=None):
    """کوئری‌ستِ کاربرانی که ``actor`` حق دیدنشان را دارد

    * مدیر سیستم: همه
    * مدیر اجرایی: مدیران عادی و مشتری‌ها (+ مدیران سئو در صورت داشتن دسترسی
      سئو). سوپریوزرها و سایر مدیران اجرایی اصلاً در کوئری نمی‌آیند.
    * مدیر عادی: فقط مشتری‌ها
    * مدیر سئو و مشتری: هیچ‌کس
    """
    if queryset is None:
        from django.contrib.auth import get_user_model

        queryset = get_user_model().objects.all()

    roles = manageable_roles(actor)
    if not roles:
        return queryset.none()
    return queryset.filter(role_filter(roles))
