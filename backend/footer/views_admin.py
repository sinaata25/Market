from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from accounts.permissions import ShopAdminRequiredMixin
from catalog.validators import validate_category_icon
from common.responses import fail, first_error_message, ok

from .dto import (
    admin_icon_dto,
    admin_item_dto,
    admin_section_dto,
    admin_settings_dto,
)
from .geocoding import GeocodingUnavailable, reverse, search
from .maps import LATITUDE_RANGE, LONGITUDE_RANGE, format_coordinate
from .files import schedule_footer_image_delete
from .images import image_upload_error
from .models import FooterIcon, FooterItem, FooterSection, FooterSettings
from .revalidation import schedule_footer_revalidation
from .selectors import icons_queryset, sections_queryset
from .serializers import (
    FooterIconWriteSerializer,
    FooterItemCreateSerializer,
    FooterItemUpdateSerializer,
    FooterSectionCreateSerializer,
    FooterSectionUpdateSerializer,
    FooterSettingsSerializer,
    MoveSerializer,
)
from .services import (
    FooterValidationError,
    create_icon,
    create_item,
    create_section,
    delete_icon,
    delete_item,
    delete_section,
    move_item,
    move_section,
    update_icon,
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


def _icon_file_error(file) -> str | None:
    """همان قواعد آیکن دسته‌بندی: PNG یا SVG ایمن، حداکثر ۵ مگابایت"""
    if file is None:
        return "فایل آیکن ارسال نشده است"
    try:
        validate_category_icon(file)
    except DjangoValidationError as exc:
        messages = getattr(exc, "messages", None)
        return messages[0] if messages else "فایل آیکن معتبر نیست"
    return None


class AdminFooterIconListView(ShopAdminRequiredMixin, APIView):
    """کتابخانه‌ی آیکن‌های فوتر — ساخت با multipart (name + file)"""

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return ok({"icons": [admin_icon_dto(icon) for icon in icons_queryset()]})

    @extend_schema(
        request=FooterIconWriteSerializer, responses={201: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = FooterIconWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = request.FILES.get("file")
        error = _icon_file_error(file)
        if error:
            return fail(error, 422)
        try:
            icon = create_icon(name=serializer.validated_data["name"], image=file)
        except FooterValidationError as exc:
            return _validation_failure(exc)
        return ok({"icon": admin_icon_dto(icon)}, status=201)


class AdminFooterIconDetailView(ShopAdminRequiredMixin, APIView):
    def _get(self, pk: int) -> FooterIcon | None:
        return FooterIcon.objects.filter(pk=pk).first()

    @extend_schema(
        request=FooterIconWriteSerializer, responses={200: OpenApiTypes.OBJECT}
    )
    def patch(self, request, pk: int):
        icon = self._get(pk)
        if icon is None:
            return fail("آیکن یافت نشد", 404)
        serializer = FooterIconWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            icon = update_icon(icon, **serializer.validated_data)
        except FooterValidationError as exc:
            return _validation_failure(exc)
        return ok({"icon": admin_icon_dto(icon)})

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def delete(self, request, pk: int):
        icon = self._get(pk)
        if icon is None:
            return fail("آیکن یافت نشد", 404)
        # جاهایی که از آن استفاده می‌کردند بی‌آیکن می‌شوند، نه خراب
        delete_icon(icon)
        return ok({"deleted": True})


class AdminFooterIconImageView(ShopAdminRequiredMixin, APIView):
    """تعویض فایل یک آیکن — همه‌ی جاهایی که از آن استفاده می‌کنند با هم عوض می‌شوند"""

    def post(self, request, pk: int):
        icon = FooterIcon.objects.filter(pk=pk).first()
        if icon is None:
            return fail("آیکن یافت نشد", 404)
        file = request.FILES.get("file")
        error = _icon_file_error(file)
        if error:
            return fail(error, 422)

        old_name = icon.image.name if icon.image else ""
        old_storage = icon.image.storage if icon.image else None
        try:
            icon = update_icon(icon, image=file)
        except FooterValidationError as exc:
            return _validation_failure(exc)
        if old_name and old_name != icon.image.name:
            schedule_footer_image_delete(
                old_name, old_storage, using=icon._state.db or "default"
            )
        return ok({"icon": admin_icon_dto(icon)}, status=201)


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


class GeocodingThrottle(UserRateThrottle):
    """سرویس نشانی مهمان ماست؛ سیاست استفاده‌اش نرخ پایین می‌خواهد"""

    scope = "footer_geocode"


class AdminFooterGeocodeSearchView(ShopAdminRequiredMixin, APIView):
    """جست‌وجوی نشانی برای انتخابگر نقشه — فقط مدیران داشبورد"""

    throttle_classes = [GeocodingThrottle]

    @extend_schema(
        parameters=[OpenApiParameter("q", str, description="عبارت جست‌وجو")],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        if not query:
            return fail("عبارت جست‌وجو خالی است", 422)
        try:
            results = search(query)
        except GeocodingUnavailable:
            return fail("سرویس جست‌وجوی نشانی در دسترس نیست", 503)
        return ok(
            {
                "results": [
                    {
                        "label": result.label,
                        "latitude": format_coordinate(result.latitude),
                        "longitude": format_coordinate(result.longitude),
                    }
                    for result in results
                ]
            }
        )


class AdminFooterGeocodeReverseView(ShopAdminRequiredMixin, APIView):
    """نشانی خوانای یک نقطه‌ی روی نقشه — مدیر همچنان می‌تواند ویرایشش کند"""

    throttle_classes = [GeocodingThrottle]

    @extend_schema(
        parameters=[
            OpenApiParameter("lat", str, description="عرض جغرافیایی"),
            OpenApiParameter("lng", str, description="طول جغرافیایی"),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        latitude = _bounded_decimal(request.query_params.get("lat"), *LATITUDE_RANGE)
        longitude = _bounded_decimal(request.query_params.get("lng"), *LONGITUDE_RANGE)
        if latitude is None or longitude is None:
            return fail("مختصات معتبر نیست", 422)
        try:
            address = reverse(latitude, longitude)
        except GeocodingUnavailable:
            return fail("سرویس نشانی در دسترس نیست", 503)
        return ok({"address": address or None})


def _bounded_decimal(raw, low: Decimal, high: Decimal) -> Decimal | None:
    if raw is None:
        return None
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return None
    if not value.is_finite() or not low <= value <= high:
        return None
    return value
