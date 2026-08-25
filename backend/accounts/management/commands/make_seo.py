# -*- coding: utf-8 -*-
"""ارتقای کاربر به «مدیر سئو» — اجرا: python manage.py make_seo 09121234567"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from common.utils import is_valid_iran_mobile, normalize_phone

User = get_user_model()


class Command(BaseCommand):
    help = "کاربر را مدیر سئو می‌کند (دسترسی فقط به پنل سئو)"

    def add_arguments(self, parser):
        parser.add_argument("phone")
        parser.add_argument("--revoke", action="store_true")

    def handle(self, *args, **options):
        phone = normalize_phone(options["phone"])
        if not is_valid_iran_mobile(phone):
            self.stderr.write("شماره موبایل معتبر نیست")
            return
        user, created = User.objects.get_or_create(phone=phone)
        # پنل سئو ناحیه‌ای جداست: مدیر فروشگاه/سوپریوزر نمی‌تواند مدیر سئو شود
        if not options["revoke"] and (user.is_staff or user.is_superuser):
            command = "make_manager" if user.is_manager_admin else "make_admin"
            self.stderr.write(
                "این کاربر مدیر فروشگاه است؛ ابتدا با "
                f"«{command} {phone} --revoke» دسترسی داشبورد را بگیرید"
            )
            return
        user.is_seo_manager = not options["revoke"]
        user.save(update_fields=["is_seo_manager"])
        state = "مدیر سئو شد ✅" if user.is_seo_manager else "دسترسی سئویش گرفته شد"
        prefix = "کاربر جدید ساخته و " if created else ""
        self.stdout.write(self.style.SUCCESS(f"{prefix}{phone} {state}"))
