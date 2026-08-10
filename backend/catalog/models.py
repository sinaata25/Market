from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .validators import validate_category_icon


class Brand(models.Model):
    name = models.CharField("نام", max_length=100, unique=True)
    slug = models.SlugField("نامک", max_length=100, unique=True)
    description = models.TextField("توضیحات", blank=True)
    logo = models.FileField(
        "نشان تجاری",
        upload_to="brands/logos/",
        blank=True,
        validators=[validate_category_icon],
        help_text="فایل PNG یا SVG ایمن، حداکثر ۵ مگابایت",
    )
    website = models.URLField("وب‌سایت", blank=True)
    is_active = models.BooleanField("نمایش در فروشگاه", default=True)
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "برند"
        verbose_name_plural = "برندها"
        ordering = ["name", "id"]

    def __str__(self) -> str:
        return self.name


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
    brand = models.ForeignKey(
        Brand,
        verbose_name="برند",
        on_delete=models.PROTECT,
        related_name="products",
        null=True,
        blank=True,
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


class ProductRating(models.Model):
    rating = models.PositiveSmallIntegerField(
        "امتیاز", validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    product = models.ForeignKey(
        Product, verbose_name="محصول", on_delete=models.CASCADE, related_name="ratings"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="کاربر",
        on_delete=models.CASCADE,
        related_name="product_ratings",
    )

    class Meta:
        verbose_name = "امتیاز محصول"
        verbose_name_plural = "امتیازهای محصول"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"], name="unique_user_product_rating"
            )
        ]

    def __str__(self) -> str:
        return f"{self.product} — {self.rating}★"


class ProductComment(models.Model):
    class Type(models.TextChoices):
        COMMENT = "comment", "دیدگاه"
        QUESTION = "question", "پرسش"

    class ModerationStatus(models.TextChoices):
        PENDING = "pending", "در انتظار تایید"
        APPROVED = "approved", "تایید شده"
        REJECTED = "rejected", "رد شده"

    content = models.TextField("متن")
    comment_type = models.CharField(
        "نوع",
        max_length=16,
        choices=Type.choices,
        default=Type.COMMENT,
    )
    moderation_status = models.CharField(
        "وضعیت بررسی",
        max_length=16,
        choices=ModerationStatus.choices,
        default=ModerationStatus.PENDING,
    )
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    product = models.ForeignKey(
        Product,
        verbose_name="محصول",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="نویسنده",
        on_delete=models.CASCADE,
        related_name="product_comments",
    )
    parent = models.ForeignKey(
        "self",
        verbose_name="پاسخ به",
        on_delete=models.CASCADE,
        related_name="replies",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "دیدگاه محصول"
        verbose_name_plural = "دیدگاه‌های محصول"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(
                fields=["product", "moderation_status", "created_at"],
                name="comment_product_status_idx",
            )
        ]

    def __str__(self) -> str:
        return f"{self.product} — {self.get_comment_type_display()}"
