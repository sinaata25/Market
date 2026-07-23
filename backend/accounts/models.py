from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """مدیریت ساخت کاربر با شماره موبایل به‌جای نام کاربری"""

    use_in_migrations = True

    def create_user(self, phone: str, password: str | None = None, **extra):
        if not phone:
            raise ValueError("شماره موبایل الزامی است")
        user = self.model(phone=phone, **extra)
        if password:
            user.set_password(password)
        else:
            # ورود فقط با OTP انجام می‌شود؛ رمز غیرقابل استفاده است
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone: str, password: str, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if not extra["is_staff"] or not extra["is_superuser"]:
            raise ValueError("سوپریوزر باید is_staff و is_superuser داشته باشد")
        return self.create_user(phone, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """کاربر فروشگاه — شناسه‌ی ورود: شماره موبایل"""

    phone = models.CharField("شماره موبایل", max_length=11, unique=True)
    name = models.CharField("نام", max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    # نقش «مدیر سئو»: دسترسی فقط به پنل سئو، بدون سفارش‌ها/کاربران/مالی
    is_seo_manager = models.BooleanField("مدیر سئو", default=False)
    date_joined = models.DateTimeField("تاریخ عضویت", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self) -> str:
        return self.name or self.phone


class Address(models.Model):
    """دفترچه آدرس کاربر"""

    user = models.ForeignKey(
        "accounts.User",
        verbose_name="کاربر",
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    title = models.CharField("عنوان", max_length=50, default="خانه")
    full_name = models.CharField("نام تحویل‌گیرنده", max_length=100)
    phone = models.CharField("شماره تماس", max_length=11)
    province = models.CharField("استان", max_length=50)
    city = models.CharField("شهر", max_length=50)
    address = models.TextField("آدرس")
    postal_code = models.CharField("کد پستی", max_length=10, blank=True)
    is_default = models.BooleanField("آدرس پیش‌فرض", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "آدرس"
        verbose_name_plural = "آدرس‌ها"
        ordering = ["-is_default", "-created_at"]

    def __str__(self) -> str:
        return f"{self.title} — {self.city}"


class Favorite(models.Model):
    """علاقه‌مندی‌های کاربر"""

    user = models.ForeignKey(
        "accounts.User",
        verbose_name="کاربر",
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    product = models.ForeignKey(
        "catalog.Product",
        verbose_name="محصول",
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "علاقه‌مندی"
        verbose_name_plural = "علاقه‌مندی‌ها"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"], name="unique_user_favorite"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} ❤ {self.product}"


class Otp(models.Model):
    """کد یکبارمصرف ورود"""

    phone = models.CharField("شماره موبایل", max_length=11, db_index=True)
    code = models.CharField("کد", max_length=5)
    expires_at = models.DateTimeField("انقضا")
    attempts = models.PositiveSmallIntegerField("تعداد تلاش", default=0)
    used = models.BooleanField("مصرف‌شده", default=False)
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)

    class Meta:
        verbose_name = "کد یکبارمصرف"
        verbose_name_plural = "کدهای یکبارمصرف"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.phone} — {self.code}"

    @property
    def is_expired(self) -> bool:
        return self.expires_at < timezone.now()
