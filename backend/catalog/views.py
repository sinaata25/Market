import math

from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from common.responses import fail, ok

from .category_tree import descendant_category_ids, visible_category_ids
from .dto import category_dto, product_dto
from .models import Category, Product, Review

SORTS = {
    "newest": "-created_at",
    "cheapest": "price",
    "expensive": "-price",
    "popular": "-rating_count",
}


class CategoryLinkResponseSerializer(serializers.Serializer):
    slug = serializers.CharField()
    title = serializers.CharField()


class CategoryResponseSerializer(serializers.Serializer):
    slug = serializers.CharField()
    title = serializers.CharField()
    icon = serializers.CharField(
        allow_null=True,
        help_text="Relative media URL for a validated PNG or SVG icon, or null.",
    )
    sub = CategoryLinkResponseSerializer(many=True)
    isTopLevel = serializers.BooleanField()


class CategoryListDataSerializer(serializers.Serializer):
    categories = CategoryResponseSerializer(many=True)


class CategoryListEnvelopeSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    data = CategoryListDataSerializer()


class CategoryListView(APIView):
    """فهرست دسته‌بندی‌ها"""

    @extend_schema(responses={200: CategoryListEnvelopeSerializer})
    def get(self, request):
        visible_ids = visible_category_ids()
        categories = [
            category_dto(category, visible_ids=visible_ids)
            for category in Category.objects.filter(id__in=visible_ids).prefetch_related(
                "parents", "children"
            )
        ]
        return ok({"categories": categories})


class ProductListView(APIView):
    """فهرست محصولات با فیلتر، جستجو، مرتب‌سازی و صفحه‌بندی.

    مثال: /api/products?category=garden-tools&sort=cheapest&page=1
    """

    def get(self, request):
        qs = Product.objects.select_related("category").prefetch_related(
            "categories", "images"
        ).filter(is_active=True)

        category = request.query_params.get("category")
        if category:
            visible_ids = visible_category_ids()
            selected_category = Category.objects.filter(
                slug=category, id__in=visible_ids
            ).first()
            if selected_category is not None:
                category_ids = descendant_category_ids(
                    selected_category.id, allowed_ids=visible_ids
                )
                qs = qs.filter(
                    Q(category_id__in=category_ids)
                    | Q(categories__id__in=category_ids)
                ).distinct()
            else:
                qs = qs.none()

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(title__contains=search)

        if request.query_params.get("discounted") in ("true", "1"):
            qs = qs.filter(old_price__isnull=False)

        sort = request.query_params.get("sort", "newest")
        qs = qs.order_by(SORTS.get(sort, "-created_at"))

        try:
            page = max(1, int(request.query_params.get("page", 1)))
            per_page = min(50, max(1, int(request.query_params.get("perPage", 20))))
        except ValueError:
            return fail("پارامتر صفحه‌بندی نامعتبر است", 422)

        total = qs.count()
        start = (page - 1) * per_page
        items = [product_dto(p) for p in qs[start : start + per_page]]

        return ok(
            {
                "items": items,
                "total": total,
                "page": page,
                "perPage": per_page,
                "pages": math.ceil(total / per_page),
            }
        )


class ProductDetailView(APIView):
    """جزئیات یک محصول به‌همراه محصولات مرتبط"""

    def get(self, request, pk: int):
        try:
            product = (
                Product.objects.select_related("category")
                .prefetch_related("categories", "images")
                .get(pk=pk, is_active=True)
            )
        except Product.DoesNotExist:
            return fail("محصول یافت نشد", 404)

        category_ids = {category.id for category in product.categories.all()}
        category_ids.add(product.category_id)

        # اول محصولات دارای حداقل یک دسته‌ی مشترک، سپس سایر محصولات تا سقف ۴ مورد
        same = list(
            Product.objects.select_related("category")
            .prefetch_related("categories", "images")
            .filter(is_active=True)
            .filter(
                Q(category_id__in=category_ids)
                | Q(categories__id__in=category_ids)
            )
            .distinct()
            .exclude(pk=pk)[:4]
        )
        if len(same) < 4:
            others = (
                Product.objects.select_related("category")
                .prefetch_related("categories", "images")
                .filter(is_active=True)
                .exclude(
                    Q(category_id__in=category_ids)
                    | Q(categories__id__in=category_ids)
                )
                .exclude(pk=pk)
                .distinct()
                .order_by("-rating_count")[: 4 - len(same)]
            )
            same.extend(others)

        return ok(
            {
                "product": product_dto(product),
                "related": [product_dto(p) for p in same],
            }
        )


class ProductBySlugView(APIView):
    """یافتن محصول با نامک سئو (تنظیم‌شده در پنل سئو)"""

    def get(self, request, slug: str):
        from seo.models import PageMeta

        meta = PageMeta.objects.filter(page_type="product", slug=slug).first()
        if meta is None:
            return fail("محصول یافت نشد", 404)
        try:
            product_id = int(meta.object_key)
        except ValueError:
            return fail("محصول یافت نشد", 404)
        view = ProductDetailView()
        return view.get(request, pk=product_id)


def mask_author(user) -> str:
    """نام کاربر یا شماره‌ی ماسک‌شده"""
    if user.name:
        return user.name
    return f"کاربر {user.phone[:4]}***{user.phone[-2:]}"


class ReviewCreateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        error_messages={
            "required": "امتیاز الزامی است",
            "min_value": "امتیاز باید بین ۱ تا ۵ باشد",
            "max_value": "امتیاز باید بین ۱ تا ۵ باشد",
        },
    )
    text = serializers.CharField(
        min_length=5,
        max_length=1000,
        error_messages={
            "required": "متن دیدگاه الزامی است",
            "min_length": "متن دیدگاه حداقل ۵ حرف باشد",
            "max_length": "متن دیدگاه حداکثر ۱۰۰۰ حرف باشد",
        },
    )


class ReviewListCreateView(APIView):
    """فهرست دیدگاه‌های محصول / ثبت دیدگاه (نیازمند ورود)"""

    def get(self, request, pk: int):
        if not Product.objects.filter(pk=pk, is_active=True).exists():
            return fail("محصول یافت نشد", 404)
        reviews = Review.objects.filter(
            product_id=pk, is_published=True
        ).select_related("user")
        return ok(
            {
                "reviews": [
                    {
                        "id": r.id,
                        "rating": r.rating,
                        "text": r.text,
                        "createdAt": r.created_at.isoformat(),
                        "author": mask_author(r.user),
                    }
                    for r in reviews
                ]
            }
        )

    def post(self, request, pk: int):
        if not request.user.is_authenticated:
            return fail("برای ثبت دیدگاه ابتدا وارد شوید", 401)

        try:
            product = Product.objects.get(pk=pk, is_active=True)
        except Product.DoesNotExist:
            return fail("محصول یافت نشد", 404)

        ser = ReviewCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        if Review.objects.filter(product=product, user=request.user).exists():
            return fail("شما قبلاً برای این محصول دیدگاه ثبت کرده‌اید", 409)

        review = Review.objects.create(
            product=product,
            user=request.user,
            rating=ser.validated_data["rating"],
            text=ser.validated_data["text"],
        )

        return ok(
            {"review": {"id": review.id, "isPublished": review.is_published}},
            status=201,
        )
