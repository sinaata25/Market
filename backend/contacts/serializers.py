from rest_framework import serializers
from footer.models import FooterIcon
from .models import FloatingContactButton
from .validation import ICON_NAMES


FIELD_NAMES = {
    "phone_number": "phoneNumber", "icon_name": "iconName", "library_icon": "iconId",
    "tooltip_text": "tooltipText", "is_active": "isActive",
    "open_in_new_tab": "openInNewTab", "display_order": "displayOrder",
}


class ButtonWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    platform = serializers.RegexField(r"^[a-z][a-z0-9_-]*$", max_length=40)
    phoneNumber = serializers.CharField(source="phone_number", max_length=40, required=False, allow_blank=True)
    username = serializers.CharField(max_length=500, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    url = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    iconName = serializers.ChoiceField(source="icon_name", choices=ICON_NAMES, required=False, allow_blank=True)
    iconId = serializers.PrimaryKeyRelatedField(source="library_icon", queryset=FooterIcon.objects.all(), required=False, allow_null=True)
    tooltipText = serializers.CharField(source="tooltip_text", max_length=200, required=False, allow_blank=True)
    isActive = serializers.BooleanField(source="is_active", required=False)
    openInNewTab = serializers.BooleanField(source="open_in_new_tab", required=False)
    position = serializers.ChoiceField(choices=FloatingContactButton.Position.choices, required=False)
    displayOrder = serializers.IntegerField(source="display_order", min_value=0, max_value=2147483647, required=False)


class MoveSerializer(serializers.Serializer):
    direction = serializers.ChoiceField(choices=["up", "down"])
