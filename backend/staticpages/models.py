from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .definitions import PAGE_KEY_CHOICES, SUPPORTED_PAGE_KEYS
from .validation import validate_content, validate_visibility


class StaticPage(models.Model):
    key = models.CharField(
        "شناسه صفحه", max_length=40, choices=PAGE_KEY_CHOICES, unique=True
    )
    content = models.JSONField("محتوا")
    is_visible = models.BooleanField("نمایش صفحه", default=True)
    section_visibility = models.JSONField("نمایش بخش‌ها", default=dict)
    updated_at = models.DateTimeField("آخرین ویرایش", auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="ویرایشگر",
        related_name="updated_static_pages",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = "محتوای صفحه"
        verbose_name_plural = "محتوای صفحات"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(key__in=SUPPORTED_PAGE_KEYS),
                name="staticpages_supported_key",
            )
        ]

    def clean(self):
        super().clean()
        if self.key not in SUPPORTED_PAGE_KEYS:
            raise ValidationError({"key": "شناسه صفحه پشتیبانی نمی‌شود"})
        validate_content(self.key, self.content)
        validate_visibility(self.key, self.is_visible, self.section_visibility)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.get_key_display()
