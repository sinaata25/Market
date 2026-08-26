"""Normalization and transactional writes for reusable product specifications."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, TypedDict

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.utils.text import slugify

if TYPE_CHECKING:
    from .models import Product, SpecificationKey


_ARABIC_TO_PERSIAN = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})
_SPACE_RE = re.compile(r"\s+")
MAX_SPECIFICATION_POSITION = 2_147_483_647


class SpecificationInput(TypedDict):
    key_id: int
    value: str
    position: int


def _canonical_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.translate(_ARABIC_TO_PERSIAN)
    text = text.replace("\u00a0", " ").replace("\u200c", " ")
    return _SPACE_RE.sub(" ", text).strip()


def normalize_specification_name(value: object) -> tuple[str, str]:
    """Return a clean display name and a case-insensitive canonical identity."""

    display_name = _canonical_text(value)
    if not display_name:
        raise ValueError("نام مشخصه نمی‌تواند خالی باشد")
    if len(display_name) > 100:
        raise ValueError("نام مشخصه حداکثر ۱۰۰ نویسه باشد")
    return display_name, display_name.casefold()


def normalize_specification_value(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    if not text:
        raise ValueError("مقدار مشخصه نمی‌تواند خالی باشد")
    if len(text) > 500:
        raise ValueError("مقدار مشخصه حداکثر ۵۰۰ نویسه باشد")
    return text


def unique_specification_slug(instance: SpecificationKey, name: str) -> str:
    max_length = instance._meta.get_field("slug").max_length
    base = slugify(name, allow_unicode=True).strip("-") or "specification"
    base = base[:max_length].rstrip("-") or "specification"
    candidate = base
    suffix = 2
    queryset = type(instance).objects.all()
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)
    while queryset.filter(slug=candidate).exists():
        marker = f"-{suffix}"
        candidate = f"{base[: max_length - len(marker)].rstrip('-')}{marker}"
        suffix += 1
    return candidate


def product_specification_prefetch() -> Prefetch:
    from .models import ProductSpecification

    return Prefetch(
        "specifications",
        queryset=ProductSpecification.objects.select_related("key").order_by(
            "position", "id"
        ),
    )


def validate_specification_inputs(
    raw_items: Iterable[Mapping[str, object]],
) -> list[SpecificationInput]:
    from .models import SpecificationKey

    items: list[SpecificationInput] = []
    seen_key_ids: set[int] = set()
    for index, raw_item in enumerate(raw_items):
        key_id = raw_item.get("keyId")
        value = raw_item.get("value")
        position = raw_item.get("position", index)
        if isinstance(key_id, bool) or not isinstance(key_id, int) or key_id < 1:
            raise ValidationError(
                {"specifications": f"شناسه مشخصه ردیف {index + 1} نامعتبر است"}
            )
        if key_id in seen_key_ids:
            raise ValidationError(
                {"specifications": "یک مشخصه نمی‌تواند دو بار برای یک محصول تکرار شود"}
            )
        if (
            isinstance(position, bool)
            or not isinstance(position, int)
            or not 0 <= position <= MAX_SPECIFICATION_POSITION
        ):
            raise ValidationError(
                {"specifications": f"ترتیب ردیف {index + 1} نامعتبر است"}
            )
        try:
            clean_value = normalize_specification_value(value)
        except ValueError as exc:
            raise ValidationError({"specifications": str(exc)}) from exc
        seen_key_ids.add(key_id)
        items.append({"key_id": key_id, "value": clean_value, "position": position})

    existing_ids = set(
        SpecificationKey.objects.filter(pk__in=seen_key_ids).values_list("pk", flat=True)
    )
    missing_ids = seen_key_ids - existing_ids
    if missing_ids:
        raise ValidationError({"specifications": "یک یا چند مشخصه یافت نشد"})
    return items


def replace_product_specifications(
    product: Product, items: Iterable[SpecificationInput]
) -> None:
    from .models import ProductSpecification

    ProductSpecification.objects.filter(product=product).delete()
    ProductSpecification.objects.bulk_create(
        [
            ProductSpecification(
                product=product,
                key_id=item["key_id"],
                value=item["value"],
                position=item["position"],
            )
            for item in items
        ]
    )


@transaction.atomic
def save_product_with_specifications(
    *, product: Product, data: dict, specification_items: list[SpecificationInput] | None
) -> Product:
    """Save the product, category assignment and optional spec replacement atomically."""

    from .models import Product

    if product.pk:
        product = Product.objects.select_for_update().get(pk=product.pk)

    categories = data["categories"]
    product.title = data["title"]
    product.title_en = data.get("titleEn", "")
    product.category = categories[0]
    product.brand = data["brand"]
    product.price = data["price"]
    product.old_price = data.get("oldPrice")
    product.stock = data["stock"]
    product.badge = data.get("badge", "")
    product.description = data.get("description", "")
    product.warranty = data.get("warranty", "")
    product.shipping_note = data.get("shippingNote", "")
    product.return_note = data.get("returnNote", "")
    product.save()
    product.categories.set(categories)
    if specification_items is not None:
        replace_product_specifications(product, specification_items)
    return product
