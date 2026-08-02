import re

import common.utils
from django.db import migrations, models


PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
TRANSLATION = {ord(char): str(index) for index, char in enumerate(PERSIAN_DIGITS)}
TRANSLATION.update(
    {ord(char): str(index) for index, char in enumerate(ARABIC_DIGITS)}
)


def normalize_phone(value):
    phone = re.sub(r"\s+", "", (value or "").translate(TRANSLATION)).strip()
    phone = phone.replace("-", "").replace("(", "").replace(")", "")
    if phone.startswith("+98"):
        phone = "0" + phone[3:]
    elif phone.startswith("0098"):
        phone = "0" + phone[4:]
    elif phone.startswith("98") and len(phone) == 12:
        phone = "0" + phone[2:]
    return phone


def canonicalize_users(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    normalized = []
    seen = set()
    for pk, raw_phone in User.objects.order_by("pk").values_list("pk", "phone"):
        phone = normalize_phone(raw_phone)
        if not re.fullmatch(r"09[0-9]{9}", phone):
            raise RuntimeError(
                f"User {pk} has an invalid phone; repair it before migration 0004"
            )
        if phone in seen:
            raise RuntimeError(
                "Two users normalize to the same phone; merge them before migration 0004"
            )
        seen.add(phone)
        normalized.append((pk, phone))

    for pk, phone in normalized:
        User.objects.filter(pk=pk).update(phone=phone)


def invalidate_and_deduplicate_otps(apps, schema_editor):
    """
    OTPs are intentionally short-lived. Keep one diagnostic row per phone,
    invalidate it, and discard older plaintext rows before adding uniqueness.
    """

    Otp = apps.get_model("accounts", "Otp")
    groups = {}
    invalid_pks = []
    for pk, raw_phone in Otp.objects.order_by("-created_at", "-pk").values_list(
        "pk", "phone"
    ):
        phone = normalize_phone(raw_phone)
        if not re.fullmatch(r"09[0-9]{9}", phone):
            invalid_pks.append(pk)
            continue
        groups.setdefault(phone, []).append(pk)

    Otp.objects.filter(pk__in=invalid_pks).delete()
    for phone, rows in groups.items():
        keep, *duplicates = rows
        Otp.objects.filter(pk=keep).update(phone=phone, code_hash="", used=True)
        Otp.objects.filter(pk__in=duplicates).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_address_favorite"),
    ]

    operations = [
        migrations.RunPython(canonicalize_users, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="phone",
            field=models.CharField(
                max_length=11,
                unique=True,
                validators=[common.utils.validate_iran_mobile],
                verbose_name="شماره موبایل",
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(
                condition=models.Q(("phone__regex", "^09[0-9]{9}$")),
                name="accounts_user_phone_canonical",
            ),
        ),
        migrations.AddField(
            model_name="otp",
            name="code_hash",
            field=models.CharField(
                default="", editable=False, max_length=128, verbose_name="هش کد"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="otp",
            name="provider_message_id",
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=64,
                verbose_name="شناسه پیام IPPanel",
            ),
        ),
        migrations.AddField(
            model_name="otp",
            name="resend_blocked_until",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        # Giving the legacy field a safe default makes schema rollback possible.
        # Plaintext OTP values are intentionally not recoverable on rollback.
        migrations.AlterField(
            model_name="otp",
            name="code",
            field=models.CharField(default="", max_length=5, verbose_name="کد"),
        ),
        migrations.RunPython(invalidate_and_deduplicate_otps, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="otp",
            name="code",
        ),
        migrations.RenameField(
            model_name="otp",
            old_name="created_at",
            new_name="sent_at",
        ),
        migrations.AlterField(
            model_name="otp",
            name="sent_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="زمان ارسال"),
        ),
        migrations.AddField(
            model_name="otp",
            name="delivery_status",
            field=models.CharField(blank=True, editable=False, max_length=16),
        ),
        migrations.AddField(
            model_name="otp",
            name="failure_window_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="otp",
            name="locked_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="otp",
            name="pending_code_hash",
            field=models.CharField(blank=True, editable=False, max_length=128),
        ),
        migrations.AddField(
            model_name="otp",
            name="pending_expires_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="otp",
            name="send_started_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="otp",
            name="send_token",
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.AddConstraint(
            model_name="otp",
            constraint=models.CheckConstraint(
                condition=models.Q(("phone__regex", "^09[0-9]{9}$")),
                name="accounts_otp_phone_canonical",
            ),
        ),
        migrations.AlterField(
            model_name="otp",
            name="phone",
            field=models.CharField(
                max_length=11,
                unique=True,
                validators=[common.utils.validate_iran_mobile],
                verbose_name="شماره موبایل",
            ),
        ),
        migrations.AlterField(
            model_name="otp",
            name="attempts",
            field=models.PositiveSmallIntegerField(
                default=0, verbose_name="تلاش‌های ناموفق"
            ),
        ),
        migrations.AlterModelOptions(
            name="otp",
            options={
                "ordering": ["-sent_at"],
                "verbose_name": "کد یکبارمصرف",
                "verbose_name_plural": "کدهای یکبارمصرف",
            },
        ),
    ]
