from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max

from catalog.models import Product
from catalog.selectors import filtered_products_queryset

from .models import Banner, HomepageSection, allowed_fields
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
    HomepageSection.SectionType.INCREDIBLE_PRODUCTS: "شگفت‌انگیزها",
    HomepageSection.SectionType.DISCOUNTED_PRODUCTS: "همه تخفیف‌ها",
    HomepageSection.SectionType.NEW_PRODUCTS: "جدیدترین محصولات",
    HomepageSection.SectionType.ALL_PRODUCTS: "همه محصولات",
    HomepageSection.SectionType.PRODUCT_COLLECTION: "منتخب فروشگاه",
    HomepageSection.SectionType.RECENTLY_VIEWED: "محصولات اخیراً مشاهده‌شده",
}

DEFAULT_LIMITS: dict[str, int] = {
    HomepageSection.SectionType.CATEGORIES: 8,
    HomepageSection.SectionType.BRANDS: 12,
    HomepageSection.SectionType.BEST_SELLERS: 8,
    HomepageSection.SectionType.INCREDIBLE_PRODUCTS: 6,
    HomepageSection.SectionType.DISCOUNTED_PRODUCTS: 6,
    HomepageSection.SectionType.NEW_PRODUCTS: 8,
    # این بخش صفحه‌بندی می‌شود؛ عدد یعنی تعداد کالای هر صفحه
    HomepageSection.SectionType.ALL_PRODUCTS: 6,
    HomepageSection.SectionType.PRODUCT_COLLECTION: 8,
    # ردیف برند/دسته‌بندی: پیش‌فرض ۶ کالا
    HomepageSection.SectionType.BRAND_PRODUCTS: 6,
    HomepageSection.SectionType.CATEGORY_PRODUCTS: 6,
    HomepageSection.SectionType.RECENTLY_VIEWED: 10,
}

# نوع بخش‌هایی که داده‌شان یک فهرست محصول است — پارامترهای انتخاب محصول هرکدام
PRODUCT_SECTION_FILTERS = {
    HomepageSection.SectionType.BEST_SELLERS: {"best_seller": True, "sort": "featured"},
    # شگفت‌انگیزها انتخاب دستی مدیر است، نه هر محصول تخفیف‌دار
    HomepageSection.SectionType.INCREDIBLE_PRODUCTS: {
        "incredible": True,
        "sort": "incredible",
    },
    HomepageSection.SectionType.DISCOUNTED_PRODUCTS: {"discounted": True, "sort": "newest"},
    HomepageSection.SectionType.NEW_PRODUCTS: {"sort": "newest"},
    # بدون هیچ فیلتری: کل کاتالوگ، همان چیزی که صفحه‌ی /products نشان می‌دهد
    HomepageSection.SectionType.ALL_PRODUCTS: {"sort": "newest"},
}


# هر نوع بخشی که داده‌اش فهرست محصول است — مرجع واحد برای DTO عمومی، تا نوع
# تازه بی‌سروصدا از پاسخ فروشگاه حذف نشود
PRODUCT_SECTION_TYPES = set(PRODUCT_SECTION_FILTERS) | {
    HomepageSection.SectionType.PRODUCT_COLLECTION,
    HomepageSection.SectionType.BRAND_PRODUCTS,
    HomepageSection.SectionType.CATEGORY_PRODUCTS,
}


def resolved_title(section: HomepageSection) -> str:
    """عنوان نمایشی بخش — عنوان سفارشی مدیر، وگرنه پیش‌فرض این نوع بخش

    برای ردیف برند/دسته‌بندی، پیش‌فرض نام همان برند یا دسته‌بندی است تا مدیر
    مجبور به تایپ دوباره‌ی آن نباشد.
    """
    if section.title:
        return section.title
    if (
        section.section_type == HomepageSection.SectionType.BRAND_PRODUCTS
        and section.brand_id
    ):
        return section.brand.name
    if (
        section.section_type == HomepageSection.SectionType.CATEGORY_PRODUCTS
        and section.category_id
    ):
        return section.category.title
    return DEFAULT_TITLES.get(section.section_type, "")


def resolved_limit(section: HomepageSection) -> int:
    return section.limit or DEFAULT_LIMITS.get(section.section_type, 8)


def _section_queryset(section: HomepageSection):
    """کوئری‌ست محصولات این بخش — پایه‌ی هم فهرست و هم شمارش کل

    برای بخش‌های غیرمحصولی None برمی‌گرداند. منطق فیلتر از catalog.selectors
    می‌آید تا با API عمومی محصولات یکی بماند.
    """
    section_type = section.section_type

    # ردیف برند/دسته‌بندی: مرجع الزامی است، اما اگر بخش هنوز ذخیره نشده باشد
    # (یا مرجعش رفته باشد) به‌جای خطا فهرست خالی برمی‌گردد
    if section_type == HomepageSection.SectionType.BRAND_PRODUCTS:
        if section.brand_id is None:
            return None
        return filtered_products_queryset(brand_slug=section.brand.slug, sort="newest")

    if section_type == HomepageSection.SectionType.CATEGORY_PRODUCTS:
        if section.category_id is None:
            return None
        return filtered_products_queryset(
            category_slug=section.category.slug, sort="newest"
        )

    if section_type == HomepageSection.SectionType.PRODUCT_COLLECTION:
        return filtered_products_queryset(
            category_slug=section.category.slug if section.category_id else None,
            brand_slug=section.brand.slug if section.brand_id else None,
            sort=section.sort or "newest",
        )

    filters = PRODUCT_SECTION_FILTERS.get(section_type)
    if filters is None:
        return None
    return filtered_products_queryset(**filters)


def section_products(section: HomepageSection) -> list[Product]:
    """محصولات این بخش را برمی‌گرداند — منطق فیلتر از catalog.selectors است."""
    qs = _section_queryset(section)
    if qs is None:
        return []
    return list(qs[: resolved_limit(section)])


def section_products_total(section: HomepageSection) -> int:
    """تعداد کل محصولات این بخش — بخش صفحه‌بندی‌شده به آن نیاز دارد"""
    qs = _section_queryset(section)
    return 0 if qs is None else qs.count()


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


def _clear_disallowed_references(section: HomepageSection) -> None:
    """پس از تعویض نوع بخش، مرجع‌هایی که به نوع تازه ربطی ندارند پاک می‌شوند

    بدون این کار، تعویض «محصولات برند» به «محصولات دسته‌بندی» با خطای
    «این فیلد برای این نوع بخش قابل استفاده نیست» رد می‌شد.
    """
    allowed = allowed_fields(section.section_type)
    if "brand" not in allowed:
        section.brand = None
    if "category" not in allowed:
        section.category = None
    if "banner" not in allowed:
        section.banner = None
    if "sort" not in allowed:
        section.sort = ""


@transaction.atomic
def update_section(section: HomepageSection, **fields) -> HomepageSection:
    for field_name, value in fields.items():
        setattr(section, field_name, value)
    if "section_type" in fields:
        _clear_disallowed_references(section)
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
