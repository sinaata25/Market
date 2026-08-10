from django.db.models import Avg, Count

from .models import Product, ProductComment, ProductRating


PURCHASED_ORDER_STATUSES = ("PAID", "SHIPPED", "DELIVERED")


def has_purchased_product(user, product_id: int) -> bool:
    if not user or not user.is_authenticated:
        return False
    from orders.models import OrderItem

    return OrderItem.objects.filter(
        product_id=product_id,
        order__user=user,
        order__status__in=PURCHASED_ORDER_STATUSES,
    ).exists()


def purchaser_ids_for_product(product_id: int, user_ids: set[int]) -> set[int]:
    if not user_ids:
        return set()
    from orders.models import OrderItem

    return set(
        OrderItem.objects.filter(
            product_id=product_id,
            order__user_id__in=user_ids,
            order__status__in=PURCHASED_ORDER_STATUSES,
        ).values_list("order__user_id", flat=True)
    )


def verified_purchase_pairs(
    product_user_pairs: set[tuple[int, int]],
) -> set[tuple[int, int]]:
    if not product_user_pairs:
        return set()
    from orders.models import OrderItem

    product_ids = {product_id for product_id, _ in product_user_pairs}
    user_ids = {user_id for _, user_id in product_user_pairs}
    purchased = set(
        OrderItem.objects.filter(
            product_id__in=product_ids,
            order__user_id__in=user_ids,
            order__status__in=PURCHASED_ORDER_STATUSES,
        ).values_list("product_id", "order__user_id")
    )
    return purchased & product_user_pairs


def recompute_product_rating(product_id: int) -> None:
    aggregate = ProductRating.objects.filter(product_id=product_id).aggregate(
        avg=Avg("rating"), count=Count("id")
    )
    Product.objects.filter(pk=product_id).update(
        rating=round(aggregate["avg"] or 0, 1),
        rating_count=aggregate["count"],
    )


def mask_author(user) -> str:
    if user.name:
        return user.name
    return f"کاربر {user.phone[:4]}***{user.phone[-2:]}"


def comment_dto(comment: ProductComment, verified_user_ids: set[int]) -> dict:
    return {
        "id": comment.id,
        "content": comment.content,
        "type": comment.comment_type,
        "status": comment.moderation_status,
        "parentId": comment.parent_id,
        "createdAt": comment.created_at.isoformat(),
        "updatedAt": comment.updated_at.isoformat(),
        "author": mask_author(comment.user),
        "isAdminResponse": bool(comment.user.is_staff),
        "isVerifiedPurchase": comment.user_id in verified_user_ids,
        "replies": [],
    }


def visible_comment_threads(product_id: int, user) -> list[dict]:
    visible_statuses = [ProductComment.ModerationStatus.APPROVED]
    comments = ProductComment.objects.filter(
        product_id=product_id,
        moderation_status__in=visible_statuses,
    )
    if user and user.is_authenticated:
        from django.db.models import Q

        comments = ProductComment.objects.filter(product_id=product_id).filter(
            Q(moderation_status=ProductComment.ModerationStatus.APPROVED)
            | Q(user=user)
        )

    rows = list(comments.select_related("user").order_by("created_at", "id"))
    verified_ids = purchaser_ids_for_product(
        product_id, {comment.user_id for comment in rows}
    )
    items = {comment.id: comment_dto(comment, verified_ids) for comment in rows}
    roots = []
    for comment in rows:
        item = items[comment.id]
        if comment.parent_id and comment.parent_id in items:
            items[comment.parent_id]["replies"].append(item)
        elif comment.parent_id is None:
            roots.append(item)
    return roots
