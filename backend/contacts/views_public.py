from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from common.responses import ok
from .dto import button_dto
from .selectors import buttons_queryset


class PublicFloatingContactButtonsView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return ok({"buttons": [button_dto(button) for button in buttons_queryset(active_only=True)]})
