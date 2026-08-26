from django.core.exceptions import ValidationError
from django.db import models

from catalog.models import Brand, Category
from catalog.selectors import SORTS as PRODUCT_SORTS

SORT_CHOICES = [(key, key) for key in PRODUCT_SORTS]

THEME_CHOICES = [
    ("brand", "سبز (برند)"),
    ("secondary", "آبی"),
    ("accent", "طلایی"),
]

# فیلدهایی که هر نوع بخش واقعاً استفاده می‌کند — بقیه باید خالی بمانند
_TYPE_ALLOWED_FIELDS: dict[str, set[str]] = {
    "banner": {"banner"},
    "categories": {"limit"},
    "brands": {"limit"},
    "best_sellers": {"limit"},
    "incredible_products": {"limit"},
    "discounted_products": {"limit"},
    "new_products": {"limit"},
    # limit اینجا یعنی «تعداد در هر صفحه»، چون این بخش صفحه‌بندی می‌شود
    "all_products": {"limit"},
    "product_collection": {"category", "brand", "sort", "limit"},
    "recently_viewed": {"limit"},
}


class Banner(models.Model):
    """بنر تبلیغاتی قابل استفاده در بخش‌های صفحه اصلی"""

    title = models.CharField("عنوان", max_length=150, blank=True)
    subtitle = models.CharField("زیرعنوان", max_length=300, blank=True)
    image = models.ImageField("تصویر", upload_to="banners/", blank=True)
    theme = models.CharField(
        "پس‌زمینه", max_length=20, choices=THEME_CHOICES, default="brand"
    )
    link_url = models.CharField("لینک مقصد", max_length=300, blank=True)
    link_label = models.CharField("متن دکمه", max_length=60, blank=True)
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "بنر"
        verbose_name_plural = "بنرها"
        ordering = ["-created_at", "-id"]

    def clean(self):
        super().clean()
        if bool(self.link_url) != bool(self.link_label):
            raise ValidationError(
                {
                    "linkLabel": (
                        "لینک مقصد و متن دکمه باید هر دو تنظیم شوند یا هیچ‌کدام"
                    )
                }
            )
        is_internal_link = self.link_url.startswith("/") and not self.link_url.startswith(
            "//"
        )
        is_external_link = self.link_url.startswith(("http://", "https://"))
        if self.link_url and not (is_internal_link or is_external_link):
            raise ValidationError(
                {"linkUrl": "لینک باید مسیر داخلی (/...) یا آدرس http(s) باشد"}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title or f"بنر #{self.pk}"


class HomepageSection(models.Model):
    """یک بخش از صفحه اصلی — نوع، ترتیب، وضعیت نمایش و پیکربندی مربوط به آن نوع"""

    class SectionType(models.TextChoices):
        BANNER = "banner", "بنر"
        CATEGORIES = "categories", "دسته‌بندی‌ها"
        BRANDS = "brands", "برندها"
        BEST_SELLERS = "best_sellers", "پرفروش‌ترین‌ها"
        INCREDIBLE_PRODUCTS = "incredible_products", "شگفت‌انگیزها (منتخب مدیر)"
        DISCOUNTED_PRODUCTS = "discounted_products", "همه محصولات تخفیف‌دار"
        NEW_PRODUCTS = "new_products", "جدیدترین محصولات"
        ALL_PRODUCTS = "all_products", "همه محصولات (صفحه‌بندی‌شده)"
        PRODUCT_COLLECTION = "product_collection", "مجموعه محصولات سفارشی"
        RECENTLY_VIEWED = "recently_viewed", "محصولات اخیراً مشاهده‌شده"

    section_type = models.CharField(
        "نوع بخش", max_length=32, choices=SectionType.choices
    )
    title = models.CharField(
        "عنوان (اختیاری)",
        max_length=150,
        blank=True,
        help_text="در صورت خالی بودن، عنوان پیش‌فرض همان نوع بخش استفاده می‌شود",
    )
    position = models.PositiveIntegerField("ترتیب", default=0)
    is_active = models.BooleanField("فعال", default=True)

    banner = models.ForeignKey(
        Banner,
        verbose_name="بنر",
        on_delete=models.SET_NULL,
        related_name="sections",
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        Category,
        verbose_name="دسته‌بندی",
        # A deleted filter must not silently turn a curated collection into
        # an unfiltered "all products" section.
        on_delete=models.CASCADE,
        related_name="+",
        null=True,
        blank=True,
    )
    brand = models.ForeignKey(
        Brand,
        verbose_name="برند",
        on_delete=models.CASCADE,
        related_name="+",
        null=True,
        blank=True,
    )
    sort = models.CharField(
        "مرتب‌سازی", max_length=20, choices=SORT_CHOICES, blank=True
    )
    limit = models.PositiveSmallIntegerField(
        "حداکثر تعداد",
        null=True,
        blank=True,
        help_text="خالی = پیش‌فرض این نوع بخش",
    )

    created_at = models.DateTimeField("ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "بخش صفحه اصلی"
        verbose_name_plural = "بخش‌های صفحه اصلی"
        ordering = ["position", "id"]
        indexes = [models.Index(fields=["position", "id"], name="home_section_order_idx")]

    def clean(self):
        super().clean()
        allowed = _TYPE_ALLOWED_FIELDS.get(self.section_type)
        if allowed is None:
            raise ValidationError({"sectionType": "نوع بخش پشتیبانی نمی‌شود"})

        if "banner" in allowed and self.banner_id is None:
            raise ValidationError({"bannerId": "برای بخش بنر انتخاب بنر الزامی است"})

        if "banner" not in allowed and self.banner_id is not None:
            raise ValidationError(
                {"bannerId": "این فیلد برای این نوع بخش قابل استفاده نیست"}
            )
        if "category" not in allowed and self.category_id is not None:
            raise ValidationError(
                {"categorySlug": "این فیلد برای این نوع بخش قابل استفاده نیست"}
            )
        if "brand" not in allowed and self.brand_id is not None:
            raise ValidationError(
                {"brandSlug": "این فیلد برای این نوع بخش قابل استفاده نیست"}
            )
        if "sort" not in allowed and self.sort:
            raise ValidationError(
                {"sort": "این فیلد برای این نوع بخش قابل استفاده نیست"}
            )
        if "limit" not in allowed and self.limit is not None:
            raise ValidationError(
                {"limit": "این فیلد برای این نوع بخش قابل استفاده نیست"}
            )

        if self.limit is not None and not (1 <= self.limit <= 24):
            raise ValidationError({"limit": "حداکثر تعداد باید بین ۱ تا ۲۴ باشد"})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.get_section_type_display()} ({self.position})"
