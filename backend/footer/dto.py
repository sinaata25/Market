"""تبدیل مدل‌های فوتر به ساختار پاسخ API (camelCase)"""

from __future__ import annotations

from datetime import date

from .models import FooterItem, FooterSection, FooterSettings
from .selectors import section_items
from .services import resolved_brand_title, resolved_copyright
from .validation import is_external_url, phone_href


def _item_href(item: FooterItem) -> str | None:
    """مقصد قابل کلیک این آیتم — شماره و ایمیل مقصدشان را خودشان می‌سازند"""
    if item.item_type == FooterItem.ItemType.PHONE:
        return phone_href(item.text) or None
    if item.item_type == FooterItem.ItemType.EMAIL:
        return f"mailto:{item.text.strip()}" if item.text.strip() else None
    return item.url or None


def item_dto(item: FooterItem) -> dict:
    href = _item_href(item)
    return {
        "id": item.id,
        "type": item.item_type,
        "label": item.label or None,
        "text": item.text or None,
        "url": href,
        "image": item.image.url if item.image else None,
        "icon": item.icon or None,
        "openInNewTab": item.open_in_new_tab,
        # از روی خود نشانی مشتق می‌شود تا برچسب و مقصد هرگز ناهمخوان نشوند
        "isExternal": bool(href) and is_external_url(href),
        "position": item.position,
    }


def admin_item_dto(item: FooterItem) -> dict:
    return {
        **item_dto(item),
        "sectionId": item.section_id,
        # مقدار خام ورودی مدیر، نه مقصد ساخته‌شده
        "rawUrl": item.url or None,
        "isActive": item.is_active,
        "staticPageKey": item.static_page_key or None,
        "createdAt": item.created_at,
        "updatedAt": item.updated_at,
    }


def public_section_dto(section: FooterSection, items: list[FooterItem]) -> dict:
    return {
        "id": section.id,
        "title": section.title or None,
        "variant": section.variant,
        "description": section.description or None,
        "position": section.position,
        "items": [item_dto(item) for item in items],
    }


def admin_section_dto(section: FooterSection) -> dict:
    return {
        "id": section.id,
        "title": section.title or None,
        "variant": section.variant,
        "description": section.description or None,
        "position": section.position,
        "isActive": section.is_active,
        "items": [admin_item_dto(item) for item in section_items(section)],
        "createdAt": section.created_at,
        "updatedAt": section.updated_at,
    }


def settings_dto(settings_row: FooterSettings, *, year: int | None = None) -> dict:
    return {
        "brandTitle": resolved_brand_title(settings_row) or None,
        "logo": settings_row.logo.url if settings_row.logo else None,
        "description": settings_row.description or None,
        "copyright": resolved_copyright(
            settings_row, year=year or date.today().year
        )
        or None,
        "address": settings_row.address or None,
        "phone": settings_row.phone or None,
        "phoneUrl": phone_href(settings_row.phone) or None,
        "email": settings_row.email or None,
        "emailUrl": f"mailto:{settings_row.email}" if settings_row.email else None,
    }


def admin_settings_dto(settings_row: FooterSettings) -> dict:
    return {
        **settings_dto(settings_row),
        # مقدار ذخیره‌شده، بدون جایگزینی {year} و بدون پُرکردن از تنظیمات سئو
        "storedBrandTitle": settings_row.brand_title or None,
        "storedCopyright": settings_row.copyright_text or None,
        "updatedAt": settings_row.updated_at,
    }
