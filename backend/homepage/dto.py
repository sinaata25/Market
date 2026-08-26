"""تبدیل مدل‌های صفحه اصلی به ساختار پاسخ API (camelCase)"""

from __future__ import annotations

from catalog.category_tree import visible_category_ids
from catalog.dto import brand_dto, category_dto, category_summary, product_dto
from catalog.models import Brand, Category

from .models import Banner, HomepageSection
from .services import (
    PRODUCT_SECTION_FILTERS,
    resolved_limit,
    resolved_title,
    section_products,
    section_products_total,
)


def banner_dto(banner: Banner) -> dict:
    return {
        "id": banner.id,
        "title": banner.title or None,
        "subtitle": banner.subtitle or None,
        "image": banner.image.url if banner.image else None,
        "theme": banner.theme,
        "linkUrl": banner.link_url or None,
        "linkLabel": banner.link_label or None,
        "isActive": banner.is_active,
    }


def admin_banner_dto(banner: Banner) -> dict:
    data = banner_dto(banner)
    data["sectionCount"] = getattr(banner, "section_count", None)
    if data["sectionCount"] is None:
        data["sectionCount"] = banner.sections.count()
    return data


def _root_categories(
    *, limit: int | None, visible_ids: set[int]
) -> list[Category]:
    categories = [
        category
        for category in Category.objects.filter(
            id__in=visible_ids
        ).prefetch_related("parents", "children")
        if not category.parents.exists()
    ]
    return categories[:limit] if limit else categories


def _active_brands(*, limit: int | None) -> list[Brand]:
    brands = list(Brand.objects.filter(is_active=True))
    return brands[:limit] if limit else brands


def public_section_dto(section: HomepageSection) -> dict | None:
    """داده‌ی این بخش برای فروشگاه — اگر مرجع لازم آن حذف شده باشد None برمی‌گرداند"""
    section_type = section.section_type
    title = resolved_title(section) or None

    if section_type == HomepageSection.SectionType.BANNER:
        if section.banner_id is None or not section.banner.is_active:
            return None
        return {
            "id": section.id,
            "type": section_type,
            "position": section.position,
            "title": title,
            "limit": resolved_limit(section),
            "data": {"banner": banner_dto(section.banner)},
        }

    if section_type == HomepageSection.SectionType.CATEGORIES:
        visible_ids = visible_category_ids()
        categories = _root_categories(
            limit=resolved_limit(section), visible_ids=visible_ids
        )
        return {
            "id": section.id,
            "type": section_type,
            "position": section.position,
            "title": title,
            "limit": resolved_limit(section),
            "data": {
                "categories": [
                    category_dto(category, visible_ids=visible_ids)
                    for category in categories
                ]
            },
        }

    if section_type == HomepageSection.SectionType.BRANDS:
        brands = _active_brands(limit=resolved_limit(section))
        return {
            "id": section.id,
            "type": section_type,
            "position": section.position,
            "title": title,
            "limit": resolved_limit(section),
            "data": {"brands": [brand_dto(brand) for brand in brands]},
        }

    if section_type == HomepageSection.SectionType.RECENTLY_VIEWED:
        return {
            "id": section.id,
            "type": section_type,
            "position": section.position,
            "title": title,
            "limit": resolved_limit(section),
            # Visitor-specific data is intentionally loaded from local history.
            "data": {},
        }

    # از خودِ پیکربندی فیلترها گرفته می‌شود تا افزودن نوع بخش محصولی جدید،
    # یک‌جا انجام شود و بخش تازه بی‌سروصدا از پاسخ عمومی حذف نشود
    product_types = set(PRODUCT_SECTION_FILTERS) | {
        HomepageSection.SectionType.PRODUCT_COLLECTION
    }
    if section_type not in product_types:
        return None

    # بخش‌های محصولی: پرفروش‌ترین‌ها، شگفت‌انگیزها، تخفیف‌دارها، جدیدترین‌ها،
    # همه محصولات، مجموعه سفارشی
    products = section_products(section)
    data = {"products": [product_dto(product) for product in products]}

    # بخش «همه محصولات» صفحه‌بندی می‌شود: فروشگاه برای ساختن صفحه‌بندی به
    # تعداد کل نیاز دارد و بقیه‌ی صفحه‌ها را از API عمومی محصولات می‌گیرد.
    if section_type == HomepageSection.SectionType.ALL_PRODUCTS:
        data["total"] = section_products_total(section)

    return {
        "id": section.id,
        "type": section_type,
        "position": section.position,
        "title": title,
        "limit": resolved_limit(section),
        "data": data,
    }


def admin_section_dto(section: HomepageSection) -> dict:
    return {
        "id": section.id,
        "sectionType": section.section_type,
        "title": section.title or None,
        "resolvedTitle": resolved_title(section) or None,
        "position": section.position,
        "isActive": section.is_active,
        "banner": banner_dto(section.banner) if section.banner_id else None,
        "category": category_summary(section.category) if section.category_id else None,
        "brand": brand_dto(section.brand) if section.brand_id else None,
        "sort": section.sort or None,
        "limit": section.limit,
        "resolvedLimit": resolved_limit(section),
        "createdAt": section.created_at,
        "updatedAt": section.updated_at,
    }
