from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from .definitions import (
    PAGE_DEFINITIONS,
    default_content,
    fields_for_page,
)
from .models import StaticPage
from .validation import content_errors


class PageContentValidationError(Exception):
    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        super().__init__(next(iter(errors.values()), "محتوای صفحه معتبر نیست"))


def _safe_stored_content(key: str, page: StaticPage | None) -> dict[str, Any]:
    if page is None or content_errors(key, page.content):
        return default_content(key)
    return deepcopy(page.content)


def page_contents(
    keys: Iterable[str],
) -> dict[str, tuple[dict[str, Any], StaticPage | None]]:
    unique_keys = tuple(dict.fromkeys(keys))
    unsupported = next(
        (key for key in unique_keys if key not in PAGE_DEFINITIONS), None
    )
    if unsupported is not None:
        raise KeyError(unsupported)

    stored = {
        page.key: page
        for page in StaticPage.objects.filter(key__in=unique_keys).select_related(
            "updated_by"
        )
    }
    return {
        key: (_safe_stored_content(key, stored.get(key)), stored.get(key))
        for key in unique_keys
    }


def page_content(key: str) -> tuple[dict[str, Any], StaticPage | None]:
    return page_contents((key,))[key]


def _set_value(content: dict[str, Any], path: tuple[str | int, ...], value: str):
    current: Any = content
    for part in path[:-1]:
        current = current[part]
    current[path[-1]] = value


@transaction.atomic
def update_page_fields(*, key: str, fields: dict[str, Any], user) -> StaticPage:
    if key not in PAGE_DEFINITIONS:
        raise KeyError(key)
    if not fields:
        raise PageContentValidationError({"fields": "حداقل یک فیلد لازم است"})

    definitions = {field.id: field for field in fields_for_page(key)}
    unknown = set(fields) - set(definitions)
    if unknown:
        field_id = sorted(unknown)[0]
        raise PageContentValidationError(
            {field_id: "این فیلد برای صفحه قابل ویرایش نیست"}
        )

    page = (
        StaticPage.objects.select_for_update()
        .filter(key=key)
        .select_related("updated_by")
        .first()
    )
    content = _safe_stored_content(key, page)

    for field_id, raw_value in fields.items():
        if not isinstance(raw_value, str):
            raise PageContentValidationError({field_id: "مقدار باید متن باشد"})
        _set_value(content, definitions[field_id].path, raw_value.strip())

    errors = content_errors(key, content)
    if errors:
        raise PageContentValidationError(errors)

    if page is None:
        page = StaticPage(key=key)
    page.content = content
    page.updated_by = user
    try:
        page.save()
    except ValidationError as exc:
        detail = getattr(exc, "message_dict", {"content": exc.messages[0]})
        flattened = {
            field: messages[0] if isinstance(messages, list) else str(messages)
            for field, messages in detail.items()
        }
        raise PageContentValidationError(flattened) from exc
    return page
