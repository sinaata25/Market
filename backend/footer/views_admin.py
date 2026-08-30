from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from accounts.permissions import ShopAdminRequiredMixin
from common.responses import fail, first_error_message, ok

from .dto import admin_item_dto, admin_section_dto, admin_settings_dto
from .files import schedule_footer_image_delete
from .images import image_upload_error
from .models import FooterItem, FooterSection, FooterSettings
from .revalidation import schedule_footer_revalidation
from .selectors import sections_queryset
from .serializers import (
    FooterItemCreateSerializer,
    FooterItemUpdateSerializer,
    FooterSectionCreateSerializer,
    FooterSectionUpdateSerializer,
    FooterSettingsSerializer,
    MoveSerializer,
)
from .services import (
    FooterValidationError,
    create_item,
    create_section,
    delete_item,
    delete_section,
    move_item,
    move_section,
    update_item,
    update_section,
    update_settings,
)


def _validation_failure(exc: FooterValidationError):
    message = first_error_message(exc.errors) or "پیکربندی معتبر نیست"
    return fail(message, 422, data={"fieldErrors": exc.errors})


def _sections_payload() -> dict:
    return {
        "sections": [
            admin_section_dto(section)
            for section in sections_queryset(active_only=False)
        ]
    }


class AdminFooterSettingsView(ShopAdminRequiredMixin, APIView):
    """تنظیمات سراسری فوتر — یک ردیف که همیشه وجود دارد"""

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return ok({"settings": admin_settings_dto(FooterSettings.load())})

    @extend_schema(
        request=FooterSettingsSerializer, responses={200: OpenApiTypes.OBJECT}
    )
    def patch(self, request):
        serializer = FooterSettingsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            settings_row = update_settings(**serializer.validated_data)
        except FooterValidationError as exc:
            return _validation_failure(exc)
        return ok({"settings": admin_settings_dto(settings_row)})


class AdminFooterLogoView(ShopAdminRequiredMixin, APIView):
    """آپلود/حذف لوگوی فوتر (multipart/form-data با فیلد file)"""

    def post(self, request):
        settings_row = FooterSettings.load()
        file = request.FILES.get("file")
        error = image_upload_error(file)
        if error:
            return fail(error, 422)

        old_name = settings_row.logo.name if settings_row.logo else ""
        old_storage = settings_row.logo.storage if settings_row.logo else None
        settings_row.logo = file
        try:
            settings_row.save(update_fields=["logo", "updated_at"])
        except DjangoValidationError as exc:
            messages = getattr(exc, "messages", None)
            return fail(messages[0] if messages else "تصویر معتبر نیست", 422)
        if old_name and old_name != settings_row.logo.name:
            schedule_footer_image_delete(
                old_name, old_storage, using=settings_row._state.db or "default"
            )
        schedule_footer_revalidation(using=settings_row._state.db or "default")
        return ok({"settings": admin_settings_dto(settings_row)}, status=201)

    def delete(self, request):
        settings_row = FooterSettings.load()
        if not settings_row.logo:
            return ok({"settings": admin_settings_dto(settings_row)})
        old_name = settings_row.logo.name
        old_storage = settings_row.logo.storage
        settings_row.logo = ""
        settings_row.save(update_fields=["logo", "updated_at"])
        schedule_footer_image_delete(
            old_name, old_storage, using=settings_row._state.db or "default"
        )
        schedule_footer_revalidation(using=settings_row._state.db or "default")
        return ok({"settings": admin_settings_dto(settings_row)})


class AdminFooterSectionListView(ShopAdminRequiredMixin, APIView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return ok(_sections_payload())

    @extend_schema(
        request=FooterSectionCreateSerializer, responses={201: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = FooterSectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            section = create_section(**serializer.validated_data)
        except FooterValidationError as exc:
            return _validation_failure(exc)
        return ok({"section": admin_section_dto(section)}, status=201)


class AdminFooterSectionDetailView(ShopAdminRequiredMixin, APIView):
    def _get(self, pk: int) -> FooterSection | None:
        return sections_queryset(active_only=False).filter(pk=pk).first()

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request, pk: int):
        section = self._get(pk)
        if section is None:
            return fail("بخش فوتر یافت نشد", 404)
        return ok({"section": admin_section_dto(section)})

    @extend_schema(
        request=FooterSectionUpdateSerializer, responses={200: OpenApiTypes.OBJECT}
    )
    def patch(self, request, pk: int):
        section = self._get(pk)
        if section is None:
            return fail("بخش فوتر یافت نشد", 404)
        serializer = FooterSectionUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            section = update_section(section, **serializer.validated_data)
        except FooterValidationError as exc:
            return _validation_failure(exc)
        return ok({"section": admin_section_dto(section)})

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def delete(self, request, pk: int):
        section = self._get(pk)
        if section is None:
            return fail("بخش فوتر یافت نشد", 404)
        delete_section(section)
        return ok({"deleted": True})


class AdminFooterSectionMoveView(ShopAdminRequiredMixin, APIView):
    @extend_schema(request=MoveSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request, pk: int):
        section = FooterSection.objects.filter(pk=pk).first()
        if section is None:
            return fail("بخش فوتر یافت نشد", 404)
        serializer = MoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        move_section(section, serializer.validated_data["direction"])
        return ok(_sections_payload())


class AdminFooterItemListView(ShopAdminRequiredMixin, APIView):
    @extend_schema(
        request=FooterItemCreateSerializer, responses={201: OpenApiTypes.OBJECT}
    )
    def post(self, request, pk: int):
        section = FooterSection.objects.filter(pk=pk).first()
        if section is None:
            return fail("بخش فوتر یافت نشد", 404)
        serializer = FooterItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = create_item(section=section, **serializer.validated_data)
        except FooterValidationError as exc:
            return _validation_failure(exc)
        return ok({"item": admin_item_dto(item)}, status=201)


class AdminFooterItemDetailView(ShopAdminRequiredMixin, APIView):
    def _get(self, pk: int) -> FooterItem | None:
        return FooterItem.objects.filter(pk=pk).first()

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request, pk: int):
        item = self._get(pk)
        if item is None:
            return fail("محتوای فوتر یافت نشد", 404)
        return ok({"item": admin_item_dto(item)})

    @extend_schema(
        request=FooterItemUpdateSerializer, responses={200: OpenApiTypes.OBJECT}
    )
    def patch(self, request, pk: int):
        item = self._get(pk)
        if item is None:
            return fail("محتوای فوتر یافت نشد", 404)
        serializer = FooterItemUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            item = update_item(item, **serializer.validated_data)
        except FooterValidationError as exc:
            return _validation_failure(exc)
        return ok({"item": admin_item_dto(item)})

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def delete(self, request, pk: int):
        item = self._get(pk)
        if item is None:
            return fail("محتوای فوتر یافت نشد", 404)
        delete_item(item)
        return ok({"deleted": True})


class AdminFooterItemMoveView(ShopAdminRequiredMixin, APIView):
    @extend_schema(request=MoveSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request, pk: int):
        item = FooterItem.objects.filter(pk=pk).first()
        if item is None:
            return fail("محتوای فوتر یافت نشد", 404)
        serializer = MoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = move_item(item, serializer.validated_data["direction"])
        return ok({"items": [admin_item_dto(row) for row in items]})


class AdminFooterItemImageView(ShopAdminRequiredMixin, APIView):
    """آپلود/حذف تصویر یک آیتم فوتر (multipart/form-data با فیلد file)"""

    def post(self, request, pk: int):
        item = FooterItem.objects.filter(pk=pk).first()
        if item is None:
            return fail("محتوای فوتر یافت نشد", 404)
        file = request.FILES.get("file")
        error = image_upload_error(file)
        if error:
            return fail(error, 422)

        old_name = item.image.name if item.image else ""
        old_storage = item.image.storage if item.image else None
        item.image = file
        try:
            item.save()
        except DjangoValidationError as exc:
            messages = getattr(exc, "messages", None)
            return fail(messages[0] if messages else "تصویر معتبر نیست", 422)
        if old_name and old_name != item.image.name:
            schedule_footer_image_delete(
                old_name, old_storage, using=item._state.db or "default"
            )
        schedule_footer_revalidation(using=item._state.db or "default")
        return ok({"item": admin_item_dto(item)}, status=201)

    def delete(self, request, pk: int):
        item = FooterItem.objects.filter(pk=pk).first()
        if item is None:
            return fail("محتوای فوتر یافت نشد", 404)
        if not item.image:
            return ok({"item": admin_item_dto(item)})
        old_name = item.image.name
        old_storage = item.image.storage
        item.image = ""
        try:
            item.save()
        except DjangoValidationError as exc:
            messages = getattr(exc, "messages", None)
            # آیتم تصویری بدون تصویر معتبر نیست؛ اول نوعش باید عوض شود
            return fail(messages[0] if messages else "تصویر معتبر نیست", 422)
        schedule_footer_image_delete(
            old_name, old_storage, using=item._state.db or "default"
        )
        schedule_footer_revalidation(using=item._state.db or "default")
        return ok({"item": admin_item_dto(item)})
