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
    date_joined = models.DateTimeField("تاریخ عضویت", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self) -> str:
        return self.name or self.phone


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
