from __future__ import annotations

from django.db.models import Count, QuerySet

from .models import Banner, HomepageSection


def sections_queryset(*, active_only: bool) -> QuerySet[HomepageSection]:
    qs = HomepageSection.objects.select_related(
        "banner", "category", "brand"
    ).order_by("position", "id")
    if active_only:
        qs = qs.filter(is_active=True)
    return qs


def banners_queryset() -> QuerySet[Banner]:
    return Banner.objects.annotate(section_count=Count("sections")).order_by(
        "-created_at", "-id"
    )
