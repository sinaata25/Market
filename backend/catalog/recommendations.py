"""Manual product recommendations: validation, writes, and efficient selectors."""

from __future__ import annotations

from collections.abc import Iterable

from django.db import transaction
from django.db.models import Prefetch

from .dto import product_dto
from .models import Product, ProductRecommendation

MAX_PRODUCT_RECOMMENDATIONS = 3
MAX_CART_RECOMMENDATIONS = 6


class RecommendationValidationError(Exception):
    pass


def product_recommendation_prefetch() -> Prefetch:
    return Prefetch(
        "recommendation_links",
        queryset=(
            ProductRecommendation.objects.select_related(
                "recommended_product__category", "recommended_product__brand"
            )
            .prefetch_related(
                "recommended_product__categories", "recommended_product__images"
            )
            .order_by("position", "id")
        ),
    )


def recommended_products_dto(product: Product) -> list[dict]:
    return [
        product_dto(link.recommended_product)
        for link in product.recommendation_links.all()
    ]


@transaction.atomic
def replace_product_recommendations(
    product: Product, recommended_product_ids: Iterable[int]
) -> None:
    ids = list(recommended_product_ids)
    if len(ids) > MAX_PRODUCT_RECOMMENDATIONS:
        raise RecommendationValidationError(
            "برای هر محصول حداکثر ۳ محصول پیشنهادی قابل انتخاب است"
        )
    if len(ids) != len(set(ids)):
        raise RecommendationValidationError("محصول پیشنهادی تکراری مجاز نیست")
    if product.pk in ids:
        raise RecommendationValidationError("یک محصول نمی‌تواند به خودش پیشنهاد شود")

    products_by_id = Product.objects.in_bulk(ids)
    if len(products_by_id) != len(ids):
        raise RecommendationValidationError("یک یا چند محصول پیشنهادی یافت نشد")

    # Serializes concurrent replacements for the same source product.
    Product.objects.select_for_update().get(pk=product.pk)
    ProductRecommendation.objects.filter(source_product=product).delete()
    ProductRecommendation.objects.bulk_create(
        [
            ProductRecommendation(
                source_product=product,
                recommended_product=products_by_id[product_id],
                position=position,
            )
            for position, product_id in enumerate(ids)
        ]
    )


def cart_recommendation_dtos(cart_products: list[Product]) -> list[dict]:
    """Return at most six purchasable recommendations, deduplicated across sources."""
    if not cart_products:
        return []

    cart_product_ids = [product.id for product in cart_products]
    cart_product_id_set = set(cart_product_ids)
    source_order = {
        product_id: position for position, product_id in enumerate(cart_product_ids)
    }
    links = list(
        ProductRecommendation.objects.filter(
            source_product_id__in=cart_product_ids,
            recommended_product__is_active=True,
            recommended_product__stock__gt=0,
        )
        .exclude(recommended_product_id__in=cart_product_id_set)
        .select_related(
            "source_product",
            "recommended_product__category",
            "recommended_product__brand",
        )
        .prefetch_related(
            "recommended_product__categories", "recommended_product__images"
        )
    )
    links.sort(
        key=lambda link: (source_order[link.source_product_id], link.position, link.id)
    )

    results_by_product: dict[int, dict] = {}
    for link in links:
        result = results_by_product.get(link.recommended_product_id)
        context = {
            "id": link.source_product_id,
            "title": link.source_product.title,
        }
        if result is not None:
            result["recommendedFor"].append(context)
            continue
        if len(results_by_product) >= MAX_CART_RECOMMENDATIONS:
            continue
        results_by_product[link.recommended_product_id] = {
            "product": product_dto(link.recommended_product),
            "recommendedFor": [context],
        }

    return list(results_by_product.values())
