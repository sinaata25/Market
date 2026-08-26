from PIL import Image, UnidentifiedImageError
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from accounts.permissions import ShopAdminRequiredMixin
from common.responses import fail, first_error_message, ok

from .banner_files import schedule_banner_image_delete
from .dto import admin_banner_dto, admin_section_dto
from .models import BANNER_IMAGE_FIELDS, Banner, HomepageSection
from .selectors import banners_queryset, sections_queryset
from .serializers import (
    BannerWriteSerializer,
    HomepageSectionCreateSerializer,
    HomepageSectionMoveSerializer,
    HomepageSectionUpdateSerializer,
)
from .services import (
    HomepageValidationError,
    create_banner,
    create_section,
    delete_section,
    move_section,
    update_banner,
    update_section,
)

MAX_BANNER_IMAGE_SIZE = 5 * 1024 * 1024


def _validation_failure(exc: HomepageValidationError):
    message = first_error_message(exc.errors) or "پیکربندی معتبر نیست"
    return fail(message, 422, data={"fieldErrors": exc.errors})


class AdminHomepageSectionListView(ShopAdminRequiredMixin, APIView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        sections = sections_queryset(active_only=False)
        return ok({"sections": [admin_section_dto(section) for section in sections]})

    @extend_schema(
        request=HomepageSectionCreateSerializer, responses={201: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = HomepageSectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data["section_type"] = data.pop("sectionType")
        if "isActive" in data:
            data["is_active"] = data.pop("isActive")
        try:
            section = create_section(**data)
        except HomepageValidationError as exc:
            return _validation_failure(exc)
        return ok({"section": admin_section_dto(section)}, status=201)


class AdminHomepageSectionDetailView(ShopAdminRequiredMixin, APIView):
    def _get(self, pk: int) -> HomepageSection | None:
        return sections_queryset(active_only=False).filter(pk=pk).first()

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request, pk: int):
        section = self._get(pk)
        if section is None:
            return fail("بخش یافت نشد", 404)
        return ok({"section": admin_section_dto(section)})

    @extend_schema(
        request=HomepageSectionUpdateSerializer, responses={200: OpenApiTypes.OBJECT}
    )
    def patch(self, request, pk: int):
        section = self._get(pk)
        if section is None:
            return fail("بخش یافت نشد", 404)
        serializer = HomepageSectionUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if "isActive" in data:
            data["is_active"] = data.pop("isActive")
        try:
            section = update_section(section, **data)
        except HomepageValidationError as exc:
            return _validation_failure(exc)
        return ok({"section": admin_section_dto(section)})

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def delete(self, request, pk: int):
        section = self._get(pk)
        if section is None:
            return fail("بخش یافت نشد", 404)
        delete_section(section)
        return ok({"deleted": True})


class AdminHomepageSectionMoveView(ShopAdminRequiredMixin, APIView):
    @extend_schema(
        request=HomepageSectionMoveSerializer, responses={200: OpenApiTypes.OBJECT}
    )
    def post(self, request, pk: int):
        section = sections_queryset(active_only=False).filter(pk=pk).first()
        if section is None:
            return fail("بخش یافت نشد", 404)
        serializer = HomepageSectionMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        move_section(section, serializer.validated_data["direction"])
        sections = sections_queryset(active_only=False)
        return ok({"sections": [admin_section_dto(item) for item in sections]})


class AdminBannerListView(ShopAdminRequiredMixin, APIView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        banners = banners_queryset()
        return ok({"banners": [admin_banner_dto(banner) for banner in banners]})

    @extend_schema(
        request=BannerWriteSerializer, responses={201: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = BannerWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            banner = create_banner(**serializer.validated_data)
        except HomepageValidationError as exc:
            return _validation_failure(exc)
        return ok({"banner": admin_banner_dto(banner)}, status=201)


class AdminBannerDetailView(ShopAdminRequiredMixin, APIView):
    def _get(self, pk: int) -> Banner | None:
        return Banner.objects.filter(pk=pk).first()

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request, pk: int):
        banner = self._get(pk)
        if banner is None:
            return fail("بنر یافت نشد", 404)
        return ok({"banner": admin_banner_dto(banner)})

    @extend_schema(
        request=BannerWriteSerializer, responses={200: OpenApiTypes.OBJECT}
    )
    def patch(self, request, pk: int):
        banner = self._get(pk)
        if banner is None:
            return fail("بنر یافت نشد", 404)
        serializer = BannerWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            banner = update_banner(banner, **serializer.validated_data)
        except HomepageValidationError as exc:
            return _validation_failure(exc)
        return ok({"banner": admin_banner_dto(banner)})

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def delete(self, request, pk: int):
        banner = self._get(pk)
        if banner is None:
            return fail("بنر یافت نشد", 404)
        stored_images = [
            (field.name, field.storage)
            for field in (
                getattr(banner, field_name)
                for field_name in BANNER_IMAGE_FIELDS.values()
            )
            if field
        ]
        using = banner._state.db or "default"
        banner.delete()
        for name, storage in stored_images:
            schedule_banner_image_delete(name, storage, using=using)
        return ok({"deleted": True})


class AdminBannerImageView(ShopAdminRequiredMixin, APIView):
    """آپلود/حذف یک نسخه‌ی تصویر بنر (multipart/form-data با فیلد file)

    variant یکی از کلیدهای BANNER_IMAGE_FIELDS است: desktop یا mobile.
    هر نسخه مستقل ذخیره و حذف می‌شود.
    """

    def _resolve(self, pk: int, variant: str) -> tuple[Banner | None, str]:
        field_name = BANNER_IMAGE_FIELDS.get(variant, "")
        if not field_name:
            return None, ""
        return Banner.objects.filter(pk=pk).first(), field_name

    def post(self, request, pk: int, variant: str):
        banner, field_name = self._resolve(pk, variant)
        if not field_name:
            return fail("نسخه‌ی تصویر پشتیبانی نمی‌شود", 404)
        if banner is None:
            return fail("بنر یافت نشد", 404)
        file = request.FILES.get("file")
        if file is None:
            return fail("فایل تصویر ارسال نشده است", 422)
        if file.size > MAX_BANNER_IMAGE_SIZE:
            return fail("حجم تصویر حداکثر ۵ مگابایت باشد", 422)
        try:
            image = Image.open(file)
            image.verify()
            file.seek(0)
        except (UnidentifiedImageError, OSError):
            return fail("فایل ارسال‌شده تصویر معتبر نیست", 422)

        current = getattr(banner, field_name)
        old_name = current.name if current else ""
        old_storage = current.storage if current else None
        setattr(banner, field_name, file)
        try:
            banner.save(update_fields=[field_name])
        except DjangoValidationError as exc:
            messages = getattr(exc, "messages", None)
            return fail(messages[0] if messages else "تصویر معتبر نیست", 422)
        if old_name and old_name != getattr(banner, field_name).name:
            schedule_banner_image_delete(
                old_name, old_storage, using=banner._state.db or "default"
            )
        return ok({"banner": admin_banner_dto(banner)}, status=201)

    def delete(self, request, pk: int, variant: str):
        banner, field_name = self._resolve(pk, variant)
        if not field_name:
            return fail("نسخه‌ی تصویر پشتیبانی نمی‌شود", 404)
        if banner is None:
            return fail("بنر یافت نشد", 404)
        current = getattr(banner, field_name)
        if not current:
            return ok({"banner": admin_banner_dto(banner)})
        old_name = current.name
        old_storage = current.storage
        setattr(banner, field_name, "")
        banner.save(update_fields=[field_name])
        schedule_banner_image_delete(
            old_name, old_storage, using=banner._state.db or "default"
        )
        return ok({"banner": admin_banner_dto(banner)})
