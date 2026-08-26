# -*- coding: utf-8 -*-
"""ارتقای یک کاربر به مدیر (دسترسی داشبورد) — اجرا: python manage.py make_admin 09121234567"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from common.utils import is_valid_iran_mobile, normalize_phone

User = get_user_model()


class Command(BaseCommand):
    help = "کاربر با این شماره را staff (مدیر داشبورد) می‌کند؛ اگر نبود می‌سازد"

    def add_arguments(self, parser):
        parser.add_argument("phone", help="شماره موبایل کاربر، مثل 09121234567")
        parser.add_argument(
            "--revoke", action="store_true", help="گرفتن دسترسی مدیریت"
        )

    def handle(self, *args, **options):
        phone = normalize_phone(options["phone"])
        if not is_valid_iran_mobile(phone):
            self.stderr.write("شماره موبایل معتبر نیست")
            return

        user, created = User.objects.get_or_create(phone=phone)
        # گرفتن staff از مدیر اجرایی، نقشش را ناسازگار می‌کند
        if options["revoke"] and user.is_manager_admin:
            self.stderr.write(
                "این کاربر مدیر اجرایی است؛ برای لغو دسترسی از "
                f"«make_manager {phone} --revoke» استفاده کنید"
            )
            return
        # نقش مدیر سئو با داشبورد فروشگاه ناسازگار است
        if not options["revoke"] and user.is_seo_manager:
            self.stderr.write(
                "این کاربر مدیر سئو است؛ ابتدا با "
                f"«make_seo {phone} --revoke» نقش سئو را لغو کنید"
            )
            return
        user.is_staff = not options["revoke"]
        user.save(update_fields=["is_staff"])

        state = "مدیر شد ✅" if user.is_staff else "دسترسی مدیریتش گرفته شد"
        prefix = "کاربر جدید ساخته و " if created else ""
        self.stdout.write(self.style.SUCCESS(f"{prefix}{phone} {state}"))
