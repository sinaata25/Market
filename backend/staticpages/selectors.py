from __future__ import annotations

from collections.abc import Iterable

from .models import StaticPage


def static_pages_by_key(keys: Iterable[str]) -> dict[str, StaticPage]:
    return {
        page.key: page
        for page in StaticPage.objects.filter(key__in=keys).select_related(
            "updated_by"
        )
    }
