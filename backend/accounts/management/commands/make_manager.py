# -*- coding: utf-8 -*-
"""ارتقای کاربر به «مدیر اجرایی» — اجرا: python manage.py make_manager 09121234567"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from common.utils import is_valid_iran_mobile, normalize_phone

User = get_user_model()


class Command(BaseCommand):
    help = "کاربر را مدیر اجرایی می‌کند (کل داشبورد کسب‌وکار، بدون ناحیه‌ی سیستمی)"

    def add_arguments(self, parser):
        parser.add_argument("phone", help="شماره موبایل کاربر، مثل 09121234567")
        parser.add_argument(
            "--revoke", action="store_true", help="گرفتن نقش مدیر اجرایی"
        )

    def handle(self, *args, **options):
        phone = normalize_phone(options["phone"])
        if not is_valid_iran_mobile(phone):
            self.stderr.write("شماره موبایل معتبر نیست")
            return

        user, created = User.objects.get_or_create(phone=phone)
        if not options["revoke"]:
            # نقش اجرایی نقشِ کسب‌وکار است؛ با سوپریوزر و مدیر سئو ناسازگار است
            if user.is_superuser:
                self.stderr.write(
                    "این کاربر مدیر سیستم (سوپریوزر) است و نقش اجرایی نمی‌گیرد"
                )
                return
            if user.is_seo_manager:
                self.stderr.write(
                    "این کاربر مدیر سئو است؛ ابتدا با "
                    f"«make_seo {phone} --revoke» نقش سئو را لغو کنید"
                )
                return

        user.is_manager_admin = not options["revoke"]
        user.is_staff = user.is_manager_admin
        user.save(update_fields=["is_manager_admin", "is_staff"])

        state = (
            "مدیر اجرایی شد ✅"
            if user.is_manager_admin
            else "نقش اجرایی‌اش لغو شد"
        )
        prefix = "کاربر جدید ساخته و " if created else ""
        self.stdout.write(self.style.SUCCESS(f"{prefix}{phone} {state}"))
