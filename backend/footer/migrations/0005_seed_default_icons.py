"""ایموجی‌های فوتر را به آیکن‌های تصویری قابل تعویض تبدیل می‌کند

تا پیش از این، مزیت‌های فوتر با ایموجی (🚚 ✅ 💳 🎧) و ردیف‌های تماس با
ایموجی‌های هارد‌کدشده نمایش داده می‌شدند. این مهاجرت فایل‌های SVG همراهِ اپ
را در رسانه‌ی پروژه ذخیره می‌کند و به همان جاها وصلشان می‌کند، پس ظاهر فوتر
حفظ می‌شود اما از این پس هر آیکن از داشبورد قابل تعویض است.
"""

from pathlib import Path

from django.core.files.base import ContentFile
from django.db import migrations

ICON_DIRECTORY = Path(__file__).resolve().parent.parent / "default_icons"

# نام فایل → نام نمایشی در کتابخانه‌ی آیکن‌ها
ICON_NAMES = {
    "delivery": "ارسال",
    "authenticity": "ضمانت اصالت",
    "secure-payment": "پرداخت امن",
    "support": "پشتیبانی",
    "address": "نشانی",
    "phone": "تلفن",
    "email": "ایمیل",
}

# ایموجی فعلی آیتم → فایل آیکنی که جایش را می‌گیرد
EMOJI_REPLACEMENTS = {
    "🚚": "delivery",
    "✅": "authenticity",
    "💳": "secure-payment",
    "🎧": "support",
    "📍": "address",
    "☎️": "phone",
    "✉️": "email",
}

# آیکن‌های ردیف‌های اطلاعات تماس، که پیش‌تر در کامپوننت هارد‌کد بودند
SETTINGS_ICONS = {
    "address_icon": "address",
    "phone_icon": "phone",
    "email_icon": "email",
}


def seed_default_icons(apps, schema_editor):
    FooterIcon = apps.get_model("footer", "FooterIcon")
    FooterItem = apps.get_model("footer", "FooterItem")
    FooterSettings = apps.get_model("footer", "FooterSettings")

    storage = FooterIcon._meta.get_field("image").storage

    icons: dict[str, object] = {}
    for slug, display_name in ICON_NAMES.items():
        source = ICON_DIRECTORY / f"{slug}.svg"
        if not source.exists():
            continue
        icon = FooterIcon.objects.filter(name=display_name).first()
        if icon is not None:
            icons[slug] = icon
            continue

        # اگر فایل از اجرای قبلی (یا یک محیط دیگر با همان رسانه) موجود است،
        # دوباره نوشته نمی‌شود؛ وگرنه هر بار ساخت دیتابیس یک نسخه‌ی تکراری
        # در media جا می‌گذارد.
        target = f"footer/icons/{slug}.svg"
        if storage.exists(target):
            icons[slug] = FooterIcon.objects.create(
                name=display_name, image=target
            )
            continue
        icon = FooterIcon(name=display_name)
        icon.image.save(f"{slug}.svg", ContentFile(source.read_bytes()), save=True)
        icons[slug] = icon

    # آیتم‌هایی که ایموجی دارند و هنوز آیکنی برایشان انتخاب نشده
    for emoji, slug in EMOJI_REPLACEMENTS.items():
        icon = icons.get(slug)
        if icon is None:
            continue
        FooterItem.objects.filter(icon=emoji, icon_image__isnull=True).update(
            icon_image=icon
        )

    settings_row = FooterSettings.objects.filter(pk=1).first()
    if settings_row is None:
        return
    changed = []
    for field_name, slug in SETTINGS_ICONS.items():
        icon = icons.get(slug)
        if icon is not None and getattr(settings_row, f"{field_name}_id") is None:
            setattr(settings_row, field_name, icon)
            changed.append(field_name)
    if changed:
        settings_row.save(update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [("footer", "0004_footer_icon_library")]

    operations = [
        # Reversing must not delete icons an admin may have re-pointed since deploy.
        migrations.RunPython(seed_default_icons, migrations.RunPython.noop),
    ]
