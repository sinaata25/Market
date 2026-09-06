from django.core.exceptions import ValidationError
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from accounts.permissions import ShopAdminRequiredMixin
from common.responses import fail, first_error_message, ok
from .dto import admin_button_dto
from .selectors import buttons_queryset
from .serializers import ButtonWriteSerializer, FIELD_NAMES, MoveSerializer
from .services import create_button, delete_button, move_button, update_button
from .validation import PLATFORMS, validate_contact_icon


def validation_failure(errors):
    if isinstance(errors, ValidationError):
        errors = getattr(errors, "message_dict", {"icon": errors.messages})
    fields = {FIELD_NAMES.get(key, key): first_error_message(value) for key, value in errors.items()}
    return fail(first_error_message(fields), 422, data={"fieldErrors": fields})


def buttons_payload():
    return {"buttons": [admin_button_dto(button) for button in buttons_queryset()]}


class AdminButtonListView(ShopAdminRequiredMixin, APIView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return ok({**buttons_payload(), "platforms": [{"value": key, "label": label, "field": field} for key, label, field in PLATFORMS]})

    @extend_schema(request=ButtonWriteSerializer, responses={201: OpenApiTypes.OBJECT})
    def post(self, request):
        serializer = ButtonWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_failure(serializer.errors)
        try:
            button = create_button(**serializer.validated_data)
        except ValidationError as exc:
            return validation_failure(exc)
        return ok({"button": admin_button_dto(button)}, status=201)


class AdminButtonDetailView(ShopAdminRequiredMixin, APIView):
    @extend_schema(request=ButtonWriteSerializer, responses={200: OpenApiTypes.OBJECT})
    def patch(self, request, pk):
        button = buttons_queryset().filter(pk=pk).first()
        if button is None:
            return fail("دکمه یافت نشد", 404)
        serializer = ButtonWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return validation_failure(serializer.errors)
        try:
            button = update_button(button, **serializer.validated_data)
        except ValidationError as exc:
            return validation_failure(exc)
        return ok({"button": admin_button_dto(button)})

    def delete(self, request, pk):
        button = buttons_queryset().filter(pk=pk).first()
        if button is None:
            return fail("دکمه یافت نشد", 404)
        delete_button(button)
        return ok({"deleted": True})


class AdminButtonMoveView(ShopAdminRequiredMixin, APIView):
    @extend_schema(request=MoveSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request, pk):
        button = buttons_queryset().filter(pk=pk).first()
        if button is None:
            return fail("دکمه یافت نشد", 404)
        serializer = MoveSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_failure(serializer.errors)
        move_button(button, serializer.validated_data["direction"])
        return ok(buttons_payload())


class AdminButtonIconView(ShopAdminRequiredMixin, APIView):
    def post(self, request, pk):
        button = buttons_queryset().filter(pk=pk).first()
        if button is None:
            return fail("دکمه یافت نشد", 404)
        file = request.FILES.get("file")
        if file is None:
            return validation_failure({"icon": "فایل آیکن ارسال نشده است"})
        try:
            validate_contact_icon(file)
            button = update_button(button, icon=file)
        except ValidationError as exc:
            return validation_failure(exc)
        return ok({"button": admin_button_dto(button)}, status=201)

    def delete(self, request, pk):
        button = buttons_queryset().filter(pk=pk).first()
        if button is None:
            return fail("دکمه یافت نشد", 404)
        button = update_button(button, icon="")
        return ok({"button": admin_button_dto(button)})
