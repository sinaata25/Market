from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from .definitions import (
    PAGE_DEFINITIONS,
    default_content,
    default_section_visibility,
    fields_for_page,
)
from .models import StaticPage
from .validation import content_errors, visibility_errors


class PageContentValidationError(Exception):
    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        super().__init__(next(iter(errors.values()), "محتوای صفحه معتبر نیست"))


@dataclass(frozen=True)
class ResolvedStaticPage:
    content: dict[str, Any]
    is_visible: bool
    section_visibility: dict[str, bool]
    page: StaticPage | None


def _safe_stored_content(key: str, page: StaticPage | None) -> dict[str, Any]:
    if page is None or content_errors(key, page.content):
        return default_content(key)
    return deepcopy(page.content)


def _safe_stored_visibility(
    key: str, page: StaticPage | None
) -> tuple[bool, dict[str, bool]]:
    if page is None:
        return True, default_section_visibility(key)
    errors = visibility_errors(key, page.is_visible, page.section_visibility)
    is_visible = True if "isVisible" in errors else page.is_visible
    section_errors = any(error != "isVisible" for error in errors)
    sections = (
        default_section_visibility(key)
        if section_errors
        else deepcopy(page.section_visibility)
    )
    return is_visible, sections


def page_contents(
    keys: Iterable[str],
) -> dict[str, ResolvedStaticPage]:
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
    resolved: dict[str, ResolvedStaticPage] = {}
    for key in unique_keys:
        page = stored.get(key)
        is_visible, section_visibility = _safe_stored_visibility(key, page)
        resolved[key] = ResolvedStaticPage(
            content=_safe_stored_content(key, page),
            is_visible=is_visible,
            section_visibility=section_visibility,
            page=page,
        )
    return resolved


def page_content(key: str) -> ResolvedStaticPage:
    return page_contents((key,))[key]


def page_visibilities(keys: Iterable[str]) -> dict[str, bool]:
    """Return page visibility without selecting the large content JSON."""
    unique_keys = tuple(dict.fromkeys(keys))
    unsupported = next(
        (key for key in unique_keys if key not in PAGE_DEFINITIONS), None
    )
    if unsupported is not None:
        raise KeyError(unsupported)

    stored = dict(
        StaticPage.objects.filter(key__in=unique_keys).values_list(
            "key", "is_visible"
        )
    )
    return {
        key: stored[key] if type(stored.get(key)) is bool else True
        for key in unique_keys
    }


def _set_value(content: dict[str, Any], path: tuple[str | int, ...], value: str):
    current: Any = content
    for part in path[:-1]:
        current = current[part]
    current[path[-1]] = value


_UNSET = object()


@transaction.atomic
def update_page(
    *,
    key: str,
    user,
    fields: dict[str, Any] | None = None,
    is_visible: Any = _UNSET,
    sections: dict[str, Any] | None = None,
) -> StaticPage:
    if key not in PAGE_DEFINITIONS:
        raise KeyError(key)
    if fields is None and is_visible is _UNSET and sections is None:
        raise PageContentValidationError(
            {"request": "حداقل یک تغییر لازم است"}
        )

    definitions = {field.id: field for field in fields_for_page(key)}
    fields = fields or {}
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
    current_is_visible, section_visibility = _safe_stored_visibility(key, page)

    for field_id, raw_value in fields.items():
        if not isinstance(raw_value, str):
            raise PageContentValidationError({field_id: "مقدار باید متن باشد"})
        _set_value(content, definitions[field_id].path, raw_value.strip())

    if is_visible is not _UNSET:
        if type(is_visible) is not bool:
            raise PageContentValidationError(
                {"isVisible": "وضعیت نمایش صفحه باید درست یا نادرست باشد"}
            )
        current_is_visible = is_visible

    allowed_sections = default_section_visibility(key)
    for section_id, visible in (sections or {}).items():
        if section_id not in allowed_sections:
            raise PageContentValidationError(
                {f"sections.{section_id}": "این بخش برای صفحه تعریف نشده است"}
            )
        if type(visible) is not bool:
            raise PageContentValidationError(
                {
                    f"sections.{section_id}": (
                        "وضعیت نمایش بخش باید درست یا نادرست باشد"
                    )
                }
            )
        section_visibility[section_id] = visible

    errors = content_errors(key, content)
    if errors:
        raise PageContentValidationError(errors)

    if page is None:
        page = StaticPage(key=key)
    page.content = content
    page.is_visible = current_is_visible
    page.section_visibility = section_visibility
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
