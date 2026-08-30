from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from common.responses import ok
from staticpages.services import page_visibilities

from .dto import public_section_dto, settings_dto
from .models import FooterSettings
from .selectors import section_items, sections_queryset


class PublicFooterView(APIView):
    """کل فوتر در یک درخواست: تنظیمات سراسری + بخش‌ها و محتواهای فعال

    فوتر روی تقریباً همه‌ی صفحه‌ها رندر می‌شود؛ شکستن آن به چند endpoint
    یعنی چند رفت‌وبرگشت اضافه در هر ناوبری.
    """

    authentication_classes: list = []

    @extend_schema(operation_id="footer_retrieve", responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        sections = [
            (section, section_items(section))
            for section in sections_queryset(active_only=True)
        ]

        # فقط اگر پیوندی به صفحه‌ی محتوایی وصل باشد، وضعیت نمایش آن‌ها خوانده می‌شود
        referenced_keys = {
            item.static_page_key
            for _, items in sections
            for item in items
            if item.static_page_key
        }
        visibility = page_visibilities(referenced_keys) if referenced_keys else {}

        payload = []
        for section, items in sections:
            visible_items = [
                item
                for item in items
                # پیوند به صفحه‌ای که مدیر پنهانش کرده نباید در فوتر بماند
                if not item.static_page_key
                or visibility.get(item.static_page_key, True)
            ]
            # بخش بی‌محتوا فقط یک عنوان خالی در فوتر می‌شود
            if visible_items:
                payload.append(public_section_dto(section, visible_items))

        return ok(
            {
                "settings": settings_dto(FooterSettings.current()),
                "sections": payload,
            }
        )
