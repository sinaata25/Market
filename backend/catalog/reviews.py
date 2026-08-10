from django.db.models import Avg, Count

from .models import Product, Review


def recompute_product_rating(product_id: int) -> None:
    """Keep a product's public rating in sync with published reviews only."""
    aggregate = Review.objects.filter(
        product_id=product_id, is_published=True
    ).aggregate(avg=Avg("rating"), count=Count("id"))
    Product.objects.filter(pk=product_id).update(
        rating=round(aggregate["avg"] or 0, 1),
        rating_count=aggregate["count"],
    )
