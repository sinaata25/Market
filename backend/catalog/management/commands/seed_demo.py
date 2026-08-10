# -*- coding: utf-8 -*-
"""پرکردن دیتابیس با داده‌ی نمایشی واقعی: عکس محصول از ویکی‌مدیا کامنز + دیدگاه.

اجرا:  python manage.py seed_demo
- عکس‌ها از Wikimedia Commons (تصاویر آزاد) دانلود و در media/products ذخیره می‌شوند.
- چند کاربر نمونه و دیدگاه تاییدشده ساخته می‌شود.
- ایمن برای اجرای مجدد (idempotent).
"""

import time

import requests
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from catalog.models import Product, ProductComment, ProductImage

User = get_user_model()

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "AbzarSabzShop/1.0 (dev seed; contact: dev@localhost)"}

# عبارت جستجوی عکس برای هر محصول (به انگلیسی، برای نتیجه بهتر در Commons)
PRODUCT_IMAGE_SEARCH = {
    1: "chainsaw cutting log wood",
    2: "farmer spraying knapsack sprayer field",
    3: "spade digging soil",
    4: "garden hose reel",
    5: "secateurs",
    6: "vegetable seeds packet",
    7: "work gloves gardening",
    8: "Miracle-Gro fertilizer",
}

# برای این محصولات، عکس اصلی مقاله ویکی‌پدیا استفاده می‌شود (همیشه مرتبط است)
PRODUCT_WIKI_ARTICLE = {
    1: "Chainsaw",
    3: "Spade",
    5: "Pruning shears",
    8: "Fertilizer",
}

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"

# دیدگاه‌های نمونه: (شماره کاربر، نام، شناسه محصول، امتیاز، متن)
DEMO_REVIEWS = [
    ("09120000001", "رضا محمدی", 1, 5, "برای هرس باغ گردو خریدم؛ قدرت موتور عالیه و روشن شدنش راحته. نسبت به قیمتش واقعا می‌ارزه."),
    ("09120000002", "حسین کریمی", 1, 4, "کیفیت ساخت خوبه ولی کمی سنگینه. برای کار طولانی حتما از بند شانه استفاده کنید."),
    ("09120000003", "مریم احمدی", 2, 5, "برای سمپاشی گلخانه استفاده می‌کنم. شارژش یک روز کامل جواب میده و پخش سم یکنواخته."),
    ("09120000001", "رضا محمدی", 3, 4, "بیل محکمیه و دسته‌اش خوش‌دسته. فقط بسته‌بندی ارسال می‌تونست بهتر باشه."),
    ("09120000004", "علی رضایی", 5, 5, "تیغه فوق‌العاده تیزه؛ شاخه‌های تا دو سانت رو راحت می‌بره. به همه باغدارها پیشنهاد می‌کنم."),
    ("09120000002", "حسین کریمی", 6, 4, "بذرها سبز شدن و درصد جوانه‌زنی خوبی داشتن. راهنمای کاشت هم داخل بسته بود."),
    ("09120000003", "مریم احمدی", 8, 5, "برای گل‌های آپارتمانی معجزه کرد. بعد از دو هفته رشد برگ‌ها کاملا مشخص بود."),
]


def fetch_commons_image(query: str) -> tuple[bytes, str] | None:
    """اولین عکس مناسب را از Wikimedia Commons می‌گیرد → (بایت‌ها، نام فایل)"""
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}",
        "gsrnamespace": 6,  # فقط فایل‌ها
        "gsrlimit": 5,
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "iiurlwidth": 800,
    }
    r = requests.get(COMMONS_API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    pages = (r.json().get("query") or {}).get("pages") or {}

    # مرتب بر اساس رتبه جستجو؛ فقط jpeg/png با ابعاد معقول
    for page in sorted(pages.values(), key=lambda p: p.get("index", 99)):
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        if info.get("mime") not in ("image/jpeg", "image/png"):
            continue
        if (info.get("width") or 0) < 400:
            continue
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        img = download_with_retry(url)
        if img is None:
            continue
        ext = "png" if info["mime"] == "image/png" else "jpg"
        return img, ext
    return None


def fetch_wikipedia_lead_image(article: str) -> tuple[bytes, str] | None:
    """عکس اصلی (lead) مقاله ویکی‌پدیای انگلیسی → (بایت‌ها، پسوند)"""
    params = {
        "action": "query",
        "format": "json",
        "titles": article,
        "prop": "pageimages",
        "piprop": "thumbnail",
        "pithumbsize": 800,
    }
    r = requests.get(WIKIPEDIA_API, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    pages = (r.json().get("query") or {}).get("pages") or {}
    for page in pages.values():
        thumb = (page.get("thumbnail") or {}).get("source")
        if not thumb:
            continue
        content = download_with_retry(thumb)
        if content is None:
            continue
        ext = "png" if thumb.lower().endswith(".png") else "jpg"
        return content, ext
    return None


def download_with_retry(url: str, attempts: int = 3) -> bytes | None:
    """دانلود با تلاش مجدد در برابر محدودیت نرخ (429)"""
    for i in range(attempts):
        r = requests.get(url, headers=HEADERS, timeout=60)
        if r.status_code == 429:
            time.sleep(10 * (i + 1))
            continue
        r.raise_for_status()
        return r.content
    return None


class Command(BaseCommand):
    help = "داده‌ی نمایشی: دانلود عکس واقعی محصولات از Wikimedia Commons + کاربران و دیدگاه‌های نمونه"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-images",
            action="store_true",
            help="فقط کاربران و دیدگاه‌ها؛ بدون دانلود عکس",
        )
        parser.add_argument(
            "--redo",
            nargs="*",
            type=int,
            help="شناسه محصولاتی که عکسشان حذف و دوباره دانلود شود",
        )

    def handle(self, *args, **options):
        redo = options.get("redo") or []
        if not options["skip_images"]:
            self.seed_images(redo)
        self.seed_comments()
        self.stdout.write(self.style.SUCCESS("🌱 seed_demo تمام شد."))

    # ─── عکس‌ها ─────────────────────────────────────────────

    def seed_images(self, redo: list[int]):
        self.stdout.write("⬇️  دانلود عکس محصولات از Wikimedia Commons ...")
        for product_id, query in PRODUCT_IMAGE_SEARCH.items():
            product = Product.objects.filter(pk=product_id).first()
            if product is None:
                continue
            if product_id in redo:
                # عکس فعلی حذف و دوباره دانلود شود
                for old in product.images.all():
                    old.image.delete(save=False)
                    old.delete()
            if product.images.exists():
                self.stdout.write(f"   #{product_id} عکس دارد؛ رد شد")
                continue
            try:
                # اول عکس مقاله ویکی‌پدیا (مطمئن)، بعد جستجوی Commons
                wiki_article = PRODUCT_WIKI_ARTICLE.get(product_id)
                result = (
                    fetch_wikipedia_lead_image(wiki_article) if wiki_article else None
                )
                if result is None:
                    result = fetch_commons_image(query)
            except requests.RequestException as e:
                self.stderr.write(f"   #{product_id} خطای شبکه: {e}")
                continue
            if result is None:
                self.stderr.write(f"   #{product_id} عکسی یافت نشد ({query})")
                continue
            content, ext = result
            ProductImage.objects.create(
                product=product,
                alt=product.title,
                order=0,
                image=ContentFile(content, name=f"p{product_id}.{ext}"),
            )
            self.stdout.write(
                self.style.SUCCESS(f"   ✅ #{product_id} {product.title[:30]}…")
            )
            # مکث برای رعایت محدودیت نرخ Commons
            time.sleep(3)

    # ─── کاربران و دیدگاه‌ها ────────────────────────────────

    def seed_comments(self):
        self.stdout.write("💬 ساخت کاربران و دیدگاه‌های نمونه ...")
        created = 0
        for phone, name, product_id, _rating, text in DEMO_REVIEWS:
            product = Product.objects.filter(pk=product_id).first()
            if product is None:
                continue
            user, _ = User.objects.get_or_create(phone=phone, defaults={"name": name})
            if not user.name:
                user.name = name
                user.save(update_fields=["name"])
            _, was_created = ProductComment.objects.get_or_create(
                product=product,
                user=user,
                content=text,
                defaults={
                    "moderation_status": ProductComment.ModerationStatus.APPROVED
                },
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"   ✅ {created} دیدگاه جدید"))
