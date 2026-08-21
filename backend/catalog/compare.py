"""اعتبارسنجی و آماده‌سازی داده برای مقایسه محصولات (بدون مدل جدید در دیتابیس)"""

from __future__ import annotations

from django.core.exceptions import ValidationError

from .dto import product_dto
from .models import Product
from .specifications import product_specification_prefetch

MIN_COMPARE_PRODUCTS = 2
MAX_COMPARE_PRODUCTS = 5


def _category_ids(product: Product) -> set[int]:
    ids = {product.category_id}
    ids.update(category.id for category in product.categories.all())
    return ids


def validate_compare_product_ids(product_ids: list[int]) -> None:
    if len(product_ids) < MIN_COMPARE_PRODUCTS:
        raise ValidationError(
            f"برای مقایسه حداقل {MIN_COMPARE_PRODUCTS} محصول لازم است"
        )
    if len(product_ids) > MAX_COMPARE_PRODUCTS:
        raise ValidationError(
            f"حداکثر {MAX_COMPARE_PRODUCTS} محصول را می‌توان هم‌زمان مقایسه کرد"
        )
    if len(set(product_ids)) != len(product_ids):
        raise ValidationError("محصولات تکراری نمی‌توانند در مقایسه باشند")


def load_comparable_products(product_ids: list[int]) -> list[Product]:
    """Fetch products (in the requested order), efficiently, ready for `product_dto`."""

    products = list(
        Product.objects.select_related("category", "brand")
        .prefetch_related("categories", "images", product_specification_prefetch())
        .filter(pk__in=product_ids, is_active=True)
    )
    by_id = {product.id: product for product in products}
    missing = [pid for pid in product_ids if pid not in by_id]
    if missing:
        raise ValidationError("یک یا چند محصول یافت نشد یا دیگر در دسترس نیست")

    ordered = [by_id[pid] for pid in product_ids]

    common_category_ids = _category_ids(ordered[0])
    for product in ordered[1:]:
        common_category_ids &= _category_ids(product)
    if not common_category_ids:
        raise ValidationError(
            "محصولات انتخاب‌شده باید همگی به یک دسته‌بندی مشترک تعلق داشته باشند"
        )

    return ordered


def compare_dto(product_ids: list[int]) -> dict:
    validate_compare_product_ids(product_ids)
    products = load_comparable_products(product_ids)
    return {
        "items": [
            product_dto(product, include_specifications=True) for product in products
        ]
    }
