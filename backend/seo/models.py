from django.conf import settings
from django.db import models

DEFAULT_ROBOTS = """User-agent: *
Disallow: /admin/
Disallow: /cart
Disallow: /login
Disallow: /orders

Sitemap: {site_url}/sitemap.xml
"""


class SeoSettings(models.Model):
    """تنظیمات سراسری سئو — تک‌ردیفی (singleton)"""

    site_name = models.CharField("نام سایت", max_length=100, default="ابزار سبز")
    site_url = models.CharField(
        "آدرس سایت", max_length=200, default="http://localhost:3000"
    )
    default_meta_description = models.TextField("توضیحات متای پیش‌فرض", blank=True)

    robots_txt = models.TextField("robots.txt", blank=True)

    # نقشه سایت
    sitemap_enabled = models.BooleanField("سایت‌مپ فعال", default=True)
    sitemap_include_products = models.BooleanField("محصولات در سایت‌مپ", default=True)
    sitemap_include_categories = models.BooleanField(
        "دسته‌بندی‌ها در سایت‌مپ", default=True
    )
    sitemap_include_static = models.BooleanField(
        "صفحات ثابت در سایت‌مپ", default=True
    )
    sitemap_excluded_paths = models.TextField(
        "مسیرهای حذف‌شده از سایت‌مپ", blank=True, help_text="هر مسیر در یک خط"
    )

    # قابلیت‌های صفحه
    breadcrumbs_enabled = models.BooleanField("بردکرامب + اسکیمای آن", default=True)
    lazyload_enabled = models.BooleanField("لیزی‌لود تصاویر", default=True)
    image_compression_enabled = models.BooleanField(
        "فشرده‌سازی تصاویر هنگام آپلود", default=True
    )
    org_schema_enabled = models.BooleanField("اسکیمای Organization", default=True)

    # چندزبانه — JSON: [{"lang": "fa-IR", "url": "https://..."}]
    hreflang = models.JSONField("hreflang", default=list, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تنظیمات سئو"
        verbose_name_plural = "تنظیمات سئو"

    def __str__(self) -> str:
        return "تنظیمات سئو"

    @classmethod
    def load(cls) -> "SeoSettings":
        obj, created = cls.objects.get_or_create(pk=1)
        if created and not obj.robots_txt:
            obj.robots_txt = DEFAULT_ROBOTS.format(site_url=obj.site_url)
            obj.save(update_fields=["robots_txt"])
        return obj


class PageMeta(models.Model):
    """متادیتای سئو برای هر صفحه (محصول/دسته/صفحه ثابت)"""

    class PageType(models.TextChoices):
        PRODUCT = "product", "محصول"
        CATEGORY = "category", "دسته‌بندی"
        STATIC = "static", "صفحه ثابت"

    page_type = models.CharField("نوع صفحه", max_length=20, choices=PageType.choices)
    # برای product/category شناسه‌ی عددی؛ برای static مسیر (مثل "/" یا "/support")
    object_key = models.CharField("کلید", max_length=200)

    meta_title = models.CharField("عنوان متا", max_length=200, blank=True)
    meta_description = models.TextField("توضیحات متا", blank=True)
    slug = models.SlugField("نامک", max_length=200, blank=True, allow_unicode=True)
    canonical = models.CharField("Canonical", max_length=300, blank=True)
    robots_index = models.BooleanField("index", default=True)
    robots_follow = models.BooleanField("follow", default=True)
    focus_keyword = models.CharField("کلمه کلیدی کانونی", max_length=100, blank=True)

    og_title = models.CharField("عنوان OG", max_length=200, blank=True)
    og_description = models.TextField("توضیحات OG", blank=True)
    og_image = models.CharField("تصویر OG", max_length=300, blank=True)
    twitter_card = models.CharField(
        "Twitter Card",
        max_length=30,
        default="summary_large_image",
        choices=[
            ("summary", "summary"),
            ("summary_large_image", "summary_large_image"),
        ],
    )

    schema_type = models.CharField(
        "نوع اسکیما",
        max_length=30,
        blank=True,
        choices=[
            ("Product", "Product"),
            ("Article", "Article"),
            ("FAQPage", "FAQPage"),
            ("WebPage", "WebPage"),
            ("CollectionPage", "CollectionPage"),
        ],
    )
    schema_custom = models.TextField(
        "اسکیمای سفارشی (JSON-LD)", blank=True, help_text="در صورت تعیین، جایگزین اسکیمای خودکار می‌شود"
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "متای صفحه"
        verbose_name_plural = "متای صفحات"
        constraints = [
            models.UniqueConstraint(
                fields=["page_type", "object_key"], name="unique_page_meta"
            )
        ]

    def __str__(self) -> str:
        return f"{self.page_type}:{self.object_key}"


class MetaRevision(models.Model):
    """تاریخچه نسخه‌های متای هر صفحه (قابل بازگردانی)"""

    meta = models.ForeignKey(
        PageMeta, on_delete=models.CASCADE, related_name="revisions"
    )
    data = models.JSONField("داده")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "نسخه متا"
        verbose_name_plural = "نسخه‌های متا"
        ordering = ["-created_at"]


class Redirect(models.Model):
    """ریدایرکت 301/302 — توسط middleware فرانت اعمال می‌شود"""

    from_path = models.CharField("از مسیر", max_length=300, unique=True)
    to_path = models.CharField("به مسیر", max_length=300)
    status_code = models.PositiveSmallIntegerField(
        "کد", default=301, choices=[(301, "301 دائمی"), (302, "302 موقت")]
    )
    is_active = models.BooleanField("فعال", default=True)
    note = models.CharField("یادداشت", max_length=200, blank=True)
    hits = models.PositiveIntegerField("دفعات استفاده", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ریدایرکت"
        verbose_name_plural = "ریدایرکت‌ها"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.from_path} → {self.to_path}"


class NotFoundLog(models.Model):
    """گزارش صفحات ۴۰۴"""

    path = models.CharField("مسیر", max_length=300, unique=True)
    hits = models.PositiveIntegerField("دفعات", default=1)
    referer = models.CharField("ارجاع‌دهنده", max_length=300, blank=True)
    last_seen = models.DateTimeField("آخرین بازدید", auto_now=True)
    first_seen = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "خطای ۴۰۴"
        verbose_name_plural = "خطاهای ۴۰۴"
        ordering = ["-hits"]

    def __str__(self) -> str:
        return self.path


class ScanResult(models.Model):
    """نتیجه اسکن سرعت / لینک شکسته"""

    url = models.CharField("آدرس", max_length=300)
    kind = models.CharField(
        "نوع", max_length=10, choices=[("page", "صفحه"), ("link", "لینک")]
    )
    status_code = models.PositiveSmallIntegerField("کد وضعیت", null=True)
    response_ms = models.PositiveIntegerField("زمان پاسخ (ms)", null=True)
    ok = models.BooleanField("سالم", default=True)
    checked_at = models.DateTimeField("زمان بررسی", auto_now=True)

    class Meta:
        verbose_name = "نتیجه اسکن"
        verbose_name_plural = "نتایج اسکن"
        ordering = ["ok", "-response_ms"]
