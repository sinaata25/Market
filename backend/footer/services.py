from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max

from seo.models import SeoSettings

from .files import schedule_footer_image_delete
from .maps import maps_directions_url, maps_search_url
from .models import (
    FooterIcon,
    FooterItem,
    FooterSection,
    FooterSettings,
    allowed_fields,
)
from .revalidation import schedule_footer_revalidation


class FooterValidationError(Exception):
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


def _save(instance, **kwargs) -> None:
    try:
        instance.save(**kwargs)
    except ValidationError as exc:
        raise FooterValidationError(_flatten(exc)) from exc
    schedule_footer_revalidation(using=instance._state.db or "default")


def _renumber(rows: list) -> None:
    """ترتیب‌ها را به ۰..n-۱ برمی‌گرداند تا هیچ شکاف یا مقدار تکراری نماند"""
    if not rows:
        return
    for index, row in enumerate(rows):
        row.position = index
    type(rows[0]).objects.bulk_update(rows, ["position"])


def _ordered_sections() -> list[FooterSection]:
    return list(FooterSection.objects.order_by("position", "id").select_for_update())


def _ordered_items(section_id: int) -> list[FooterItem]:
    return list(
        FooterItem.objects.filter(section_id=section_id)
        .order_by("position", "id")
        .select_for_update()
    )


def _next_position(queryset) -> int:
    last = queryset.aggregate(value=Max("position"))["value"]
    return 0 if last is None else last + 1


# ---------------------------------------------------------------- settings


@transaction.atomic
def update_settings(**fields) -> FooterSettings:
    settings_row = FooterSettings.load()
    for field_name, value in fields.items():
        setattr(settings_row, field_name, value)
    _save(settings_row)
    return settings_row


# ---------------------------------------------------------------- sections


@transaction.atomic
def create_section(**fields) -> FooterSection:
    section = FooterSection(
        position=_next_position(FooterSection.objects), **fields
    )
    _save(section)
    return section


@transaction.atomic
def update_section(section: FooterSection, **fields) -> FooterSection:
    for field_name, value in fields.items():
        setattr(section, field_name, value)
    _save(section)
    return section


@transaction.atomic
def delete_section(section: FooterSection) -> None:
    using = section._state.db or "default"
    stored_images = [
        (item.image.name, item.image.storage)
        for item in section.items.all()
        if item.image
    ]
    section.delete()
    for name, storage in stored_images:
        schedule_footer_image_delete(name, storage, using=using)
    _renumber(_ordered_sections())
    schedule_footer_revalidation(using=using)


@transaction.atomic
def move_section(section: FooterSection, direction: str) -> list[FooterSection]:
    """جابه‌جایی یک‌پله‌ی بخش و بازشماری کامل ترتیب‌ها"""
    sections = _swap(_ordered_sections(), section.pk, direction)
    schedule_footer_revalidation(using=section._state.db or "default")
    return sections


# ------------------------------------------------------------------- items


@transaction.atomic
def create_item(*, section: FooterSection, **fields) -> FooterItem:
    item = FooterItem(
        section=section,
        position=_next_position(FooterItem.objects.filter(section=section)),
        **fields,
    )
    _save(item)
    return item


def _clear_disallowed_fields(item: FooterItem) -> None:
    """پس از تعویض نوع آیتم، فیلدهایی که به نوع تازه ربطی ندارند پاک می‌شوند"""
    allowed = allowed_fields(item.item_type)
    if "label" not in allowed:
        item.label = ""
    if "url" not in allowed:
        item.url = ""
    if "text" not in allowed:
        item.text = ""
    if "image" not in allowed:
        item.image = ""
    if "icon" not in allowed:
        item.icon = ""
    if "icon_image" not in allowed:
        item.icon_image = None
    if "open_in_new_tab" not in allowed:
        item.open_in_new_tab = False
    if "static_page_key" not in allowed:
        item.static_page_key = ""


@transaction.atomic
def update_item(item: FooterItem, **fields) -> FooterItem:
    stored_image = item.image.name if item.image else ""
    storage = item.image.storage if item.image else None
    for field_name, value in fields.items():
        setattr(item, field_name, value)
    if "item_type" in fields:
        _clear_disallowed_fields(item)
    _save(item)
    # تعویض نوع آیتم تصویر را رها می‌کند؛ فایل بی‌مرجع نباید در media بماند
    if stored_image and not item.image:
        schedule_footer_image_delete(
            stored_image, storage, using=item._state.db or "default"
        )
    return item


@transaction.atomic
def delete_item(item: FooterItem) -> None:
    section_id = item.section_id
    using = item._state.db or "default"
    stored_image = item.image.name if item.image else ""
    storage = item.image.storage if item.image else None
    item.delete()
    schedule_footer_image_delete(stored_image, storage, using=using)
    _renumber(_ordered_items(section_id))
    schedule_footer_revalidation(using=using)


@transaction.atomic
def move_item(item: FooterItem, direction: str) -> list[FooterItem]:
    items = _swap(_ordered_items(item.section_id), item.pk, direction)
    schedule_footer_revalidation(using=item._state.db or "default")
    return items


def _swap(rows: list, pk: int, direction: str) -> list:
    index = next(i for i, row in enumerate(rows) if row.pk == pk)
    if direction == "up" and index > 0:
        rows[index - 1], rows[index] = rows[index], rows[index - 1]
    elif direction == "down" and index < len(rows) - 1:
        rows[index + 1], rows[index] = rows[index], rows[index + 1]
    _renumber(rows)
    return rows


# ------------------------------------------------------- derived settings

# نام برند و کپی‌رایت می‌توانند خالی بمانند؛ در آن حالت از منبع موجود
# پروژه (نام سایت در تنظیمات سئو) پُر می‌شوند تا برای یک چیز دو جای
# ویرایش وجود نداشته باشد.
DEFAULT_COPYRIGHT = "© {year} {brand} — تمامی حقوق محفوظ است."


def _site_name() -> str:
    """نام سایت بدون ساختن ردیف تنظیمات سئو — این تابع در مسیر عمومی است"""
    stored = SeoSettings.objects.values_list("site_name", flat=True).first()
    return stored or SeoSettings._meta.get_field("site_name").default


def resolved_brand_title(settings_row: FooterSettings) -> str:
    return settings_row.brand_title.strip() or _site_name()


def resolved_copyright(settings_row: FooterSettings, *, year: int) -> str:
    template = settings_row.copyright_text.strip() or DEFAULT_COPYRIGHT
    return template.replace("{year}", str(year)).replace(
        "{brand}", resolved_brand_title(settings_row)
    )


def shop_coordinates(settings_row: FooterSettings):
    """جفت مختصات فروشگاه، یا None اگر کامل تنظیم نشده باشد"""
    if settings_row.latitude is None or settings_row.longitude is None:
        return None
    return settings_row.latitude, settings_row.longitude


def shop_map_is_visible(settings_row: FooterSettings) -> bool:
    """نقشه فقط وقتی در فوتر می‌آید که مدیر روشنش کرده و مختصات کامل باشد"""
    return settings_row.show_map and shop_coordinates(settings_row) is not None


def shop_maps_url(settings_row: FooterSettings) -> str:
    """«مشاهده روی نقشه» — پیوند دلخواه مدیر، وگرنه ساخته‌شده از مختصات"""
    coordinates = shop_coordinates(settings_row)
    if coordinates is None:
        return ""
    return settings_row.maps_place_url or maps_search_url(*coordinates)


def shop_directions_url(settings_row: FooterSettings) -> str:
    """«مسیریابی» — همیشه از مختصات، تا سوزن دقیقاً روی فروشگاه بیفتد"""
    coordinates = shop_coordinates(settings_row)
    return maps_directions_url(*coordinates) if coordinates else ""


# --------------------------------------------------------------- icons


@transaction.atomic
def create_icon(**fields) -> FooterIcon:
    icon = FooterIcon(**fields)
    _save(icon)
    return icon


@transaction.atomic
def update_icon(icon: FooterIcon, **fields) -> FooterIcon:
    for field_name, value in fields.items():
        setattr(icon, field_name, value)
    _save(icon)
    return icon


@transaction.atomic
def delete_icon(icon: FooterIcon) -> None:
    """آیکن حذف می‌شود و هر جا استفاده شده بی‌آیکن می‌ماند، نه شکسته"""
    using = icon._state.db or "default"
    stored_image = icon.image.name if icon.image else ""
    storage = icon.image.storage if icon.image else None
    icon.delete()
    schedule_footer_image_delete(stored_image, storage, using=using)
    schedule_footer_revalidation(using=using)
