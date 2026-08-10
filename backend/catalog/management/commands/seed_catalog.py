# -*- coding: utf-8 -*-
"""پرکردن دیتابیس با داده‌های اولیه فروشگاه — اجرا: python manage.py seed_catalog"""

from django.core.management.base import BaseCommand

from catalog.feedback import recompute_product_rating
from catalog.models import Category, Product

CATEGORIES = [
    {
        "slug": "garden-tools",
        "title": "ابزار باغبانی",
        "sub": ["بیل و کلنگ", "قیچی باغبانی", "شن‌کش", "اره شاخه‌زنی", "ماله و کج‌بیل"],
    },
    {
        "slug": "sprayers",
        "title": "سمپاش‌ها",
        "sub": ["سمپاش پشتی", "سمپاش شارژی", "سمپاش موتوری", "سمپاش دستی", "نازل و لوازم جانبی"],
    },
    {
        "slug": "power-tools",
        "title": "ابزار موتوری",
        "sub": ["اره موتوری", "علف‌زن", "موتور برق", "دروگر", "تیلر و کولتیواتور"],
    },
    {
        "slug": "irrigation",
        "title": "آبیاری",
        "sub": ["شیلنگ آبیاری", "آبیاری قطره‌ای", "پمپ آب", "اتصالات", "تایمر آبیاری"],
    },
    {
        "slug": "seeds",
        "title": "بذر و نهال",
        "sub": ["بذر سبزیجات", "بذر صیفی", "نهال میوه", "پیاز گل", "خاک و بستر کشت"],
    },
    {
        "slug": "machinery",
        "title": "ماشین‌آلات",
        "sub": ["تراکتور", "ادوات خاک‌ورزی", "کمباین", "نشاکار", "یدکی ماشین‌آلات"],
    },
    {
        "slug": "safety",
        "title": "ایمنی و حفاظت",
        "sub": ["دستکش کار", "ماسک و فیلتر", "عینک ایمنی", "چکمه و کفش کار", "لباس کار"],
    },
    {
        "slug": "fertilizer",
        "title": "کود و سم",
        "sub": ["کود شیمیایی", "کود آلی", "سم دفع آفات", "علف‌کش", "محرک رشد"],
    },
]

PRODUCTS = [
    {
        "id": 1,
        "title": "اره موتوری حرفه‌ای ۵۲ سی‌سی با تیغه ۵۰ سانتی",
        "title_en": "Professional Chainsaw 52cc 50cm",
        "category": "ابزار موتوری",
        "subcategories": ["اره موتوری"],
        "price": 4_850_000,
        "old_price": 5_600_000,
        "rating": 4.6,
        "rating_count": 213,
        "badge": "پرفروش",
        "colors": [
            {"name": "نارنجی", "hex": "#ea580c"},
            {"name": "خاکستری", "hex": "#475569"},
        ],
        "features": [
            "موتور دو زمانه پرقدرت ۵۲ سی‌سی",
            "تیغه ۵۰ سانتی‌متری مناسب برش درختان قطور",
            "سیستم استارت آسان و کم‌مصرف",
            "دسته ضد لرزش برای کاهش خستگی",
        ],
        "specs": [
            {"label": "حجم موتور", "value": "۵۲ سی‌سی"},
            {"label": "طول تیغه", "value": "۵۰ سانتی‌متر"},
            {"label": "نوع موتور", "value": "بنزینی دو زمانه"},
            {"label": "ظرفیت مخزن سوخت", "value": "۵۵۰ میلی‌لیتر"},
            {"label": "وزن", "value": "۵.۸ کیلوگرم"},
            {"label": "کشور سازنده", "value": "آلمان"},
        ],
        "description": (
            "اره موتوری حرفه‌ای با موتور پرقدرت ۵۲ سی‌سی، مناسب برای هرس و برش "
            "درختان باغ و کارهای سنگین کشاورزی. طراحی ارگونومیک و سیستم ضد لرزش، "
            "استفاده طولانی‌مدت را راحت‌تر می‌کند."
        ),
        "warranty": "۱۸ ماه گارانتی شرکتی",
    },
    {
        "id": 2,
        "title": "سمپاش پشتی شارژی ۱۶ لیتری با باتری لیتیومی",
        "category": "سمپاش‌ها",
        "subcategories": ["سمپاش پشتی", "سمپاش شارژی"],
        "price": 1_980_000,
        "old_price": 2_350_000,
        "rating": 4.4,
        "rating_count": 156,
        "badge": "تخفیف ویژه",
    },
    {
        "id": 3,
        "title": "بیل باغبانی استیل ضدزنگ دسته چوبی",
        "category": "ابزار باغبانی",
        "subcategories": ["بیل و کلنگ"],
        "price": 420_000,
        "rating": 4.8,
        "rating_count": 89,
    },
    {
        "id": 4,
        "title": "شیلنگ آبیاری تقویت‌شده ۲۰ متری ضد پیچش",
        "category": "آبیاری",
        "subcategories": ["شیلنگ آبیاری"],
        "price": 690_000,
        "old_price": 820_000,
        "rating": 4.3,
        "rating_count": 64,
    },
    {
        "id": 5,
        "title": "قیچی باغبانی شاخه‌زنی تیغه فولادی ژاپنی",
        "category": "ابزار باغبانی",
        "subcategories": ["قیچی باغبانی"],
        "price": 350_000,
        "rating": 4.7,
        "rating_count": 142,
        "badge": "پرفروش",
    },
    {
        "id": 6,
        "title": "ست بذر سبزیجات ارگانیک ۱۲ عددی",
        "category": "بذر و نهال",
        "subcategories": ["بذر سبزیجات"],
        "price": 185_000,
        "old_price": 240_000,
        "rating": 4.5,
        "rating_count": 311,
    },
    {
        "id": 7,
        "title": "دستکش کار ضد برش مخصوص باغبانی (جفت)",
        "category": "ایمنی و حفاظت",
        "subcategories": ["دستکش کار"],
        "price": 95_000,
        "rating": 4.2,
        "rating_count": 47,
    },
    {
        "id": 8,
        "title": "کود مایع رشد گیاهان ۱ لیتری غلیظ",
        "category": "کود و سم",
        "subcategories": ["کود آلی"],
        "price": 145_000,
        "old_price": 175_000,
        "rating": 4.6,
        "rating_count": 98,
        "badge": "تخفیف ویژه",
    },
]


class Command(BaseCommand):
    help = "پرکردن دیتابیس با دسته‌بندی‌ها و محصولات اولیه (idempotent)"

    def handle(self, *args, **options):
        self.stdout.write("🌱 شروع seed ...")

        root_categories = {}
        for data in CATEGORIES:
            category, _ = Category.objects.update_or_create(
                slug=data["slug"],
                defaults={
                    "title": data["title"],
                },
            )
            root_categories[data["slug"]] = category

        for data in CATEGORIES:
            parent = root_categories[data["slug"]]
            for index, title in enumerate(data["sub"]):
                child = Category.objects.filter(title=title).first()
                if child is None:
                    base_slug = f"{parent.slug[:40]}-sub-{index + 1}"
                    slug = base_slug
                    suffix = 2
                    while Category.objects.filter(slug=slug).exists():
                        slug = f"{base_slug[:46]}-{suffix}"
                        suffix += 1
                    child = Category.objects.create(title=title, slug=slug)
                child.parents.add(parent)
        self.stdout.write(self.style.SUCCESS(f"✅ {len(CATEGORIES)} دسته‌بندی"))

        for data in PRODUCTS:
            category = Category.objects.get(title=data["category"])
            product, _ = Product.objects.update_or_create(
                id=data["id"],
                defaults={
                    "title": data["title"],
                    "title_en": data.get("title_en", ""),
                    "price": data["price"],
                    "old_price": data.get("old_price"),
                    "rating": 0,
                    "rating_count": 0,
                    "badge": data.get("badge", ""),
                    "colors": data.get("colors"),
                    "features": data.get("features"),
                    "specs": data.get("specs"),
                    "description": data.get("description", ""),
                    "warranty": data.get("warranty", ""),
                    "stock": 25,
                    "category": category,
                },
            )
            assigned_categories = [category]
            assigned_categories.extend(
                Category.objects.get(title=title)
                for title in data.get("subcategories", [])
            )
            product.categories.set(assigned_categories)
            recompute_product_rating(product.id)
        self.stdout.write(self.style.SUCCESS(f"✅ {len(PRODUCTS)} محصول"))
        self.stdout.write("🌱 seed تمام شد.")
