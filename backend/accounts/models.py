from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from common.utils import is_valid_iran_mobile, normalize_phone, validate_iran_mobile


class UserManager(BaseUserManager):
    """مدیریت ساخت کاربر با شماره موبایل به‌جای نام کاربری"""

    use_in_migrations = True

    @staticmethod
    def _normalize_phone_kwargs(kwargs: dict) -> dict:
        if "phone" in kwargs:
            kwargs = {**kwargs, "phone": normalize_phone(str(kwargs["phone"]))}
        return kwargs

    def get_or_create(self, defaults=None, **kwargs):
        return super().get_or_create(
            defaults=defaults,
            **self._normalize_phone_kwargs(kwargs),
        )

    def update_or_create(self, defaults=None, create_defaults=None, **kwargs):
        return super().update_or_create(
            defaults=defaults,
            create_defaults=create_defaults,
            **self._normalize_phone_kwargs(kwargs),
        )

    def create_user(self, phone: str, password: str | None = None, **extra):
        phone = normalize_phone(phone)
        if not is_valid_iran_mobile(phone):
            raise ValueError("شماره موبایل معتبر الزامی است")
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

    phone = models.CharField(
        "شماره موبایل",
        max_length=11,
        unique=True,
        validators=[validate_iran_mobile],
    )
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
        constraints = [
            models.CheckConstraint(
                condition=models.Q(phone__regex=r"^09[0-9]{9}$"),
                name="accounts_user_phone_canonical",
            )
        ]

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone)
        if not is_valid_iran_mobile(self.phone):
            raise ValidationError({"phone": "شماره موبایل معتبر نیست"})
        return super().save(*args, **kwargs)

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
    province_code = models.CharField(
        "کد رسمی استان", max_length=2, null=True, blank=True, editable=False
    )
    city_code = models.CharField(
        "کد رسمی شهر", max_length=4, null=True, blank=True, editable=False
    )
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
    """چالش یکبارمصرف ورود؛ برای هر شماره فقط یک رکورد وجود دارد."""

    phone = models.CharField(
        "شماره موبایل",
        max_length=11,
        unique=True,
        validators=[validate_iran_mobile],
    )
    code_hash = models.CharField("هش کد", max_length=128, editable=False)
    expires_at = models.DateTimeField("انقضا")
    attempts = models.PositiveSmallIntegerField(
        "تلاش‌های ناموفق کد فعلی", default=0
    )
    used = models.BooleanField("مصرف‌شده", default=False)
    sent_at = models.DateTimeField("زمان ارسال", null=True, blank=True)
    resend_blocked_until = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    provider_message_id = models.CharField(
        "شناسه پیام IPPanel", max_length=64, blank=True, editable=False
    )
    delivery_status = models.CharField(max_length=16, blank=True, editable=False)
    # The pending hash is written before the network request. This makes a code
    # verifiable even if IPPanel accepted it but the response/final DB write failed.
    pending_code_hash = models.CharField(max_length=128, blank=True, editable=False)
    pending_expires_at = models.DateTimeField(null=True, blank=True, editable=False)
    pending_attempts = models.PositiveSmallIntegerField(default=0, editable=False)
    send_token = models.UUIDField(null=True, blank=True, editable=False)
    send_started_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "کد یکبارمصرف"
        verbose_name_plural = "کدهای یکبارمصرف"
        ordering = ["-sent_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(phone__regex=r"^09[0-9]{9}$"),
                name="accounts_otp_phone_canonical",
            )
        ]

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone)
        if not is_valid_iran_mobile(self.phone):
            raise ValidationError({"phone": "شماره موبایل معتبر نیست"})
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        state = "مصرف‌شده" if self.used else "فعال"
        return f"{self.phone} — {state}"

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()
