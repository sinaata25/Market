"""تبدیل مدل‌های فوتر به ساختار پاسخ API (camelCase)"""

from __future__ import annotations

from datetime import date

from .models import FooterIcon, FooterItem, FooterSection, FooterSettings
from .maps import format_coordinate
from .selectors import section_items
from .services import (
    resolved_brand_title,
    resolved_copyright,
    shop_coordinates,
    shop_directions_url,
    shop_map_is_visible,
    shop_maps_url,
)
from .validation import is_external_url, phone_href


def icon_url(icon: FooterIcon | None) -> str | None:
    return icon.image.url if icon and icon.image else None


def icon_dto(icon: FooterIcon) -> dict:
    return {"id": icon.id, "name": icon.name, "image": icon_url(icon)}


def admin_icon_dto(icon: FooterIcon) -> dict:
    data = icon_dto(icon)
    count = getattr(icon, "item_count", None)
    data["usageCount"] = icon.items.count() if count is None else count
    return data


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
        # آیکن تصویری اصل است؛ ایموجی فقط وقتی آیکنی انتخاب نشده باشد
        "iconImage": icon_url(item.icon_image),
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
        "iconId": item.icon_image_id,
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


def public_location_dto(settings_row: FooterSettings) -> dict | None:
    """موقعیت فروشگاه برای فوتر، یا None وقتی نباید نمایش داده شود"""
    if not shop_map_is_visible(settings_row):
        return None
    latitude, longitude = shop_coordinates(settings_row)
    return {
        "address": settings_row.address or None,
        "icon": icon_url(settings_row.address_icon),
        "latitude": format_coordinate(latitude),
        "longitude": format_coordinate(longitude),
        "zoom": settings_row.map_zoom,
        "mapsUrl": shop_maps_url(settings_row),
        "directionsUrl": shop_directions_url(settings_row),
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
        "addressIcon": icon_url(settings_row.address_icon),
        "phone": settings_row.phone or None,
        "phoneUrl": phone_href(settings_row.phone) or None,
        "phoneIcon": icon_url(settings_row.phone_icon),
        "email": settings_row.email or None,
        "emailUrl": f"mailto:{settings_row.email}" if settings_row.email else None,
        "emailIcon": icon_url(settings_row.email_icon),
        "location": public_location_dto(settings_row),
    }


def admin_settings_dto(settings_row: FooterSettings) -> dict:
    return {
        **settings_dto(settings_row),
        # مقدار ذخیره‌شده، بدون جایگزینی {year} و بدون پُرکردن از تنظیمات سئو
        "storedBrandTitle": settings_row.brand_title or None,
        "storedCopyright": settings_row.copyright_text or None,
        # مختصات خام برای نقشه‌ی انتخابگر — بدون وابستگی به showMap
        "latitude": (
            format_coordinate(settings_row.latitude)
            if settings_row.latitude is not None
            else None
        ),
        "longitude": (
            format_coordinate(settings_row.longitude)
            if settings_row.longitude is not None
            else None
        ),
        "addressIconId": settings_row.address_icon_id,
        "phoneIconId": settings_row.phone_icon_id,
        "emailIconId": settings_row.email_icon_id,
        "showMap": settings_row.show_map,
        "mapZoom": settings_row.map_zoom,
        "mapsPlaceUrl": settings_row.maps_place_url or None,
        "mapsUrl": shop_maps_url(settings_row) or None,
        "directionsUrl": shop_directions_url(settings_row) or None,
        "updatedAt": settings_row.updated_at,
    }
