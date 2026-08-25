from collections.abc import Mapping

from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from accounts.permissions import ShopAdminRequiredMixin
from common.responses import fail, first_error_message, ok

from .definitions import SUPPORTED_PAGE_KEYS, get_page_definition
from .dto import admin_page_dto, page_summary_dto
from .serializers import (
    AdminStaticPageDetailEnvelopeSerializer,
    AdminStaticPageListEnvelopeSerializer,
    StaticPageErrorEnvelopeSerializer,
    StaticPagePatchSerializer,
)
from .services import (
    PageContentValidationError,
    page_content,
    page_contents,
    update_page,
)


def _flatten_errors(detail, prefix: str = "request") -> dict[str, str]:
    if isinstance(detail, Mapping):
        flattened: dict[str, str] = {}
        for key, value in detail.items():
            nested_prefix = (
                str(key) if prefix == "request" else f"{prefix}.{key}"
            )
            flattened.update(_flatten_errors(value, nested_prefix))
        return flattened
    if isinstance(detail, (list, tuple)):
        if not detail:
            return {prefix: "مقدار نامعتبر است"}
        return _flatten_errors(detail[0], prefix)
    return {prefix: str(detail)}


def _validation_failure(errors) -> object:
    flattened = _flatten_errors(errors)
    message = first_error_message(errors) or "محتوای صفحه معتبر نیست"
    return fail(message, 422, data={"fieldErrors": flattened})


class AdminStaticPageListView(ShopAdminRequiredMixin, APIView):
    @extend_schema(
        operation_id="admin_content_static_pages_list",
        responses={
            200: AdminStaticPageListEnvelopeSerializer,
            403: StaticPageErrorEnvelopeSerializer,
        },
    )
    def get(self, request):
        resolved = page_contents(SUPPORTED_PAGE_KEYS)
        return ok(
            {
                "pages": [
                    page_summary_dto(key, resolved[key])
                    for key in SUPPORTED_PAGE_KEYS
                ]
            }
        )


class AdminStaticPageDetailView(ShopAdminRequiredMixin, APIView):
    def _definition_exists(self, key: str) -> bool:
        return get_page_definition(key) is not None

    @extend_schema(
        operation_id="admin_content_static_pages_retrieve",
        responses={
            200: AdminStaticPageDetailEnvelopeSerializer,
            403: StaticPageErrorEnvelopeSerializer,
            404: StaticPageErrorEnvelopeSerializer,
        },
    )
    def get(self, request, key: str):
        if not self._definition_exists(key):
            return fail("صفحه محتوایی یافت نشد", 404)
        resolved = page_content(key)
        return ok({"page": admin_page_dto(key, resolved)})

    @extend_schema(
        operation_id="admin_content_static_pages_update",
        request=StaticPagePatchSerializer,
        responses={
            200: AdminStaticPageDetailEnvelopeSerializer,
            403: StaticPageErrorEnvelopeSerializer,
            404: StaticPageErrorEnvelopeSerializer,
            422: StaticPageErrorEnvelopeSerializer,
        },
    )
    def patch(self, request, key: str):
        if not self._definition_exists(key):
            return fail("صفحه محتوایی یافت نشد", 404)

        serializer = StaticPagePatchSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_failure(serializer.errors)

        changes = dict(serializer.validated_data)
        if "isVisible" in changes:
            changes["is_visible"] = changes.pop("isVisible")
        try:
            update_page(
                key=key,
                user=request.user,
                **changes,
            )
        except PageContentValidationError as exc:
            return _validation_failure(exc.errors)

        resolved = page_content(key)
        return ok({"page": admin_page_dto(key, resolved)})
