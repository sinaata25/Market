from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max

from catalog.models import Product
from catalog.selectors import filtered_products_queryset

from .models import Banner, HomepageSection
from .selectors import sections_queryset


class HomepageValidationError(Exception):
    """اعتبارسنجی مدل شکست خورد — errors نگاشت فیلد به پیام است"""

    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        super().__init__(next(iter(errors.values()), "پیکربندی معتبر نیست"))


def _flatten(exc: ValidationError) -> dict[str, str]:
    detail = getattr(exc, "message_dict", None)
    if detail is None:
        return {"request": exc.messages[0] if exc.messages else "پیکربندی معتبر نیست"}
    return {
        field: messages[0] if isinstance(messages, list) else str(messages)
        for field, messages in detail.items()
    }


def _save(instance) -> None:
    try:
        instance.save()
    except ValidationError as exc:
        raise HomepageValidationError(_flatten(exc)) from exc

DEFAULT_TITLES: dict[str, str] = {
    HomepageSection.SectionType.CATEGORIES: "دسته‌بندی‌ها",
    HomepageSection.SectionType.BRANDS: "برندهای ما",
    HomepageSection.SectionType.BEST_SELLERS: "پرفروش‌ترین‌ها",
    HomepageSection.SectionType.DISCOUNTED_PRODUCTS: "تخفیف‌های ویژه",
    HomepageSection.SectionType.NEW_PRODUCTS: "جدیدترین محصولات",
    HomepageSection.SectionType.PRODUCT_COLLECTION: "منتخب فروشگاه",
}

DEFAULT_LIMITS: dict[str, int] = {
    HomepageSection.SectionType.CATEGORIES: 8,
    HomepageSection.SectionType.BRANDS: 12,
    HomepageSection.SectionType.BEST_SELLERS: 8,
    HomepageSection.SectionType.DISCOUNTED_PRODUCTS: 6,
    HomepageSection.SectionType.NEW_PRODUCTS: 8,
    HomepageSection.SectionType.PRODUCT_COLLECTION: 8,
}

# نوع بخش‌هایی که داده‌شان یک فهرست محصول است — پارامترهای انتخاب محصول هرکدام
PRODUCT_SECTION_FILTERS = {
    HomepageSection.SectionType.BEST_SELLERS: {"best_seller": True, "sort": "featured"},
    HomepageSection.SectionType.DISCOUNTED_PRODUCTS: {"discounted": True, "sort": "newest"},
    HomepageSection.SectionType.NEW_PRODUCTS: {"sort": "newest"},
}


def resolved_title(section: HomepageSection) -> str:
    return section.title or DEFAULT_TITLES.get(section.section_type, "")


def resolved_limit(section: HomepageSection) -> int:
    return section.limit or DEFAULT_LIMITS.get(section.section_type, 8)


def section_products(section: HomepageSection) -> list[Product]:
    """محصولات این بخش را برمی‌گرداند — منطق فیلتر از catalog.selectors است."""
    limit = resolved_limit(section)
    section_type = section.section_type

    if section_type == HomepageSection.SectionType.PRODUCT_COLLECTION:
        qs = filtered_products_queryset(
            category_slug=section.category.slug if section.category_id else None,
            brand_slug=section.brand.slug if section.brand_id else None,
            sort=section.sort or "newest",
        )
        return list(qs[:limit])

    filters = PRODUCT_SECTION_FILTERS.get(section_type)
    if filters is None:
        return []
    qs = filtered_products_queryset(**filters)
    return list(qs[:limit])


@transaction.atomic
def _renumber(sections: list[HomepageSection]) -> None:
    for index, section in enumerate(sections):
        if section.position != index:
            section.position = index
    HomepageSection.objects.bulk_update(sections, ["position"])


@transaction.atomic
def create_section(
    *,
    section_type: str,
    title: str = "",
    is_active: bool = True,
    banner: Banner | None = None,
    category=None,
    brand=None,
    sort: str = "",
    limit: int | None = None,
) -> HomepageSection:
    last_position = HomepageSection.objects.aggregate(value=Max("position"))["value"]
    position = 0 if last_position is None else last_position + 1
    section = HomepageSection(
        section_type=section_type,
        title=title,
        is_active=is_active,
        banner=banner,
        category=category,
        brand=brand,
        sort=sort,
        limit=limit,
        position=position,
    )
    _save(section)
    return section


@transaction.atomic
def update_section(section: HomepageSection, **fields) -> HomepageSection:
    for field_name, value in fields.items():
        setattr(section, field_name, value)
    _save(section)
    return section


@transaction.atomic
def delete_section(section: HomepageSection) -> None:
    section.delete()
    remaining = list(sections_queryset(active_only=False).select_for_update())
    _renumber(remaining)


@transaction.atomic
def move_section(section: HomepageSection, direction: str) -> list[HomepageSection]:
    """جابه‌جایی یک‌پله بخش به بالا/پایین و بازشماری کامل ترتیب‌ها"""
    sections = list(sections_queryset(active_only=False).select_for_update())
    index = next(i for i, s in enumerate(sections) if s.pk == section.pk)

    if direction == "up" and index > 0:
        sections[index - 1], sections[index] = sections[index], sections[index - 1]
    elif direction == "down" and index < len(sections) - 1:
        sections[index + 1], sections[index] = sections[index], sections[index + 1]

    _renumber(sections)
    return sections


@transaction.atomic
def create_banner(**fields) -> Banner:
    banner = Banner(**fields)
    _save(banner)
    return banner


@transaction.atomic
def update_banner(banner: Banner, **fields) -> Banner:
    for field_name, value in fields.items():
        setattr(banner, field_name, value)
    _save(banner)
    return banner
