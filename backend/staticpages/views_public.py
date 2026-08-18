from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView

from common.responses import fail, ok

from .definitions import SUPPORTED_PAGE_KEYS, get_page_definition
from .dto import public_page_dto
from .serializers import (
    PublicStaticPageDetailEnvelopeSerializer,
    PublicStaticPageListEnvelopeSerializer,
    StaticPageErrorEnvelopeSerializer,
)
from .services import page_content, page_contents


def _requested_keys(raw_keys: str | None) -> tuple[str, ...] | None:
    if raw_keys is None:
        return SUPPORTED_PAGE_KEYS
    if len(raw_keys) > 500:
        return None

    parts = [part.strip() for part in raw_keys.split(",")]
    if not parts or any(not part for part in parts):
        return None

    keys = tuple(dict.fromkeys(parts))
    if any(get_page_definition(key) is None for key in keys):
        return None
    return keys


class PublicStaticPageListView(APIView):
    authentication_classes: list = []

    @extend_schema(
        operation_id="content_static_pages_list",
        parameters=[
            OpenApiParameter(
                "keys",
                str,
                description="Comma-separated supported page keys; omitted returns all.",
            )
        ],
        responses={
            200: PublicStaticPageListEnvelopeSerializer,
            422: StaticPageErrorEnvelopeSerializer,
        },
    )
    def get(self, request):
        keys = _requested_keys(request.query_params.get("keys"))
        if keys is None:
            return fail("شناسه یک یا چند صفحه نامعتبر است", 422)

        resolved = page_contents(keys)
        pages = [
            public_page_dto(key, resolved[key][0])
            for key in keys
        ]
        return ok({"pages": pages})


class PublicStaticPageDetailView(APIView):
    authentication_classes: list = []

    @extend_schema(
        operation_id="content_static_pages_retrieve",
        responses={
            200: PublicStaticPageDetailEnvelopeSerializer,
            404: StaticPageErrorEnvelopeSerializer,
        },
    )
    def get(self, request, key: str):
        if get_page_definition(key) is None:
            return fail("صفحه محتوایی یافت نشد", 404)
        content, _page = page_content(key)
        return ok({"page": public_page_dto(key, content)})
