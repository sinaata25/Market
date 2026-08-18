from collections.abc import Mapping

from rest_framework import serializers


class StaticPageErrorEnvelopeSerializer(serializers.Serializer):
    ok = serializers.BooleanField(default=False)
    error = serializers.CharField()
    data = serializers.JSONField(required=False)


class PublicStaticPageSerializer(serializers.Serializer):
    key = serializers.CharField()
    isVisible = serializers.BooleanField()
    sections = serializers.DictField(child=serializers.BooleanField())
    content = serializers.JSONField()


class PublicStaticPageListDataSerializer(serializers.Serializer):
    pages = PublicStaticPageSerializer(many=True)


class PublicStaticPageListEnvelopeSerializer(serializers.Serializer):
    ok = serializers.BooleanField(default=True)
    data = PublicStaticPageListDataSerializer()


class PublicStaticPageDetailDataSerializer(serializers.Serializer):
    page = PublicStaticPageSerializer()


class PublicStaticPageDetailEnvelopeSerializer(serializers.Serializer):
    ok = serializers.BooleanField(default=True)
    data = PublicStaticPageDetailDataSerializer()


class PublicStaticPageVisibilitySerializer(serializers.Serializer):
    key = serializers.CharField()
    isVisible = serializers.BooleanField()


class PublicStaticPageVisibilityDataSerializer(serializers.Serializer):
    pages = PublicStaticPageVisibilitySerializer(many=True)


class PublicStaticPageVisibilityEnvelopeSerializer(serializers.Serializer):
    ok = serializers.BooleanField(default=True)
    data = PublicStaticPageVisibilityDataSerializer()


class StaticPageSummarySerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    path = serializers.CharField()
    isVisible = serializers.BooleanField()
    updatedAt = serializers.DateTimeField(allow_null=True)
    updatedBy = serializers.CharField(allow_null=True)


class StaticPageFieldSerializer(serializers.Serializer):
    id = serializers.CharField()
    label = serializers.CharField()
    group = serializers.CharField()
    control = serializers.ChoiceField(
        choices=["text", "textarea", "email", "tel", "url"]
    )
    required = serializers.BooleanField()
    maxLength = serializers.IntegerField()
    rows = serializers.IntegerField(required=False)
    dir = serializers.ChoiceField(choices=["rtl", "ltr"], required=False)
    help = serializers.CharField(required=False)
    value = serializers.CharField(allow_blank=True)


class StaticPageSectionSerializer(serializers.Serializer):
    id = serializers.CharField()
    label = serializers.CharField()
    visible = serializers.BooleanField()


class AdminStaticPageSerializer(StaticPageSummarySerializer):
    sections = StaticPageSectionSerializer(many=True)
    fields = StaticPageFieldSerializer(many=True)


class AdminStaticPageListDataSerializer(serializers.Serializer):
    pages = StaticPageSummarySerializer(many=True)


class AdminStaticPageListEnvelopeSerializer(serializers.Serializer):
    ok = serializers.BooleanField(default=True)
    data = AdminStaticPageListDataSerializer()


class AdminStaticPageDetailDataSerializer(serializers.Serializer):
    page = AdminStaticPageSerializer()


class AdminStaticPageDetailEnvelopeSerializer(serializers.Serializer):
    ok = serializers.BooleanField(default=True)
    data = AdminStaticPageDetailDataSerializer()


class StaticPagePatchSerializer(serializers.Serializer):
    fields = serializers.DictField(
        required=False,
        allow_empty=False,
        error_messages={
            "required": "فیلد fields الزامی است",
            "not_a_dict": "fields باید یک شیء از شناسه و مقدار متنی باشد",
            "empty": "حداقل یک فیلد لازم است",
        },
    )
    isVisible = serializers.BooleanField(required=False)
    sections = serializers.DictField(
        child=serializers.BooleanField(),
        required=False,
        allow_empty=False,
        error_messages={
            "not_a_dict": "sections باید یک شیء از شناسه بخش و وضعیت باشد",
            "empty": "حداقل وضعیت یک بخش لازم است",
        },
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("حداقل یک تغییر لازم است")
        return attrs

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unexpected = set(data) - {"fields", "isVisible", "sections"}
            if unexpected:
                field = sorted(str(key) for key in unexpected)[0]
                raise serializers.ValidationError(
                    {field: "این کلید در درخواست قابل ارسال نیست"}
                )
        return super().to_internal_value(data)
