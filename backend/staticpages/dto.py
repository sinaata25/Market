from __future__ import annotations

from typing import Any

from .definitions import (
    field_value,
    fields_for_page,
    get_page_definition,
    sections_for_page,
)
from .services import ResolvedStaticPage


def _editor_name(resolved: ResolvedStaticPage) -> str | None:
    page = resolved.page
    if page is None or page.updated_by is None:
        return None
    return page.updated_by.name or page.updated_by.phone


def page_summary_dto(
    key: str, resolved: ResolvedStaticPage
) -> dict[str, Any]:
    definition = get_page_definition(key)
    if definition is None:
        raise KeyError(key)
    return {
        "key": definition.key,
        "label": definition.label,
        "path": definition.path,
        "isVisible": resolved.is_visible,
        "updatedAt": (
            resolved.page.updated_at.isoformat() if resolved.page else None
        ),
        "updatedBy": _editor_name(resolved),
    }


def public_page_dto(
    key: str, resolved: ResolvedStaticPage
) -> dict[str, Any]:
    return {
        "key": key,
        "isVisible": resolved.is_visible,
        "sections": resolved.section_visibility,
        "content": resolved.content,
    }


def _field_dto(field, content: dict[str, Any]) -> dict[str, Any]:
    data = {
        "id": field.id,
        "label": field.label,
        "group": field.group,
        "control": field.control,
        "required": field.required,
        "maxLength": field.max_length,
        "value": field_value(content, field),
    }
    if field.rows is not None:
        data["rows"] = field.rows
    if field.direction is not None:
        data["dir"] = field.direction
    if field.help_text is not None:
        data["help"] = field.help_text
    return data


def admin_page_dto(
    key: str, resolved: ResolvedStaticPage
) -> dict[str, Any]:
    return {
        **page_summary_dto(key, resolved),
        "sections": [
            {
                "id": section.id,
                "label": section.label,
                "visible": resolved.section_visibility[section.id],
            }
            for section in sections_for_page(key)
        ],
        "fields": [
            _field_dto(field, resolved.content) for field in fields_for_page(key)
        ],
    }
