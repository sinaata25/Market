from rest_framework import serializers

from staticpages.definitions import SUPPORTED_PAGE_KEYS

from .maps import ZOOM_RANGE
from .models import FooterIcon, FooterItem, FooterSection

# نام فیلد ورودی (camelCase) → نام فیلد مدل
_FIELD_RENAMES = {
    "isActive": "is_active",
    "itemType": "item_type",
    "openInNewTab": "open_in_new_tab",
    "staticPageKey": "static_page_key",
    "copyrightText": "copyright_text",
    "brandTitle": "brand_title",
    "showMap": "show_map",
    "mapZoom": "map_zoom",
    "mapsPlaceUrl": "maps_place_url",
    "iconId": "icon_image",
    "addressIconId": "address_icon",
    "phoneIconId": "phone_icon",
    "emailIconId": "email_icon",
    "altText": "alt_text",
}

# نام ورودی (camelCase) → نام فیلد مدل، برای ارجاع‌های آیکن
_ICON_FIELDS = {
    "iconId": "icon_image",
    "addressIconId": "address_icon",
    "phoneIconId": "phone_icon",
    "emailIconId": "email_icon",
}


class IconReferenceMixin:
    """شناسه‌ی آیکن را به شیء آیکن تبدیل می‌کند؛ null یعنی «بدون آیکن»"""

    def validate(self, data):
        data = super().validate(data)
        for input_name, field_name in _ICON_FIELDS.items():
            if field_name not in data:
                continue
            icon_id = data[field_name]
            if icon_id is None:
                data[field_name] = None
                continue
            icon = FooterIcon.objects.filter(pk=icon_id).first()
            if icon is None:
                raise serializers.ValidationError({input_name: "آیکن یافت نشد"})
            data[field_name] = icon
        return data


class BlankableDecimalField(serializers.DecimalField):
    """رشته‌ی خالی از فرم مدیریت یعنی «پاک کن»، نه «صفر»"""

    def validate_empty_values(self, data):
        if data == "":
            return True, None
        return super().validate_empty_values(data)


class RenamingSerializer(serializers.Serializer):
    """ورودی camelCase را به نام فیلدهای مدل برمی‌گرداند"""

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        return {_FIELD_RENAMES.get(key, key): item for key, item in value.items()}


class FooterSettingsSerializer(IconReferenceMixin, RenamingSerializer):
    brandTitle = serializers.CharField(
        max_length=120, required=False, allow_blank=True
    )
    description = serializers.CharField(
        max_length=600, required=False, allow_blank=True
    )
    copyrightText = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    address = serializers.CharField(max_length=300, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True)
    email = serializers.CharField(max_length=120, required=False, allow_blank=True)
    # محدوده‌ی مقادیر در مدل هم بررسی می‌شود؛ اینجا فقط شکل عدد کنترل می‌گردد
    latitude = BlankableDecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True
    )
    longitude = BlankableDecimalField(
        max_digits=10, decimal_places=6, required=False, allow_null=True
    )
    showMap = serializers.BooleanField(required=False)
    mapZoom = serializers.IntegerField(
        required=False, min_value=ZOOM_RANGE[0], max_value=ZOOM_RANGE[1]
    )
    mapsPlaceUrl = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )
    addressIconId = serializers.IntegerField(required=False, allow_null=True)
    phoneIconId = serializers.IntegerField(required=False, allow_null=True)
    emailIconId = serializers.IntegerField(required=False, allow_null=True)


class FooterSectionCreateSerializer(RenamingSerializer):
    title = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default=""
    )
    variant = serializers.ChoiceField(
        choices=FooterSection.Variant.choices,
        required=False,
        default=FooterSection.Variant.COLUMN,
    )
    description = serializers.CharField(
        max_length=400, required=False, allow_blank=True, default=""
    )
    isActive = serializers.BooleanField(required=False, default=True)


class FooterSectionUpdateSerializer(FooterSectionCreateSerializer):
    """همان فیلدهای ایجاد، اما هیچ‌کدام الزامی نیستند و پیش‌فرض ندارند"""

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.required = False
            field.default = serializers.empty
        return fields


class FooterItemCreateSerializer(IconReferenceMixin, RenamingSerializer):
    itemType = serializers.ChoiceField(choices=FooterItem.ItemType.choices)
    label = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default=""
    )
    url = serializers.CharField(
        max_length=300, required=False, allow_blank=True, default=""
    )
    text = serializers.CharField(
        max_length=600, required=False, allow_blank=True, default=""
    )
    icon = serializers.CharField(
        max_length=32, required=False, allow_blank=True, default=""
    )
    iconId = serializers.IntegerField(required=False, allow_null=True)
    openInNewTab = serializers.BooleanField(required=False, default=False)
    staticPageKey = serializers.ChoiceField(
        choices=SUPPORTED_PAGE_KEYS, required=False, allow_blank=True, default=""
    )
    isActive = serializers.BooleanField(required=False, default=True)


class FooterItemUpdateSerializer(FooterItemCreateSerializer):
    """نوع آیتم قابل تغییر است؛ سرویس فیلدهای بی‌ربط را پاک می‌کند"""

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.required = False
            field.default = serializers.empty
        return fields


class MoveSerializer(serializers.Serializer):
    direction = serializers.ChoiceField(choices=["up", "down"])


class FooterIconWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80)


class FooterTrustBadgeWriteSerializer(RenamingSerializer):
    """Complete metadata plus an optional replacement file, saved atomically."""

    label = serializers.CharField(max_length=120)
    url = serializers.CharField(max_length=300)
    altText = serializers.CharField(max_length=200, allow_blank=True, required=False, default="")
    position = serializers.IntegerField(min_value=0, max_value=2147483647, required=False)
    isActive = serializers.BooleanField(required=False, default=True)
    openInNewTab = serializers.BooleanField(required=False, default=True)
    file = serializers.FileField(source="image", required=False)

    def validate(self, data):
        if self.initial_data.get("embedCode") or self.initial_data.get("embed_code"):
            raise serializers.ValidationError({"embedCode": "کد HTML پشتیبانی نمی‌شود؛ تصویر و نشانی نماد را وارد کنید"})
        return data
