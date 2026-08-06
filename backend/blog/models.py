from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from .validators import validate_featured_image


def unique_slug(instance: models.Model, value: str, fallback: str) -> str:
    field = instance._meta.get_field("slug")
    max_length = field.max_length
    base = slugify(value, allow_unicode=True).strip("-") or fallback
    base = base[:max_length].rstrip("-") or fallback
    candidate = base
    suffix = 2
    queryset = type(instance).objects.all()
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)
    while queryset.filter(slug=candidate).exists():
        marker = f"-{suffix}"
        candidate = f"{base[: max_length - len(marker)].rstrip('-')}{marker}"
        suffix += 1
    return candidate


def featured_image_upload_to(instance, filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
        extension = ".img"
    now = timezone.now()
    return f"blog/featured/{now:%Y/%m}/{uuid4().hex}{extension}"


class BlogCategory(models.Model):
    name = models.CharField("نام", max_length=100, unique=True)
    slug = models.SlugField("نامک", max_length=120, unique=True, allow_unicode=True, blank=True)
    description = models.TextField("توضیحات", blank=True)

    class Meta:
        verbose_name = "دسته‌بندی وبلاگ"
        verbose_name_plural = "دسته‌بندی‌های وبلاگ"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        if not self.slug:
            self.slug = unique_slug(self, self.name, "category")
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class BlogTag(models.Model):
    name = models.CharField("نام", max_length=60, unique=True)
    slug = models.SlugField("نامک", max_length=80, unique=True, allow_unicode=True, blank=True)

    class Meta:
        verbose_name = "برچسب وبلاگ"
        verbose_name_plural = "برچسب‌های وبلاگ"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        if not self.slug:
            self.slug = unique_slug(self, self.name, "tag")
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class BlogPostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(
            status=BlogPost.Status.PUBLISHED,
            published_at__isnull=False,
            published_at__lte=timezone.now(),
        )


class BlogPost(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "پیش‌نویس"
        PUBLISHED = "PUBLISHED", "منتشرشده"

    title = models.CharField("عنوان", max_length=255)
    slug = models.SlugField(
        "نامک", max_length=280, unique=True, allow_unicode=True, blank=True
    )
    excerpt = models.CharField("خلاصه", max_length=500)
    content = models.TextField("محتوا")
    featured_image = models.ImageField(
        "تصویر شاخص",
        upload_to=featured_image_upload_to,
        blank=True,
        validators=[validate_featured_image],
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="نویسنده",
        on_delete=models.PROTECT,
        related_name="blog_posts",
    )
    category = models.ForeignKey(
        BlogCategory,
        verbose_name="دسته‌بندی",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
    )
    tags = models.ManyToManyField(
        BlogTag, verbose_name="برچسب‌ها", blank=True, related_name="posts"
    )
    status = models.CharField(
        "وضعیت", max_length=12, choices=Status.choices, default=Status.DRAFT
    )
    published_at = models.DateTimeField("زمان انتشار", null=True, blank=True)
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین تغییر", auto_now=True)
    seo_title = models.CharField("عنوان سئو", max_length=200, blank=True)
    seo_description = models.CharField("توضیحات سئو", max_length=320, blank=True)

    objects = BlogPostQuerySet.as_manager()

    class Meta:
        verbose_name = "نوشته وبلاگ"
        verbose_name_plural = "نوشته‌های وبلاگ"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "published_at"], name="blog_post_public_idx"),
            models.Index(
                fields=["category", "status", "published_at"],
                name="blog_post_category_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(status="DRAFT", published_at__isnull=True)
                    | models.Q(status="PUBLISHED", published_at__isnull=False)
                ),
                name="blog_post_publication_state",
            )
        ]

    def clean(self):
        super().clean()
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            raise ValidationError(
                {"published_at": "نوشته منتشرشده باید زمان انتشار داشته باشد."}
            )
        if self.status == self.Status.DRAFT and self.published_at is not None:
            raise ValidationError(
                {"published_at": "پیش‌نویس نباید زمان انتشار داشته باشد."}
            )

    def save(self, *args, **kwargs):
        self.title = self.title.strip()
        self.excerpt = self.excerpt.strip()
        if not self.slug:
            self.slug = unique_slug(self, self.title, "post")
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title
