from __future__ import annotations

from django.db.models import Prefetch, QuerySet

from .models import FooterItem, FooterSection


def items_queryset(*, active_only: bool) -> QuerySet[FooterItem]:
    qs = FooterItem.objects.order_by("position", "id")
    return qs.filter(is_active=True) if active_only else qs


def sections_queryset(*, active_only: bool) -> QuerySet[FooterSection]:
    """بخش‌های فوتر به‌همراه محتواهایشان — یک کوئری برای بخش‌ها و یکی برای آیتم‌ها"""
    qs = FooterSection.objects.order_by("position", "id").prefetch_related(
        Prefetch(
            "items",
            queryset=items_queryset(active_only=active_only),
            to_attr="ordered_items",
        )
    )
    return qs.filter(is_active=True) if active_only else qs


def section_items(section: FooterSection) -> list[FooterItem]:
    """آیتم‌های از پیش prefetch‌شده؛ در نبودشان یک کوئری تازه"""
    prefetched = getattr(section, "ordered_items", None)
    if prefetched is not None:
        return list(prefetched)
    return list(section.items.order_by("position", "id"))
