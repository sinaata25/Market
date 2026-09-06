from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from footer.validation import contains_control_characters, contains_html
from .validation import ICON_NAMES, destination_for, validate_contact_icon


class FloatingContactButton(models.Model):
    class Position(models.TextChoices):
        RIGHT = "bottom-right", "پایین راست"
        LEFT = "bottom-left", "پایین چپ"

    title = models.CharField("عنوان", max_length=120)
    platform = models.CharField(
        "پلتفرم", max_length=40, default="custom",
        validators=[RegexValidator(r"^[a-z][a-z0-9_-]*$", "شناسه پلتفرم معتبر نیست")],
    )
    phone_number = models.CharField("شماره تماس", max_length=40, blank=True)
    username = models.CharField("نام کاربری یا نشانی", max_length=500, blank=True)
    email = models.EmailField("ایمیل", blank=True)
    url = models.CharField("نشانی دلخواه", max_length=1000, blank=True)
    icon = models.FileField("آیکن آپلودی", upload_to="contacts/icons/", blank=True, validators=[validate_contact_icon])
    library_icon = models.ForeignKey(
        "footer.FooterIcon", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="contact_buttons", verbose_name="آیکن کتابخانه",
    )
    icon_name = models.CharField("آیکن پیش‌فرض انتخابی", max_length=40, blank=True)
    tooltip_text = models.CharField("راهنما", max_length=200, blank=True)
    is_active = models.BooleanField("فعال", default=True)
    open_in_new_tab = models.BooleanField("باز شدن در تب جدید", default=True)
    position = models.CharField("محل نمایش", max_length=20, choices=Position.choices, default=Position.RIGHT)
    display_order = models.PositiveIntegerField("ترتیب", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "دکمه تماس شناور"
        verbose_name_plural = "دکمه‌های تماس شناور"
        indexes = [models.Index(fields=["is_active", "display_order", "id"], name="contact_active_order_idx")]

    def clean(self):
        super().clean()
        errors = {}
        for field in ("title", "tooltip_text"):
            value = getattr(self, field)
            if contains_html(value) or contains_control_characters(value):
                errors[field] = "فقط متن ساده مجاز است"
        if not self.title.strip():
            errors["title"] = "عنوان الزامی است"
        if self.icon_name and self.icon_name not in ICON_NAMES:
            errors["icon_name"] = "آیکن انتخاب‌شده معتبر نیست"
        try:
            destination_for(self)
        except ValidationError as exc:
            errors.update(getattr(exc, "message_dict", {"url": exc.messages}))
        if errors:
            raise ValidationError(errors)

    @property
    def destination(self):
        return destination_for(self)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title
