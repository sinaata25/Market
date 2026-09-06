from .models import FloatingContactButton


def buttons_queryset(*, active_only=False):
    qs = FloatingContactButton.objects.select_related("library_icon").order_by("display_order", "id")
    return qs.filter(is_active=True) if active_only else qs
