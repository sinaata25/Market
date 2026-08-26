from django.utils.cache import patch_cache_control
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from common.responses import fail, ok

from .registry import UnknownProvince, get_province_by_id, get_registry


def _cache(response):
    patch_cache_control(response, public=True, max_age=86_400)
    return response


class ProvinceListView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        registry = get_registry()
        return _cache(
            ok(
                {
                    "version": str(registry.year),
                    "provinces": [
                        {"id": province.id, "name": province.name}
                        for province in registry.provinces
                    ],
                }
            )
        )


class ProvinceCityListView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request, province_id: str):
        try:
            province = get_province_by_id(province_id)
        except UnknownProvince:
            return fail("استان یافت نشد", 404)

        return _cache(
            ok(
                {
                    "province": {"id": province.id, "name": province.name},
                    "cities": [
                        {
                            "id": city.id,
                            "name": city.name,
                            "countyName": city.county_name,
                        }
                        for city in province.cities
                    ],
                }
            )
        )
