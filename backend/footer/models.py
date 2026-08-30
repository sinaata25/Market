from django.core.exceptions import ValidationError
from django.db import models

# آیکن‌های فوتر همان قواعد ایمنی آیکن دسته‌بندی را دارند (PNG یا SVG پاک‌سازی‌شده)
from catalog.validators import validate_category_icon
from staticpages.definitions import PAGE_KEY_CHOICES, SUPPORTED_PAGE_KEYS

from .maps import (
    DEFAULT_ZOOM,
    LATITUDE_RANGE,
    LONGITUDE_RANGE,
    ZOOM_RANGE,
    is_google_maps_url,
)
from .validation import (
    contains_control_characters,
    contains_html,
    is_safe_url,
    is_valid_email,
    is_valid_phone,
)

# فیلدهایی که هر نوع آیتم واقعاً استفاده می‌کند — بقیه باید خالی بمانند.
# افزودن نوع تازه یعنی یک ردیف اینجا و یک شاخه در فوتر فروشگاه، نه یک
# مدل جدید.
_TYPE_ALLOWED_FIELDS: dict[str, set[str]] = {
    "link": {
        "label",
        "url",
        "icon",
        "icon_image",
        "open_in_new_tab",
        "static_page_key",
    },
    "text": {"label", "text", "icon", "icon_image"},
    "image": {"label", "url", "image", "open_in_new_tab"},
    "phone": {"label", "text", "icon", "icon_image"},
    "email": {"label", "text", "icon", "icon_image"},
    "address": {"label", "text", "icon", "icon_image"},
    "social": {"label", "url", "icon", "icon_image", "open_in_new_tab"},
}

# بدون این فیلدها آن نوع آیتم اصلاً چیزی برای نمایش ندارد
_TYPE_REQUIRED_FIELDS: dict[str, set[str]] = {
    "link": {"label", "url"},
    "text": {"text"},
    "image": {"image"},
    "phone": {"text"},
    "email": {"text"},
    "address": {"text"},
    "social": {"url"},
}

# نام فیلد مدل → کلید خطا در API (camelCase)
_FIELD_ERROR_KEYS: dict[str, str] = {
    "label": "label",
    "url": "url",
    "text": "text",
    "image": "image",
    "icon": "icon",
    "icon_image": "iconId",
    "open_in_new_tab": "openInNewTab",
    "static_page_key": "staticPageKey",
}

_REQUIRED_FIELD_MESSAGES: dict[str, str] = {
    "label": "عنوان الزامی است",
    "url": "نشانی مقصد الزامی است",
    "text": "متن الزامی است",
    "image": "انتخاب تصویر الزامی است",
}

# متن این نوع‌ها معنای خاص دارد و جداگانه اعتبارسنجی می‌شود
_TEXT_VALIDATORS: dict[str, tuple] = {
    "phone": (is_valid_phone, "شماره تماس معتبر نیست"),
    "email": (is_valid_email, "ایمیل معتبر نیست"),
}


def allowed_fields(item_type: str) -> set[str]:
    """فیلدهای معنادار برای این نوع آیتم — خالی اگر نوع ناشناخته باشد"""
    return _TYPE_ALLOWED_FIELDS.get(item_type, set())


def _plain_text_error(value: str) -> str | None:
    if contains_html(value):
        return "ورود HTML مجاز نیست؛ محتوا را به‌صورت متن ساده وارد کنید"
    if contains_control_characters(value):
        return "متن دارای نویسه کنترلی نامعتبر است"
    return None


class FooterIcon(models.Model):
    """آیکن قابل استفاده‌ی مجدد در فوتر

    یک‌بار آپلود می‌شود و هر جای فوتر (مزیت‌ها، پیوندها، اطلاعات تماس) به
    آن ارجاع می‌دهد؛ همان الگوی «بنر» در صفحه‌ی اصلی. تعویض فایل یک آیکن،
    همه‌ی جاهایی که از آن استفاده می‌کنند را با هم به‌روز می‌کند.
    """

    name = models.CharField("نام", max_length=80, unique=True)
    image = models.FileField(
        "فایل آیکن",
        upload_to="footer/icons/",
        validators=[validate_category_icon],
        help_text="فایل PNG یا SVG ایمن، حداکثر ۵ مگابایت",
    )
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "آیکن فوتر"
        verbose_name_plural = "آیکن‌های فوتر"
        ordering = ["name", "id"]

    def clean(self):
        super().clean()
        message = _plain_text_error(self.name)
        if message:
            raise ValidationError({"name": message})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class FooterSettings(models.Model):
    """تنظیمات سراسری فوتر — تک‌ردیفی (singleton)

    نام برند عمداً پیش‌فرض خالی دارد: در آن حالت نام سایت از تنظیمات سئو
    خوانده می‌شود تا دو منبع حقیقت برای یک چیز ساخته نشود.
    """

    brand_title = models.CharField(
        "نام برند",
        max_length=120,
        blank=True,
        help_text="خالی = نام سایت از تنظیمات سئو",
    )
    logo = models.ImageField("لوگو", upload_to="footer/", blank=True)
    description = models.TextField("توضیح کوتاه", max_length=600, blank=True)
    copyright_text = models.CharField(
        "متن کپی‌رایت",
        max_length=200,
        blank=True,
        help_text="عبارت {year} با سال جاری جایگزین می‌شود",
    )
    address = models.CharField("نشانی", max_length=300, blank=True)
    phone = models.CharField("تلفن", max_length=40, blank=True)
    email = models.EmailField("ایمیل", max_length=120, blank=True)

    # آیکن ردیف‌های اطلاعات تماس در فوتر؛ آیکن نشانی روی نقشه هم به کار می‌رود
    address_icon = models.ForeignKey(
        FooterIcon,
        verbose_name="آیکن نشانی",
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    phone_icon = models.ForeignKey(
        FooterIcon,
        verbose_name="آیکن تلفن",
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    email_icon = models.ForeignKey(
        FooterIcon,
        verbose_name="آیکن ایمیل",
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )

    # موقعیت فروشگاه — نشانی متنی همان فیلد address بالاست تا دو منبع حقیقت
    # برای یک چیز ساخته نشود؛ اینجا فقط مختصات و تنظیمات نمایش نقشه است.
    latitude = models.DecimalField(
        "عرض جغرافیایی", max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        "طول جغرافیایی", max_digits=10, decimal_places=6, null=True, blank=True
    )
    show_map = models.BooleanField("نمایش نقشه در فوتر", default=True)
    map_zoom = models.PositiveSmallIntegerField(
        "بزرگ‌نمایی نقشه", default=DEFAULT_ZOOM
    )
    maps_place_url = models.CharField(
        "پیوند صفحه‌ی گوگل مپس (اختیاری)",
        max_length=500,
        blank=True,
        help_text="جای‌گزین پیوند «مشاهده روی نقشه»؛ مسیریابی همیشه از مختصات ساخته می‌شود",
    )

    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "تنظیمات فوتر"
        verbose_name_plural = "تنظیمات فوتر"

    def clean(self):
        super().clean()
        errors: dict[str, str] = {}
        plain_fields = {
            "brandTitle": self.brand_title,
            "description": self.description,
            "copyrightText": self.copyright_text,
            "address": self.address,
        }
        for key, value in plain_fields.items():
            message = _plain_text_error(value)
            if message:
                errors[key] = message
        if self.phone and not is_valid_phone(self.phone):
            errors["phone"] = "شماره تماس معتبر نیست"
        if self.email and not is_valid_email(self.email):
            errors["email"] = "ایمیل معتبر نیست"
        errors.update(self._location_errors())
        if errors:
            raise ValidationError(errors)

    def _location_errors(self) -> dict[str, str]:
        errors: dict[str, str] = {}

        # نیم‌مختصات روی نقشه معنا ندارد و سوزن را جای اشتباه می‌گذارد
        if (self.latitude is None) != (self.longitude is None):
            missing = "latitude" if self.latitude is None else "longitude"
            errors[missing] = "عرض و طول جغرافیایی باید هر دو تنظیم شوند یا هیچ‌کدام"

        if self.latitude is not None and not (
            LATITUDE_RANGE[0] <= self.latitude <= LATITUDE_RANGE[1]
        ):
            errors["latitude"] = "عرض جغرافیایی باید بین ۹۰- و ۹۰ باشد"
        if self.longitude is not None and not (
            LONGITUDE_RANGE[0] <= self.longitude <= LONGITUDE_RANGE[1]
        ):
            errors["longitude"] = "طول جغرافیایی باید بین ۱۸۰- و ۱۸۰ باشد"

        # map_zoom تهی نمی‌پذیرد، اما full_clean متد clean را حتی وقتی
        # clean_fields خطا داده هم صدا می‌زند؛ مقایسه با None نباید بترکد
        if self.map_zoom is not None and not (
            ZOOM_RANGE[0] <= self.map_zoom <= ZOOM_RANGE[1]
        ):
            errors["mapZoom"] = (
                f"بزرگ‌نمایی نقشه باید بین {ZOOM_RANGE[0]} تا {ZOOM_RANGE[1]} باشد"
            )

        if self.maps_place_url and not is_google_maps_url(self.maps_place_url):
            errors["mapsPlaceUrl"] = "پیوند باید یک نشانی معتبر گوگل مپس باشد"
        return errors

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return "تنظیمات فوتر"

    # سه آیکن اطلاعات تماس همیشه با خود ردیف خوانده می‌شوند، وگرنه هر کدام
    # یک کوئری اضافه به هر رندر فوتر اضافه می‌کنند
    ICON_RELATIONS = ("address_icon", "phone_icon", "email_icon")

    @classmethod
    def load(cls) -> "FooterSettings":
        """ردیف تنظیمات را می‌سازد اگر نباشد — فقط برای مسیرهای مدیریت"""
        cls.objects.get_or_create(pk=1)
        return cls.current()

    @classmethod
    def current(cls) -> "FooterSettings":
        """خواندنی محض: فوتر روی هر صفحه است و نباید در GET بنویسد"""
        stored = (
            cls.objects.select_related(*cls.ICON_RELATIONS).filter(pk=1).first()
        )
        return stored or cls(pk=1)


class FooterSection(models.Model):
    """یک بخش فوتر — عنوان، چیدمان، ترتیب و وضعیت نمایش"""

    class Variant(models.TextChoices):
        COLUMN = "column", "ستون (فهرست عمودی)"
        STRIP = "strip", "نوار مزیت‌ها (ردیف افقی بالای فوتر)"

    title = models.CharField("عنوان", max_length=120, blank=True)
    variant = models.CharField(
        "چیدمان", max_length=20, choices=Variant.choices, default=Variant.COLUMN
    )
    description = models.TextField("توضیح زیر عنوان", max_length=400, blank=True)
    position = models.PositiveIntegerField("ترتیب", default=0)
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "بخش فوتر"
        verbose_name_plural = "بخش‌های فوتر"
        ordering = ["position", "id"]
        indexes = [
            models.Index(fields=["position", "id"], name="footer_section_order_idx")
        ]

    def clean(self):
        super().clean()
        errors: dict[str, str] = {}
        for key, value in (("title", self.title), ("description", self.description)):
            message = _plain_text_error(value)
            if message:
                errors[key] = message
        # ستون بدون عنوان در فوتر یک فهرست بی‌نام می‌شود؛ نوار مزیت‌ها اما
        # عمداً عنوان ندارد.
        if self.variant == self.Variant.COLUMN and not self.title.strip():
            errors.setdefault("title", "عنوان بخش الزامی است")
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title or f"بخش فوتر #{self.pk}"


class FooterItem(models.Model):
    """یک محتوای درون بخش فوتر — نوع آن تعیین می‌کند کدام فیلدها معنا دارند"""

    class ItemType(models.TextChoices):
        LINK = "link", "پیوند"
        TEXT = "text", "متن"
        IMAGE = "image", "تصویر"
        PHONE = "phone", "شماره تماس"
        EMAIL = "email", "ایمیل"
        ADDRESS = "address", "نشانی"
        SOCIAL = "social", "شبکه اجتماعی"

    section = models.ForeignKey(
        FooterSection,
        verbose_name="بخش",
        on_delete=models.CASCADE,
        related_name="items",
    )
    item_type = models.CharField(
        "نوع محتوا", max_length=20, choices=ItemType.choices, default=ItemType.LINK
    )
    label = models.CharField("عنوان", max_length=120, blank=True)
    url = models.CharField("نشانی مقصد", max_length=300, blank=True)
    text = models.TextField("متن", max_length=600, blank=True)
    image = models.ImageField("تصویر", upload_to="footer/items/", blank=True)
    icon_image = models.ForeignKey(
        FooterIcon,
        verbose_name="آیکن",
        on_delete=models.SET_NULL,
        related_name="items",
        null=True,
        blank=True,
    )
    icon = models.CharField(
        "ایموجی جایگزین",
        max_length=32,
        blank=True,
        help_text="وقتی آیکن تصویری انتخاب نشده باشد به کار می‌رود",
    )
    open_in_new_tab = models.BooleanField("باز شدن در تب جدید", default=False)
    static_page_key = models.CharField(
        "صفحه‌ی محتوایی مرتبط",
        max_length=40,
        blank=True,
        choices=PAGE_KEY_CHOICES,
        help_text="اگر مدیر آن صفحه را پنهان کند، این پیوند هم پنهان می‌شود",
    )
    position = models.PositiveIntegerField("ترتیب", default=0)
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "محتوای فوتر"
        verbose_name_plural = "محتواهای فوتر"
        ordering = ["position", "id"]
        indexes = [
            models.Index(
                fields=["section", "position", "id"], name="footer_item_order_idx"
            )
        ]

    def clean(self):
        super().clean()
        allowed = _TYPE_ALLOWED_FIELDS.get(self.item_type)
        if allowed is None:
            raise ValidationError({"itemType": "نوع محتوا پشتیبانی نمی‌شود"})

        errors: dict[str, str] = {}
        values = {
            "label": self.label,
            "url": self.url,
            "text": self.text,
            "image": self.image,
            "icon": self.icon,
            "icon_image": self.icon_image_id,
            "open_in_new_tab": self.open_in_new_tab,
            "static_page_key": self.static_page_key,
        }

        for field_name in _TYPE_REQUIRED_FIELDS.get(self.item_type, set()):
            value = values[field_name]
            if not (value.strip() if isinstance(value, str) else value):
                errors[_FIELD_ERROR_KEYS[field_name]] = _REQUIRED_FIELD_MESSAGES[
                    field_name
                ]

        for field_name, value in values.items():
            if field_name in allowed or not value:
                continue
            errors.setdefault(
                _FIELD_ERROR_KEYS[field_name],
                "این فیلد برای این نوع محتوا قابل استفاده نیست",
            )

        for field_name in ("label", "text", "icon"):
            message = _plain_text_error(values[field_name])
            if message:
                errors.setdefault(_FIELD_ERROR_KEYS[field_name], message)

        if self.url and "url" in allowed and not is_safe_url(self.url):
            errors.setdefault(
                "url", "نشانی باید مسیر داخلی (/...) یا آدرس http(s) باشد"
            )

        validator = _TEXT_VALIDATORS.get(self.item_type)
        if validator and self.text.strip() and not validator[0](self.text.strip()):
            errors.setdefault("text", validator[1])

        if self.static_page_key and self.static_page_key not in SUPPORTED_PAGE_KEYS:
            errors.setdefault("staticPageKey", "صفحه‌ی محتوایی پشتیبانی نمی‌شود")

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.label or self.text[:40] or f"محتوای فوتر #{self.pk}"
