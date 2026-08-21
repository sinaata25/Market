from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from common.responses import ok

from .dto import public_section_dto
from .selectors import sections_queryset


class PublicHomepageSectionListView(APIView):
    """بخش‌های فعال صفحه اصلی، به ترتیب تعیین‌شده توسط مدیر"""

    authentication_classes: list = []

    @extend_schema(
        operation_id="home_sections_list", responses={200: OpenApiTypes.OBJECT}
    )
    def get(self, request):
        sections = sections_queryset(active_only=True)
        resolved = [public_section_dto(section) for section in sections]
        # بخش‌هایی که مرجع لازم‌شان (مثلاً بنر) حذف شده، حذف می‌شوند نه خراب‌شدن صفحه
        return ok({"sections": [section for section in resolved if section is not None]})
