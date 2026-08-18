from collections.abc import Mapping

from rest_framework import serializers


class StaticPageErrorEnvelopeSerializer(serializers.Serializer):
    ok = serializers.BooleanField(default=False)
    error = serializers.CharField()
    data = serializers.JSONField(required=False)


class PublicStaticPageSerializer(serializers.Serializer):
    key = serializers.CharField()
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


class StaticPageSummarySerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    path = serializers.CharField()
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


class AdminStaticPageSerializer(StaticPageSummarySerializer):
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


class StaticPageFieldsPatchSerializer(serializers.Serializer):
    fields = serializers.DictField(
        allow_empty=False,
        error_messages={
            "required": "فیلد fields الزامی است",
            "not_a_dict": "fields باید یک شیء از شناسه و مقدار متنی باشد",
            "empty": "حداقل یک فیلد لازم است",
        },
    )

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unexpected = set(data) - {"fields"}
            if unexpected:
                field = sorted(str(key) for key in unexpected)[0]
                raise serializers.ValidationError(
                    {field: "فقط fields در این درخواست قابل ارسال است"}
                )
        return super().to_internal_value(data)
