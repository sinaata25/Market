from rest_framework import serializers

from staticpages.definitions import SUPPORTED_PAGE_KEYS

from .models import FooterItem, FooterSection

# نام فیلد ورودی (camelCase) → نام فیلد مدل
_FIELD_RENAMES = {
    "isActive": "is_active",
    "itemType": "item_type",
    "openInNewTab": "open_in_new_tab",
    "staticPageKey": "static_page_key",
    "copyrightText": "copyright_text",
    "brandTitle": "brand_title",
}


class RenamingSerializer(serializers.Serializer):
    """ورودی camelCase را به نام فیلدهای مدل برمی‌گرداند"""

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        return {_FIELD_RENAMES.get(key, key): item for key, item in value.items()}


class FooterSettingsSerializer(RenamingSerializer):
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


class FooterItemCreateSerializer(RenamingSerializer):
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
