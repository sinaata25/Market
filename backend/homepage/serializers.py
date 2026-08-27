from rest_framework import serializers

from catalog.models import Brand, Category

from .models import (
    INTERCHANGEABLE_SECTION_TYPES,
    Banner,
    HomepageSection,
    SORT_CHOICES,
    THEME_CHOICES,
)


class HomepageSectionCreateSerializer(serializers.Serializer):
    sectionType = serializers.ChoiceField(choices=HomepageSection.SectionType.choices)
    title = serializers.CharField(
        max_length=150, required=False, allow_blank=True, default=""
    )
    isActive = serializers.BooleanField(required=False, default=True)
    bannerId = serializers.IntegerField(required=False, allow_null=True)
    categorySlug = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    brandSlug = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    sort = serializers.ChoiceField(
        choices=SORT_CHOICES, required=False, allow_blank=True, default=""
    )
    limit = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=24
    )

    def validate(self, data):
        if "bannerId" in data:
            banner_id = data.pop("bannerId")
            if banner_id is None:
                data["banner"] = None
            else:
                banner = Banner.objects.filter(pk=banner_id).first()
                if banner is None:
                    raise serializers.ValidationError({"bannerId": "بنر یافت نشد"})
                data["banner"] = banner

        if "categorySlug" in data:
            slug = data.pop("categorySlug")
            if not slug:
                data["category"] = None
            else:
                category = Category.objects.filter(slug=slug).first()
                if category is None:
                    raise serializers.ValidationError(
                        {"categorySlug": "دسته‌بندی یافت نشد"}
                    )
                data["category"] = category

        if "brandSlug" in data:
            slug = data.pop("brandSlug")
            if not slug:
                data["brand"] = None
            else:
                brand = Brand.objects.filter(slug=slug).first()
                if brand is None:
                    raise serializers.ValidationError({"brandSlug": "برند یافت نشد"})
                data["brand"] = brand

        return data


class HomepageSectionUpdateSerializer(HomepageSectionCreateSerializer):
    """همان فیلدهای ایجاد؛ نوع بخش پس از ایجاد قابل تغییر نیست

    تنها استثنا تعویض بین «محصولات برند» و «محصولات دسته‌بندی» است — این دو
    فقط در مرجعشان فرق دارند، پس مدیر می‌تواند بدون ساختن بخش تازه (و از دست
    دادن جایش در ترتیب صفحه) یکی را به دیگری تبدیل کند. نوع فعلی بخش از
    context با کلید `section_type` گرفته می‌شود.
    """

    def get_fields(self):
        fields = super().get_fields()
        fields.pop("sectionType", None)
        for field in fields.values():
            field.required = False
        return fields

    def to_internal_value(self, data):
        requested_type = data.get("sectionType") if isinstance(data, dict) else None
        current_type = self.context.get("section_type")
        switching = requested_type is not None and requested_type != current_type
        if switching and not {
            requested_type,
            current_type,
        } <= INTERCHANGEABLE_SECTION_TYPES:
            raise serializers.ValidationError(
                {"sectionType": "نوع بخش پس از ایجاد قابل تغییر نیست"}
            )
        value = super().to_internal_value(data)
        if switching:
            value["section_type"] = requested_type
        return value


class HomepageSectionMoveSerializer(serializers.Serializer):
    direction = serializers.ChoiceField(choices=["up", "down"])


class BannerWriteSerializer(serializers.Serializer):
    title = serializers.CharField(
        max_length=150, required=False, allow_blank=True, default=""
    )
    subtitle = serializers.CharField(
        max_length=300, required=False, allow_blank=True, default=""
    )
    theme = serializers.ChoiceField(choices=THEME_CHOICES, required=False, default="brand")
    linkUrl = serializers.CharField(
        max_length=300, required=False, allow_blank=True, default=""
    )
    linkLabel = serializers.CharField(
        max_length=60, required=False, allow_blank=True, default=""
    )
    isActive = serializers.BooleanField(required=False, default=True)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        renamed = dict(value)
        if "linkUrl" in renamed:
            renamed["link_url"] = renamed.pop("linkUrl")
        if "linkLabel" in renamed:
            renamed["link_label"] = renamed.pop("linkLabel")
        if "isActive" in renamed:
            renamed["is_active"] = renamed.pop("isActive")
        return renamed
