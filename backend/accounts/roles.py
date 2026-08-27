"""نقش‌ها و «توانایی‌ها» — تنها مرجع تصمیم‌گیریِ مجوز در کل پروژه

این ماژول عمداً هیچ وابستگی به DRF ندارد تا هم ویوها، هم سرویس‌ها، هم دستورهای
مدیریتی و هم ادمین جنگو از همین یک منبع تغذیه شوند.
``accounts.permissions`` فقط لایه‌ی نازکِ DRF روی همین توابع است.

# مدل نقش

نقش‌ها ستون جداگانه‌ای در دیتابیس ندارند؛ از همان فلگ‌های موجود «استنتاج»
می‌شوند تا دو منبع حقیقتِ ناسازگار به وجود نیاید:

===================  ==================================================
نقش                  شرط
===================  ==================================================
مدیر سیستم           ``is_superuser``  (سازوکار اصلی جنگو، دست‌نخورده)
مدیر اجرایی          ``is_manager_admin`` و ``is_staff`` و نه سوپریوزر
مدیر عادی            ``is_staff`` بدون هیچ نقش دیگر
مدیر سئو             ``is_seo_manager`` (شاخه‌ی جدا، بدون ``is_staff``)
مشتری                هیچ‌کدام
===================  ==================================================

«دسترسی سئوی مدیر اجرایی» یک توانایی افزوده است (``User.can_access_seo``) که
فقط سوپریوزر آن را می‌دهد یا می‌گیرد؛ نقش جدیدی نمی‌سازد.

# سلسله‌مراتب

    مدیر سیستم
        ├── مدیر اجرایی ── مدیر عادی ── مشتری
        └── مدیر سئو            (شاخه‌ی تخصصی و جدا)

مدیر اجرایی فقط وقتی وارد شاخه‌ی سئو می‌شود که سوپریوزر صراحتاً اجازه داده باشد.
"""

from django.db import models


class Role(models.TextChoices):
    """نقش استنتاج‌شده — هرگز در دیتابیس ذخیره نمی‌شود

    ``SUPERUSER`` اینجا هست چون API و داشبورد باید نقش هر ردیف را نام ببرند،
    اما مبنای آن همیشه ``user.is_superuser`` است نه یک ستون موازی.
    """

    SUPERUSER = "superuser", "مدیر سیستم"
    MANAGER_ADMIN = "manager_admin", "مدیر اجرایی"
    REGULAR_ADMIN = "regular_admin", "مدیر عادی"
    SEO_ADMIN = "seo_admin", "مدیر سئو"
    CUSTOMER = "customer", "مشتری"


#: نقش‌هایی که در پنل مدیریت «حساب مدیریتی» شمرده می‌شوند
ADMIN_ROLES = frozenset(
    {Role.SUPERUSER, Role.MANAGER_ADMIN, Role.REGULAR_ADMIN, Role.SEO_ADMIN}
)


# ─── استنتاج نقش ─────────────────────────────────────────────


def is_active_user(user) -> bool:
    """کاربر واقعی، لاگین‌شده و فعال باشد (نه ناشناس، نه غیرفعال‌شده)"""
    return bool(
        user is not None
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
    )


def role_of(user) -> Role | None:
    """نقش کاربر؛ ``None`` یعنی کاربر معتبرِ فعالی در کار نیست

    ترتیب بررسی مهم است: بالاترین نقش اول.
    """
    if not is_active_user(user):
        return None
    if user.is_superuser:
        return Role.SUPERUSER
    if user.is_seo_manager:
        return Role.SEO_ADMIN
    if user.is_manager_admin and user.is_staff:
        return Role.MANAGER_ADMIN
    if user.is_staff:
        return Role.REGULAR_ADMIN
    return Role.CUSTOMER


def role_of_record(user) -> Role:
    """نقش یک ردیف کاربر برای نمایش/فیلتر — بدون شرط «فعال بودن»

    ``role_of`` برای کاربرِ درخواست‌دهنده است و حساب غیرفعال را بی‌نقش می‌داند؛
    اما در فهرست کاربران، حسابِ غیرفعال هم باید نقشش را نشان بدهد.
    """
    if user.is_superuser:
        return Role.SUPERUSER
    if user.is_seo_manager:
        return Role.SEO_ADMIN
    if user.is_manager_admin and user.is_staff:
        return Role.MANAGER_ADMIN
    if user.is_staff:
        return Role.REGULAR_ADMIN
    return Role.CUSTOMER


def is_developer_admin(user) -> bool:
    """مدیر سیستم — ``is_superuser`` جنگو، بالاترین سطح و بدون محدودیت نقشی"""
    return role_of(user) is Role.SUPERUSER


def is_manager_admin(user) -> bool:
    """مدیر اجرایی — کل داشبورد کسب‌وکار، بدون ناحیه‌ی سطح‌سیستم"""
    return role_of(user) is Role.MANAGER_ADMIN


def is_regular_admin(user) -> bool:
    """مدیر عادی — کارهای عملیاتی داشبورد، با مدیریت کاربرِ بسیار محدود"""
    return role_of(user) is Role.REGULAR_ADMIN


def is_seo_admin(user) -> bool:
    """مدیر سئو — حسابِ شاخه‌ی تخصصی سئو (نه صرفاً «کسی که به سئو دسترسی دارد»)"""
    return role_of(user) is Role.SEO_ADMIN


def is_customer(user) -> bool:
    return role_of(user) is Role.CUSTOMER


def is_shop_admin(user) -> bool:
    """دسترسی به داشبورد فروشگاه — سوپریوزر، مدیر اجرایی و مدیر عادی

    مدیر سئو و مشتری اینجا راه ندارند. این فقط «در ورودی» داشبورد است؛
    محدودیت‌های داخل هر بخش با توانایی‌های زیر کنترل می‌شود.
    """
    return role_of(user) in (
        Role.SUPERUSER,
        Role.MANAGER_ADMIN,
        Role.REGULAR_ADMIN,
    )


# ─── توانایی‌ها ──────────────────────────────────────────────


def can_access_seo(user) -> bool:
    """دسترسی به پنل سئو

    سه گروه: مدیر سیستم، مدیر سئو، و مدیر اجرایی‌ای که سوپریوزر به او
    دسترسی سئو داده است. عمداً از ``user.has_perm`` استفاده نمی‌شود چون برای
    سوپریوزر همیشه True است و مرزهای بقیه‌ی نقش‌ها را بی‌معنا می‌کند.
    """
    role = role_of(user)
    if role in (Role.SUPERUSER, Role.SEO_ADMIN):
        return True
    return role is Role.MANAGER_ADMIN and bool(user.can_access_seo)


def can_grant_seo_access(user) -> bool:
    """دادن/گرفتن دسترسی سئوی مدیر اجرایی — فقط مدیر سیستم

    حتی مدیر اجرایی‌ای که خودش دسترسی سئو دارد نمی‌تواند آن را به کسی بدهد.
    """
    return is_developer_admin(user)


def can_manage_users(user) -> bool:
    """ورود به بخش مدیریت کاربران داشبورد (دامنه‌اش با نقش فرق می‌کند)"""
    return is_shop_admin(user)


def can_view_admin_users(user) -> bool:
    """دیدن حساب‌های مدیریتی (نه فقط مشتری‌ها)"""
    return role_of(user) in (Role.SUPERUSER, Role.MANAGER_ADMIN)


#: نقش‌هایی که هر نقش می‌تواند بسازد — جدول §۱۱ صورت‌مسئله
_CREATABLE_ROLES: dict[Role, frozenset[Role]] = {
    Role.SUPERUSER: frozenset(
        {
            Role.SUPERUSER,
            Role.MANAGER_ADMIN,
            Role.REGULAR_ADMIN,
            Role.SEO_ADMIN,
            Role.CUSTOMER,
        }
    ),
    Role.MANAGER_ADMIN: frozenset({Role.REGULAR_ADMIN, Role.CUSTOMER}),
    Role.REGULAR_ADMIN: frozenset({Role.CUSTOMER}),
    Role.SEO_ADMIN: frozenset(),
    Role.CUSTOMER: frozenset(),
}


def creatable_roles(actor) -> frozenset[Role]:
    """نقش‌هایی که این کاربر اجازه‌ی ساختنشان را دارد"""
    role = role_of(actor)
    if role is None:
        return frozenset()
    allowed = _CREATABLE_ROLES[role]
    # مدیر اجرایی فقط با دسترسی سئو می‌تواند «مدیر سئو» بسازد
    if role is Role.MANAGER_ADMIN and can_access_seo(actor):
        allowed = allowed | {Role.SEO_ADMIN}
    return allowed


def can_create_role(actor, role: Role) -> bool:
    return role in creatable_roles(actor)


#: نقش‌هایی که هر نقش اجازه‌ی «دیدن و مدیریت» حسابشان را دارد
_MANAGEABLE_ROLES: dict[Role, frozenset[Role]] = {
    Role.SUPERUSER: frozenset(
        {
            Role.SUPERUSER,
            Role.MANAGER_ADMIN,
            Role.REGULAR_ADMIN,
            Role.SEO_ADMIN,
            Role.CUSTOMER,
        }
    ),
    # مدیر اجرایی نه سوپریوزر می‌بیند نه مدیر اجرایی دیگر
    Role.MANAGER_ADMIN: frozenset({Role.REGULAR_ADMIN, Role.CUSTOMER}),
    Role.REGULAR_ADMIN: frozenset({Role.CUSTOMER}),
    Role.SEO_ADMIN: frozenset(),
    Role.CUSTOMER: frozenset(),
}


def manageable_roles(actor) -> frozenset[Role]:
    """نقش‌هایی که حسابشان برای این کاربر «قابل دیدن و مدیریت» است"""
    role = role_of(actor)
    if role is None:
        return frozenset()
    allowed = _MANAGEABLE_ROLES[role]
    if role is Role.MANAGER_ADMIN and can_access_seo(actor):
        allowed = allowed | {Role.SEO_ADMIN}
    return allowed


def can_view_user(actor, target) -> bool:
    """آیا این کاربر اصلاً حق دیدن آن حساب را دارد؟

    مبنای فیلتر کوئری‌ست و بررسی تک‌رکوردی است؛ هر دو از همین یک جدول
    تغذیه می‌شوند تا «فهرست پنهان می‌کند ولی جزئیات لو می‌دهد» رخ ندهد.
    """
    return role_of_record(target) in manageable_roles(actor)


def can_edit_user(actor, target) -> bool:
    """ویرایش اطلاعات پایه‌ی یک حساب (نام/شماره)"""
    if not can_view_user(actor, target):
        return False
    # هیچ‌کس از مسیر مدیریت کاربران، حساب خودش را ویرایش نمی‌کند؛
    # پروفایل شخصی مسیر جداگانه‌ی خودش را دارد (/api/auth/profile)
    return actor.pk != target.pk


def can_change_role(actor, target, new_role: Role) -> bool:
    """تغییر نقش — هم نقش فعلی و هم نقش مقصد باید مجاز باشند

    این جلوی «مشتری بساز، بعد ارتقایش بده» را می‌گیرد.
    """
    if not can_edit_user(actor, target):
        return False
    if not can_create_role(actor, new_role):
        return False
    return True


def can_manage_account_state(actor, target) -> bool:
    """فعال/غیرفعال‌کردن یک حساب

    مدیر عادی عمداً هیچ حسابی را غیرفعال نمی‌کند: قاعده‌ی کسب‌وکاریِ موجودی
    برای این کار وجود ندارد، پس امن‌ترین حالت انتخاب شده است.
    """
    if not can_edit_user(actor, target):
        return False
    return role_of(actor) in (Role.SUPERUSER, Role.MANAGER_ADMIN)


def can_delete_user(actor, target) -> bool:
    """حذف کامل حساب — فقط مدیر سیستم، و نه حساب خودش

    مدیر اجرایی هم فقط غیرفعال می‌کند؛ حذف سخت با تاریخچه‌ی سفارش‌ها
    برخورد می‌کند و در این پروژه قاعده‌ای برای واگذاری‌اش وجود نداشته است.
    """
    if not can_view_user(actor, target):
        return False
    if actor.pk == target.pk:
        return False
    return is_developer_admin(actor)
