import math

from django.db import transaction
from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from common.responses import fail, ok

from .category_tree import descendant_category_ids, visible_category_ids
from .dto import brand_dto, category_dto, product_dto
from .feedback import (
    has_purchased_product,
    recompute_product_rating,
    visible_comment_threads,
)
from .models import Brand, Category, Product, ProductComment, ProductRating
from .specifications import product_specification_prefetch

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


class BrandResponseSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    logo = serializers.CharField(allow_null=True)
    website = serializers.CharField(allow_null=True)
    isActive = serializers.BooleanField()


class BrandListDataSerializer(serializers.Serializer):
    brands = BrandResponseSerializer(many=True)


class BrandListEnvelopeSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    data = BrandListDataSerializer()


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


class BrandListView(APIView):
    """فهرست برندهای فعال، مستقل از درخت دسته‌بندی"""

    @extend_schema(responses={200: BrandListEnvelopeSerializer})
    def get(self, request):
        brands = Brand.objects.filter(is_active=True)
        return ok({"brands": [brand_dto(brand) for brand in brands]})


class ProductListView(APIView):
    """فهرست محصولات با فیلتر، جستجو، مرتب‌سازی و صفحه‌بندی.

    مثال: /api/products?category=garden-tools&sort=cheapest&page=1
    """

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "category",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Category slug; includes visible descendants.",
            ),
            OpenApiParameter(
                "brand",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description="Active brand slug; independent from category.",
            ),
            OpenApiParameter("search", OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter(
                "discounted", OpenApiTypes.BOOL, OpenApiParameter.QUERY
            ),
            OpenApiParameter("sort", OpenApiTypes.STR, OpenApiParameter.QUERY),
            OpenApiParameter("page", OpenApiTypes.INT, OpenApiParameter.QUERY),
            OpenApiParameter(
                "perPage", OpenApiTypes.INT, OpenApiParameter.QUERY
            ),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        qs = Product.objects.select_related("category", "brand").prefetch_related(
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

        brand = request.query_params.get("brand")
        if brand:
            qs = qs.filter(brand__slug=brand, brand__is_active=True)

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
                Product.objects.select_related("category", "brand")
                .prefetch_related(
                    "categories", "images", product_specification_prefetch()
                )
                .get(pk=pk, is_active=True)
            )
        except Product.DoesNotExist:
            return fail("محصول یافت نشد", 404)

        category_ids = {category.id for category in product.categories.all()}
        category_ids.add(product.category_id)

        # اول محصولات دارای حداقل یک دسته‌ی مشترک، سپس سایر محصولات تا سقف ۴ مورد
        same = list(
            Product.objects.select_related("category", "brand")
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
                Product.objects.select_related("category", "brand")
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
                "product": product_dto(product, include_specifications=True),
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


class RatingWriteSerializer(serializers.Serializer):
    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        error_messages={
            "required": "امتیاز الزامی است",
            "min_value": "امتیاز باید بین ۱ تا ۵ باشد",
            "max_value": "امتیاز باید بین ۱ تا ۵ باشد",
        },
    )


class CommentCreateSerializer(serializers.Serializer):
    content = serializers.CharField(
        min_length=5,
        max_length=2000,
        error_messages={
            "required": "متن دیدگاه الزامی است",
            "min_length": "متن دیدگاه حداقل ۵ حرف باشد",
            "max_length": "متن دیدگاه حداکثر ۲۰۰۰ حرف باشد",
        },
    )
    type = serializers.ChoiceField(
        choices=ProductComment.Type.choices,
        default=ProductComment.Type.COMMENT,
    )
    parentId = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class ProductRatingView(APIView):
    """آمار امتیاز و ثبت/ویرایش امتیاز خریدار"""

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request, pk: int):
        product = Product.objects.filter(pk=pk, is_active=True).first()
        if product is None:
            return fail("محصول یافت نشد", 404)

        my_rating = None
        if request.user.is_authenticated:
            my_rating = ProductRating.objects.filter(
                product=product, user=request.user
            ).values_list("rating", flat=True).first()
        return ok(
            {
                "rating": {
                    "average": product.rating,
                    "count": product.rating_count,
                    "myRating": my_rating,
                    "canRate": has_purchased_product(request.user, product.id),
                }
            }
        )

    @extend_schema(
        request=RatingWriteSerializer,
        responses={200: OpenApiTypes.OBJECT, 201: OpenApiTypes.OBJECT},
    )
    def put(self, request, pk: int):
        if not request.user.is_authenticated:
            return fail("برای ثبت امتیاز ابتدا وارد شوید", 401)

        try:
            product = Product.objects.get(pk=pk, is_active=True)
        except Product.DoesNotExist:
            return fail("محصول یافت نشد", 404)

        if not has_purchased_product(request.user, product.id):
            return fail("فقط خریداران این محصول می‌توانند امتیاز بدهند", 403)

        ser = RatingWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=product.pk)
            rating, created = ProductRating.objects.update_or_create(
                product=product,
                user=request.user,
                defaults={"rating": ser.validated_data["rating"]},
            )
            recompute_product_rating(product.id)
            product.refresh_from_db(fields=["rating", "rating_count"])
        return ok(
            {
                "rating": {
                    "value": rating.rating,
                    "average": product.rating,
                    "count": product.rating_count,
                }
            },
            status=201 if created else 200,
        )


class ProductCommentListCreateView(APIView):
    """گفتگوهای تاییدشده و پیام‌های خود کاربر"""

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request, pk: int):
        if not Product.objects.filter(pk=pk, is_active=True).exists():
            return fail("محصول یافت نشد", 404)
        return ok({"comments": visible_comment_threads(pk, request.user)})

    @extend_schema(
        request=CommentCreateSerializer,
        responses={201: OpenApiTypes.OBJECT},
    )
    def post(self, request, pk: int):
        if not request.user.is_authenticated:
            return fail("برای ثبت دیدگاه ابتدا وارد شوید", 401)

        product = Product.objects.filter(pk=pk, is_active=True).first()
        if product is None:
            return fail("محصول یافت نشد", 404)

        ser = CommentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        parent = None
        parent_id = ser.validated_data.get("parentId")
        if parent_id:
            parent = ProductComment.objects.filter(
                pk=parent_id,
                product=product,
                moderation_status=ProductComment.ModerationStatus.APPROVED,
            ).first()
            if parent is None:
                return fail("پیام مرجع یافت نشد یا هنوز تایید نشده است", 409)

        status = (
            ProductComment.ModerationStatus.APPROVED
            if request.user.is_staff
            else ProductComment.ModerationStatus.PENDING
        )
        comment = ProductComment.objects.create(
            product=product,
            user=request.user,
            parent=parent,
            content=ser.validated_data["content"].strip(),
            comment_type=(
                parent.comment_type if parent else ser.validated_data["type"]
            ),
            moderation_status=status,
        )

        return ok(
            {
                "comment": {
                    "id": comment.id,
                    "status": comment.moderation_status,
                    "isAdminResponse": bool(request.user.is_staff),
                }
            },
            status=201,
        )
