"""ساختار فوتر فعلی فروشگاه را به داده تبدیل می‌کند

پیش از این، ستون‌ها و مزیت‌های فوتر در کامپوننت Next هارد‌کد بودند. این
مهاجرت دقیقاً همان محتوا را می‌سازد تا بعد از استقرار هیچ چیزی از فوتر
غایب نشود؛ از این پس مدیر همه‌شان را از داشبورد تغییر می‌دهد.
"""

from django.db import migrations

BRAND_TITLE = "گروه صنعتی توانا"
DESCRIPTION = (
    "فروشگاه اینترنتی ابزارآلات و ادوات کشاورزی؛ ارائه‌دهنده انواع ابزار "
    "باغبانی، سمپاش و ماشین‌آلات با بهترین قیمت و ضمانت اصالت کالا."
)

# (عنوان, چیدمان, [(نوع, عنوان آیتم, نشانی, متن, آیکن, کلید صفحه محتوایی)])
SECTIONS = [
    (
        "",
        "strip",
        [
            ("text", "", "", "ارسال به سراسر کشور", "🚚", ""),
            ("text", "", "", "ضمانت اصالت کالا", "✅", ""),
            ("text", "", "", "پرداخت امن و درب منزل", "💳", ""),
            ("text", "", "", "پشتیبانی ۷ روز هفته", "🎧", ""),
        ],
    ),
    (
        "گروه صنعتی توانا",
        "column",
        [
            ("link", "درباره ما", "/about", "", "", "about"),
            ("link", "تماس با ما", "/contact", "", "", "contact"),
            ("link", "وبلاگ کشاورزی", "/blog", "", "", ""),
        ],
    ),
    (
        "خدمات مشتریان",
        "column",
        [
            ("link", "پاسخ به پرسش‌ها", "/support", "", "", "support"),
            ("link", "رویه ارسال سفارش", "/help/shipping", "", "", "shipping"),
            ("link", "شرایط بازگشت کالا", "/help/returns", "", "", "returns"),
        ],
    ),
    (
        "راهنمای خرید",
        "column",
        [
            ("link", "نحوه ثبت سفارش", "/help/how-to-order", "", "", "how-to-order"),
            ("link", "رهگیری سفارش", "/help/track-order", "", "", "track-order"),
            ("link", "گارانتی محصولات", "/help/warranty", "", "", "warranty"),
        ],
    ),
]


def seed_current_footer(apps, schema_editor):
    FooterSettings = apps.get_model("footer", "FooterSettings")
    FooterSection = apps.get_model("footer", "FooterSection")
    FooterItem = apps.get_model("footer", "FooterItem")

    if FooterSection.objects.exists():
        return

    # نام برند دقیقاً همان چیزی است که تا امروز در فوتر دیده می‌شد؛ اگر
    # مدیر خالی‌اش کند، از نام سایت در تنظیمات سئو پُر می‌شود. متن
    # کپی‌رایت عمداً خالی می‌ماند تا قالب پیش‌فرض همان جمله‌ی فعلی را بسازد.
    FooterSettings.objects.update_or_create(
        pk=1, defaults={"brand_title": BRAND_TITLE, "description": DESCRIPTION}
    )

    for position, (title, variant, items) in enumerate(SECTIONS):
        section = FooterSection.objects.create(
            title=title, variant=variant, position=position, is_active=True
        )
        FooterItem.objects.bulk_create(
            [
                FooterItem(
                    section=section,
                    item_type=item_type,
                    label=label,
                    url=url,
                    text=text,
                    icon=icon,
                    static_page_key=page_key,
                    position=index,
                    is_active=True,
                )
                for index, (
                    item_type,
                    label,
                    url,
                    text,
                    icon,
                    page_key,
                ) in enumerate(items)
            ]
        )


class Migration(migrations.Migration):
    dependencies = [("footer", "0001_initial")]

    operations = [
        # Reversing must not delete footer content an admin may have edited after deploy.
        migrations.RunPython(seed_current_footer, migrations.RunPython.noop),
    ]
