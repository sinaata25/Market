"""کوئری‌های قابل استفاده‌ی مجدد محصولات — هم برای API عمومی و هم بخش‌های صفحه اصلی"""

from django.db.models import Q, QuerySet

from .category_tree import descendant_category_ids, visible_category_ids
from .models import Category, Product

SORTS = {
    "newest": "-created_at",
    "cheapest": "price",
    "expensive": "-price",
    "popular": "-rating_count",
    # ترتیب انتخاب مدیر برای پرفروش‌ترین‌ها — مستقل از آمار فروش/امتیاز واقعی
    "featured": ("best_seller_position", "-created_at"),
}


def filtered_products_queryset(
    *,
    category_slug: str | None = None,
    brand_slug: str | None = None,
    search: str | None = None,
    discounted: bool = False,
    best_seller: bool = False,
    sort: str = "newest",
) -> QuerySet[Product]:
    """فهرست محصولات فعال با همان فیلترهایی که ProductListView عمومی می‌پذیرد.

    منبع واحد منطق فیلتر محصول — هم API عمومی محصولات و هم بخش‌های محصولی
    صفحه اصلی از همین تابع استفاده می‌کنند تا کوئری تکراری نشود.
    """
    qs = Product.objects.select_related("category", "brand").prefetch_related(
        "categories", "images"
    ).filter(is_active=True)

    if category_slug:
        visible_ids = visible_category_ids()
        selected_category = Category.objects.filter(
            slug=category_slug, id__in=visible_ids
        ).first()
        if selected_category is not None:
            category_ids = descendant_category_ids(
                selected_category.id, allowed_ids=visible_ids
            )
            qs = qs.filter(
                Q(category_id__in=category_ids) | Q(categories__id__in=category_ids)
            ).distinct()
        else:
            qs = qs.none()

    if brand_slug:
        qs = qs.filter(brand__slug=brand_slug, brand__is_active=True)

    if search:
        qs = qs.filter(title__contains=search)

    if discounted:
        qs = qs.filter(old_price__isnull=False)

    # پرفروش‌ترین‌ها انتخاب دستی مدیر است، نه آمار فروش/امتیاز واقعی
    if best_seller:
        qs = qs.filter(is_best_seller=True)

    order = SORTS.get(sort, "-created_at")
    return qs.order_by(*order) if isinstance(order, tuple) else qs.order_by(order)
