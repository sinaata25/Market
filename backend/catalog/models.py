from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .validators import validate_category_icon


class Category(models.Model):
    slug = models.SlugField("نامک", unique=True)
    title = models.CharField("عنوان", max_length=100, unique=True)
    is_active = models.BooleanField("نمایش در فروشگاه", default=True)
    icon = models.FileField(
        "آیکن",
        upload_to="categories/icons/",
        blank=True,
        validators=[validate_category_icon],
        help_text="فایل PNG یا SVG ایمن، حداکثر ۵ مگابایت",
    )
    parents = models.ManyToManyField(
        "self",
        verbose_name="دسته‌بندی‌های والد",
        symmetrical=False,
        related_name="children",
        blank=True,
    )

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.title


class Product(models.Model):
    title = models.CharField("عنوان", max_length=255)
    title_en = models.CharField("عنوان انگلیسی", max_length=255, blank=True)
    price = models.PositiveIntegerField("قیمت (تومان)")
    old_price = models.PositiveIntegerField("قیمت قبل (تومان)", null=True, blank=True)
    rating = models.FloatField("امتیاز", default=0)
    rating_count = models.PositiveIntegerField("تعداد امتیاز", default=0)
    badge = models.CharField("برچسب", max_length=50, blank=True)
    colors = models.JSONField("رنگ‌ها", null=True, blank=True)  # [{name, hex}]
    features = models.JSONField("ویژگی‌ها", null=True, blank=True)  # [str]
    specs = models.JSONField("مشخصات", null=True, blank=True)  # [{label, value}]
    description = models.TextField("توضیحات", blank=True)
    warranty = models.CharField("گارانتی", max_length=100, blank=True)
    stock = models.PositiveIntegerField("موجودی", default=10)
    is_active = models.BooleanField("نمایش در فروشگاه", default=True)
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)

    category = models.ForeignKey(
        Category,
        verbose_name="دسته‌بندی اصلی",
        on_delete=models.PROTECT,
        related_name="products",
    )
    categories = models.ManyToManyField(
        Category,
        verbose_name="همه دسته‌بندی‌ها",
        related_name="categorized_products",
    )

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class ProductImage(models.Model):
    """تصویر محصول — اولین تصویر (کمترین order) تصویر اصلی است"""

    image = models.ImageField("تصویر", upload_to="products/")
    alt = models.CharField("متن جایگزین", max_length=255, blank=True)
    order = models.PositiveSmallIntegerField("ترتیب", default=0)

    product = models.ForeignKey(
        Product,
        verbose_name="محصول",
        on_delete=models.CASCADE,
        related_name="images",
    )

    class Meta:
        verbose_name = "تصویر محصول"
        verbose_name_plural = "تصاویر محصول"
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"{self.product} — {self.order}"


class Review(models.Model):
    rating = models.PositiveSmallIntegerField(
        "امتیاز", validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField("متن")
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)

    product = models.ForeignKey(
        Product, verbose_name="محصول", on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="کاربر",
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    class Meta:
        verbose_name = "دیدگاه"
        verbose_name_plural = "دیدگاه‌ها"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"], name="unique_user_product_review"
            )
        ]

    def __str__(self) -> str:
        return f"{self.product} — {self.rating}★"
