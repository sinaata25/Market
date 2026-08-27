"""API های داشبورد مدیریت — فقط برای مدیران فروشگاه (نه مدیر سئو)"""

import math
from datetime import timedelta
from decimal import Decimal

from PIL import Image, UnidentifiedImageError
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Avg, Count, F, IntegerField, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from accounts.permissions import ShopAdminRequiredMixin, is_manager_admin
from catalog.category_tree import visible_category_ids
from catalog.brand_files import schedule_brand_logo_delete
from catalog.brand_pricing import adjust_brand_prices
from catalog.dto import brand_dto, category_dto, category_summary, product_dto
from catalog.feedback import verified_purchase_pairs
from catalog.icon_files import schedule_category_icon_delete
from catalog.models import (
    Brand,
    Category,
    Product,
    ProductComment,
    ProductImage,
    ProductRating,
    SpecificationKey,
)
from catalog.recommendations import (
    RecommendationValidationError,
    product_recommendation_prefetch,
    recommended_products_dto,
    replace_product_recommendations,
)
from catalog.specifications import (
    MAX_SPECIFICATION_POSITION,
    normalize_specification_name,
    product_specification_prefetch,
    save_product_with_specifications,
    validate_specification_inputs,
)
from catalog.validators import validate_category_icon
from common.responses import fail, ok
from common.search import SearchQueryTooLong, filter_by_search
from orders.models import Order, OrderItem

User = get_user_model()

VALID_STATUSES = [s for s, _ in Order.Status.choices]


def positive_page(value) -> int | None:
    try:
        page = max(1, int(value or 1))
        return page if page <= 1_000_000 else None
    except (TypeError, ValueError):
        return None


def admin_product_dto(product: Product) -> dict:
    """DTO محصول برای ادمین + شناسه تصاویر (برای حذف)"""
    data = product_dto(product, include_specifications=True)
    data["imageItems"] = [
        {"id": img.id, "url": img.image.url} for img in product.images.all()
    ]
    data["recommendedProducts"] = recommended_products_dto(product)
    return data


def admin_created_product_dto(product: Product) -> dict:
    data = product_dto(product, include_specifications=True)
    data["recommendedProducts"] = recommended_products_dto(product)
    return data


def specification_key_dto(key: SpecificationKey) -> dict:
    return {
        "id": key.id,
        "name": key.name,
        "slug": key.slug,
        "productCount": (
            key.product_count
            if hasattr(key, "product_count")
            else key.product_specifications.values("product_id").distinct().count()
        ),
    }


def specification_keys_queryset():
    return SpecificationKey.objects.annotate(
        product_count=Count("product_specifications__product", distinct=True)
    )


def admin_brand_dto(brand: Brand) -> dict:
    data = brand_dto(brand)
    data.update(
        {
            "id": brand.id,
            "isActive": brand.is_active,
            "productCount": (
                brand.product_count
                if hasattr(brand, "product_count")
                else brand.products.count()
            ),
        }
    )
    return data


def order_row(o: Order) -> dict:
    return {
        "id": o.id,
        "code": o.code,
        "status": o.status,
        "createdAt": o.created_at.isoformat(),
        "fullName": o.full_name,
        "phone": o.phone,
        "province": o.province,
        "city": o.city,
        "address": o.address,
        "postalCode": o.postal_code,
        "itemsPrice": o.items_price,
        "discount": o.discount,
        "shippingPrice": o.shipping_price,
        "totalPrice": o.total_price,
        "items": [
            {"id": i.id, "title": i.title, "price": i.price, "qty": i.qty}
            for i in o.items.all()
        ],
    }


# ─── آمار داشبورد ────────────────────────────────────────────


class StatsView(ShopAdminRequiredMixin, APIView):
    def get(self, request):
        active_orders = Order.objects.exclude(status=Order.Status.CANCELED)

        revenue = active_orders.aggregate(s=Sum("total_price"))["s"] or 0

        # فروش ۱۴ روز اخیر (بر اساس روز)
        since = timezone.localdate() - timedelta(days=13)
        daily_qs = (
            active_orders.filter(created_at__date__gte=since)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("total_price"), count=Count("id"))
        )
        daily_map = {row["day"]: row for row in daily_qs}
        sales_by_day = []
        for i in range(14):
            day = since + timedelta(days=i)
            row = daily_map.get(day)
            sales_by_day.append(
                {
                    "date": day.isoformat(),
                    "total": row["total"] if row else 0,
                    "count": row["count"] if row else 0,
                }
            )

        status_breakdown = {
            row["status"]: row["count"]
            for row in Order.objects.values("status").annotate(count=Count("id"))
        }

        top_rows = (
            OrderItem.objects.exclude(order__status=Order.Status.CANCELED)
            .values("product_id", "title")
            .annotate(
                sold=Sum("qty"),
                revenue=Sum(
                    F("price") * F("qty"), output_field=IntegerField()
                ),
            )
            .order_by("-sold")[:5]
        )
        top_products = [
            {
                "product_id": r["product_id"],
                "title": r["title"],
                "qty": r["sold"],
                "revenue": r["revenue"],
            }
            for r in top_rows
        ]

        low_stock = [
            {"id": p.id, "title": p.title, "stock": p.stock}
            for p in Product.objects.filter(stock__lte=5).order_by("stock")[:8]
        ]

        recent_orders = [
            order_row(o)
            for o in Order.objects.prefetch_related("items").order_by("-created_at")[:6]
        ]

        return ok(
            {
                "totals": {
                    "revenue": revenue,
                    "orders": Order.objects.count(),
                    "pendingOrders": Order.objects.filter(
                        status=Order.Status.PENDING
                    ).count(),
                    "users": User.objects.count(),
                    "products": Product.objects.count(),
                    "comments": ProductComment.objects.count(),
                    "ratings": ProductRating.objects.count(),
                    "avgRating": round(
                        ProductRating.objects.aggregate(a=Avg("rating"))["a"] or 0,
                        1,
                    ),
                },
                "salesByDay": sales_by_day,
                "statusBreakdown": status_breakdown,
                "topProducts": top_products,
                "lowStock": low_stock,
                "recentOrders": recent_orders,
            }
        )


# ─── سفارش‌ها ────────────────────────────────────────────────


class AdminOrderListView(ShopAdminRequiredMixin, APIView):
    def get(self, request):
        qs = Order.objects.prefetch_related("items").order_by("-created_at")

        status = request.query_params.get("status")
        if status in VALID_STATUSES:
            qs = qs.filter(status=status)

        search = request.query_params.get("search", "")
        if search:
            try:
                qs = filter_by_search(
                    qs,
                    search,
                    fields=("code", "full_name", "phone"),
                )
            except SearchQueryTooLong as exc:
                return fail(str(exc), 422)

        page = positive_page(request.query_params.get("page"))
        if page is None:
            return fail("پارامتر صفحه‌بندی نامعتبر است", 422)
        per_page = 15
        total = qs.count()
        rows = qs[(page - 1) * per_page : page * per_page]

        return ok(
            {
                "orders": [order_row(o) for o in rows],
                "total": total,
                "page": page,
                "pages": math.ceil(total / per_page) or 1,
            }
        )


class AdminOrderDetailView(ShopAdminRequiredMixin, APIView):
    def patch(self, request, pk: int):
        status = request.data.get("status")
        if status not in VALID_STATUSES:
            return fail("وضعیت نامعتبر است", 422)

        with transaction.atomic():
            order = (
                Order.objects.select_for_update()
                .prefetch_related("items")
                .filter(pk=pk)
                .first()
            )
            if order is None:
                return fail("سفارش یافت نشد", 404)
            if order.status == Order.Status.CANCELED and status != order.status:
                return fail("سفارش لغوشده قابل بازگشایی نیست", 409)
            if status == Order.Status.CANCELED and order.status != status:
                for item in order.items.all():
                    Product.objects.filter(pk=item.product_id).update(
                        stock=F("stock") + item.qty
                    )
            order.status = status
            order.save(update_fields=["status"])
        return ok({"order": order_row(order)})


# ─── دسته‌بندی‌ها ────────────────────────────────────────────


class CategoryWriteSerializer(serializers.ModelSerializer):
    isActive = serializers.BooleanField(source="is_active", required=False)
    parentIds = serializers.PrimaryKeyRelatedField(
        source="parents",
        queryset=Category.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = Category
        fields = ["title", "slug", "parentIds", "isActive"]

    def validate_parentIds(self, parents):
        category = self.instance
        if category is None:
            return parents
        parent_ids = {parent.pk for parent in parents}
        if category.pk in parent_ids:
            raise serializers.ValidationError(
                "یک دسته‌بندی نمی‌تواند والد خودش باشد"
            )

        descendants = {category.pk}
        frontier = {category.pk}
        while frontier:
            child_ids = set(
                Category.objects.filter(parents__id__in=frontier)
                .exclude(id__in=descendants)
                .distinct()
                .values_list("id", flat=True)
            )
            descendants.update(child_ids)
            frontier = child_ids
        if parent_ids & descendants:
            raise serializers.ValidationError(
                "این رابطه باعث ایجاد چرخه در دسته‌بندی‌ها می‌شود"
            )
        return parents


def admin_category_dto(
    category: Category, *, visible_ids: set[int] | None = None
) -> dict:
    if visible_ids is None:
        visible_ids = visible_category_ids()
    data = category_dto(category)
    data["id"] = category.id
    data["isActive"] = category.is_active
    data["effectiveIsActive"] = category.id in visible_ids
    data["parents"] = [
        {"id": parent.id, **category_summary(parent)}
        for parent in category.parents.all()
    ]
    data["productCount"] = (
        category.product_count
        if hasattr(category, "product_count")
        else category.categorized_products.count()
    )
    return data


class AdminCategoryListView(ShopAdminRequiredMixin, APIView):
    def get(self, request):
        visible_ids = visible_category_ids()
        categories = (
            Category.objects.annotate(
                product_count=Count("categorized_products", distinct=True)
            )
            .prefetch_related("parents", "children")
        )
        return ok(
            {
                "categories": [
                    admin_category_dto(item, visible_ids=visible_ids)
                    for item in categories
                ]
            }
        )

    def post(self, request):
        serializer = CategoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        category = (
            Category.objects.annotate(
                product_count=Count("categorized_products", distinct=True)
            )
            .prefetch_related("parents", "children")
            .get(pk=category.pk)
        )
        return ok({"category": admin_category_dto(category)}, status=201)


class AdminCategoryDetailView(ShopAdminRequiredMixin, APIView):
    def patch(self, request, pk: int):
        category = Category.objects.filter(pk=pk).first()
        if category is None:
            return fail("دسته‌بندی یافت نشد", 404)
        serializer = CategoryWriteSerializer(
            category, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        category = serializer.save()
        category = (
            Category.objects.annotate(
                product_count=Count("categorized_products", distinct=True)
            )
            .prefetch_related("parents", "children")
            .get(pk=category.pk)
        )
        return ok({"category": admin_category_dto(category)})

    def delete(self, request, pk: int):
        category = Category.objects.filter(pk=pk).first()
        if category is None:
            return fail("دسته‌بندی یافت نشد", 404)
        if category.products.exists() or category.categorized_products.exists():
            return fail(
                "این دسته‌بندی دارای محصول است و تا زمان انتقال یا حذف محصولات قابل حذف نیست",
                409,
            )
        if category.children.exists():
            return fail(
                "این دسته‌بندی والد دسته‌های دیگر است؛ ابتدا رابطه والد را تغییر دهید",
                409,
            )
        icon_name = category.icon.name if category.icon else ""
        icon_storage = category.icon.storage if category.icon else None
        using = category._state.db or "default"
        try:
            category.delete()
        except ProtectedError:
            return fail(
                "این دسته‌بندی دارای محصول است و تا زمان انتقال یا حذف محصولات قابل حذف نیست",
                409,
            )
        if icon_name:
            schedule_category_icon_delete(
                icon_name, icon_storage, using=using
            )
        return ok({"deleted": True})


class AdminCategoryIconView(ShopAdminRequiredMixin, APIView):
    def _get(self, pk: int) -> Category | None:
        return Category.objects.filter(pk=pk).first()

    def post(self, request, pk: int):
        category = self._get(pk)
        if category is None:
            return fail("دسته‌بندی یافت نشد", 404)
        icon = request.FILES.get("file")
        if icon is None:
            return fail("فایل آیکن ارسال نشده است", 422)
        try:
            validate_category_icon(icon)
        except DjangoValidationError as exc:
            messages = getattr(exc, "messages", None)
            return fail(messages[0] if messages else "آیکن معتبر نیست", 422)

        old_name = category.icon.name if category.icon else ""
        old_storage = category.icon.storage if category.icon else None
        category.icon = icon
        category.save(update_fields=["icon"])
        if old_name and old_name != category.icon.name:
            schedule_category_icon_delete(
                old_name,
                old_storage,
                using=category._state.db or "default",
            )
        return ok({"category": admin_category_dto(category)}, status=201)

    def delete(self, request, pk: int):
        category = self._get(pk)
        if category is None:
            return fail("دسته‌بندی یافت نشد", 404)
        if not category.icon:
            return ok({"category": admin_category_dto(category)})
        old_name = category.icon.name
        old_storage = category.icon.storage
        category.icon = ""
        category.save(update_fields=["icon"])
        schedule_category_icon_delete(
            old_name,
            old_storage,
            using=category._state.db or "default",
        )
        return ok({"category": admin_category_dto(category)})


# ─── برندها ──────────────────────────────────────────────────


class BrandWriteSerializer(serializers.ModelSerializer):
    isActive = serializers.BooleanField(source="is_active", required=False)

    class Meta:
        model = Brand
        fields = [
            "name",
            "slug",
            "description",
            "website",
            "isActive",
        ]


class AdminBrandListView(ShopAdminRequiredMixin, APIView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        brands = Brand.objects.annotate(product_count=Count("products"))
        return ok({"brands": [admin_brand_dto(brand) for brand in brands]})

    @extend_schema(request=BrandWriteSerializer, responses={201: OpenApiTypes.OBJECT})
    def post(self, request):
        serializer = BrandWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        brand = serializer.save()
        brand = Brand.objects.annotate(product_count=Count("products")).get(
            pk=brand.pk
        )
        return ok({"brand": admin_brand_dto(brand)}, status=201)


class AdminBrandDetailView(ShopAdminRequiredMixin, APIView):
    @extend_schema(request=BrandWriteSerializer, responses={200: OpenApiTypes.OBJECT})
    def patch(self, request, pk: int):
        brand = Brand.objects.filter(pk=pk).first()
        if brand is None:
            return fail("برند یافت نشد", 404)
        serializer = BrandWriteSerializer(brand, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        brand = serializer.save()
        brand = Brand.objects.annotate(product_count=Count("products")).get(
            pk=brand.pk
        )
        return ok({"brand": admin_brand_dto(brand)})

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def delete(self, request, pk: int):
        brand = Brand.objects.filter(pk=pk).first()
        if brand is None:
            return fail("برند یافت نشد", 404)
        if brand.products.exists():
            return fail(
                "این برند دارای محصول است؛ ابتدا برند محصولات را تغییر دهید",
                409,
            )
        logo_name = brand.logo.name if brand.logo else ""
        logo_storage = brand.logo.storage if brand.logo else None
        using = brand._state.db or "default"
        try:
            brand.delete()
        except ProtectedError:
            return fail(
                "این برند دارای محصول است؛ ابتدا برند محصولات را تغییر دهید",
                409,
            )
        if logo_name:
            schedule_brand_logo_delete(logo_name, logo_storage, using=using)
        return ok({"deleted": True})


class BrandLogoUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        help_text="Validated PNG or safe SVG logo, up to 5 MB."
    )


class AdminBrandLogoView(ShopAdminRequiredMixin, APIView):
    def _get(self, pk: int) -> Brand | None:
        return Brand.objects.filter(pk=pk).first()

    @extend_schema(
        request=BrandLogoUploadSerializer,
        responses={201: OpenApiTypes.OBJECT},
    )
    def post(self, request, pk: int):
        brand = self._get(pk)
        if brand is None:
            return fail("برند یافت نشد", 404)
        logo = request.FILES.get("file")
        if logo is None:
            return fail("فایل نشان تجاری ارسال نشده است", 422)
        try:
            validate_category_icon(logo)
        except DjangoValidationError as exc:
            messages = getattr(exc, "messages", None)
            return fail(
                messages[0] if messages else "نشان تجاری معتبر نیست", 422
            )

        old_name = brand.logo.name if brand.logo else ""
        old_storage = brand.logo.storage if brand.logo else None
        brand.logo = logo
        brand.save(update_fields=["logo", "updated_at"])
        if old_name and old_name != brand.logo.name:
            schedule_brand_logo_delete(
                old_name,
                old_storage,
                using=brand._state.db or "default",
            )
        return ok({"brand": admin_brand_dto(brand)}, status=201)

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def delete(self, request, pk: int):
        brand = self._get(pk)
        if brand is None:
            return fail("برند یافت نشد", 404)
        if not brand.logo:
            return ok({"brand": admin_brand_dto(brand)})
        old_name = brand.logo.name
        old_storage = brand.logo.storage
        brand.logo = ""
        brand.save(update_fields=["logo", "updated_at"])
        schedule_brand_logo_delete(
            old_name,
            old_storage,
            using=brand._state.db or "default",
        )
        return ok({"brand": admin_brand_dto(brand)})


class BrandPriceAdjustmentSerializer(serializers.Serializer):
    operation = serializers.ChoiceField(choices=["increase", "decrease"])
    percentage = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=Decimal("1000"),
    )

    def validate(self, data):
        if data["operation"] == "decrease" and data["percentage"] >= 100:
            raise serializers.ValidationError(
                "درصد کاهش باید کمتر از ۱۰۰ باشد"
            )
        return data


class AdminBrandPriceAdjustmentView(ShopAdminRequiredMixin, APIView):
    @extend_schema(
        request=BrandPriceAdjustmentSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request, pk: int):
        brand = Brand.objects.filter(pk=pk).first()
        if brand is None:
            return fail("برند یافت نشد", 404)
        serializer = BrandPriceAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_count = adjust_brand_prices(
            brand=brand,
            operation=serializer.validated_data["operation"],
            percentage=serializer.validated_data["percentage"],
        )
        return ok(
            {
                "brand": {"id": brand.id, "name": brand.name},
                "updatedCount": updated_count,
            }
        )


# ─── محصولات ─────────────────────────────────────────────────


class SpecificationKeyWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, trim_whitespace=False, required=False)
    slug = serializers.SlugField(
        max_length=120, allow_unicode=True, allow_blank=True, required=False
    )

    def validate(self, data):
        instance = self.context.get("instance")
        if not data:
            raise serializers.ValidationError("حداقل یک فیلد را ارسال کنید")
        if instance is None and "name" not in data:
            raise serializers.ValidationError({"name": "نام مشخصه الزامی است"})

        if "name" in data:
            try:
                name, normalized_name = normalize_specification_name(data["name"])
            except ValueError as exc:
                raise serializers.ValidationError({"name": str(exc)}) from exc
            duplicates = SpecificationKey.objects.filter(
                normalized_name=normalized_name
            )
            if instance is not None:
                duplicates = duplicates.exclude(pk=instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    {"name": "مشخصه‌ای با این نام از قبل وجود دارد"}
                )
            data["name"] = name
            data["normalized_name"] = normalized_name

        if "slug" in data and data["slug"]:
            duplicates = SpecificationKey.objects.filter(slug=data["slug"])
            if instance is not None:
                duplicates = duplicates.exclude(pk=instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    {"slug": "مشخصه‌ای با این نامک از قبل وجود دارد"}
                )
        return data


def save_specification_key(
    *, serializer: SpecificationKeyWriteSerializer, instance: SpecificationKey | None = None
) -> SpecificationKey:
    data = dict(serializer.validated_data)
    normalized_name = data.pop("normalized_name", None)
    key = instance or SpecificationKey()
    if "name" in data:
        key.name = data["name"]
        key.normalized_name = normalized_name
    if "slug" in data:
        key.slug = data["slug"]
    try:
        key.save()
    except (DjangoValidationError, IntegrityError) as exc:
        raise serializers.ValidationError(
            "نام یا نامک مشخصه تکراری است"
        ) from exc
    return key


class AdminSpecificationKeyListView(ShopAdminRequiredMixin, APIView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        queryset = specification_keys_queryset()
        search = request.query_params.get("search", "")
        if search:
            try:
                queryset = filter_by_search(
                    queryset,
                    search,
                    fields=("normalized_name", "slug"),
                )
            except SearchQueryTooLong as exc:
                return fail(str(exc), 422)
        raw_limit = request.query_params.get("limit")
        if raw_limit is not None:
            try:
                limit = int(raw_limit)
                if not 1 <= limit <= 100:
                    raise ValueError
            except (TypeError, ValueError):
                return fail("محدوده نتایج نامعتبر است", 422)
            queryset = queryset[:limit]
        return ok(
            {"specifications": [specification_key_dto(key) for key in queryset]}
        )

    @extend_schema(
        request=SpecificationKeyWriteSerializer, responses={201: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = SpecificationKeyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = save_specification_key(serializer=serializer)
        return ok(
            {
                "specification": specification_key_dto(
                    specification_keys_queryset().get(pk=key.pk)
                )
            },
            status=201,
        )


class AdminSpecificationKeyDetailView(ShopAdminRequiredMixin, APIView):
    @extend_schema(
        request=SpecificationKeyWriteSerializer, responses={200: OpenApiTypes.OBJECT}
    )
    def patch(self, request, pk: int):
        key = SpecificationKey.objects.filter(pk=pk).first()
        if key is None:
            return fail("مشخصه یافت نشد", 404)
        serializer = SpecificationKeyWriteSerializer(
            data=request.data, partial=True, context={"instance": key}
        )
        serializer.is_valid(raise_exception=True)
        key = save_specification_key(serializer=serializer, instance=key)
        return ok(
            {
                "specification": specification_key_dto(
                    specification_keys_queryset().get(pk=key.pk)
                )
            }
        )

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def delete(self, request, pk: int):
        key = SpecificationKey.objects.filter(pk=pk).first()
        if key is None:
            return fail("مشخصه یافت نشد", 404)
        error = "این مشخصه در محصولات استفاده شده و قابل حذف نیست"
        if key.product_specifications.exists():
            return fail(error, 409)
        try:
            key.delete()
        except ProtectedError:
            return fail(error, 409)
        return ok({"deleted": True})


class ProductSpecificationWriteSerializer(serializers.Serializer):
    keyId = serializers.IntegerField(min_value=1)
    value = serializers.CharField(max_length=500, trim_whitespace=True)
    position = serializers.IntegerField(
        min_value=0, max_value=MAX_SPECIFICATION_POSITION
    )


class ProductWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    titleEn = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    categorySlug = serializers.CharField(required=False)
    categorySlugs = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=False
    )
    brandSlug = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    price = serializers.IntegerField(min_value=0)
    oldPrice = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    stock = serializers.IntegerField(min_value=0)
    badge = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default=""
    )
    description = serializers.CharField(required=False, allow_blank=True, default="")
    warranty = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    shippingNote = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    returnNote = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    specifications = ProductSpecificationWriteSerializer(
        many=True, required=False, allow_empty=True, max_length=100
    )
    recommendedProductIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
        max_length=3,
    )

    def validate(self, data):
        recommendation_ids = data.pop("recommendedProductIds", None)
        if recommendation_ids is not None and len(recommendation_ids) != len(
            set(recommendation_ids)
        ):
            raise serializers.ValidationError(
                {"recommendedProductIds": "محصول پیشنهادی تکراری مجاز نیست"}
            )
        data["recommendation_ids"] = recommendation_ids
        raw_specifications = data.pop("specifications", None)
        data["specification_items"] = (
            validate_specification_inputs(raw_specifications)
            if raw_specifications is not None
            else None
        )
        slugs = data.pop("categorySlugs", None)
        legacy_slug = data.pop("categorySlug", None)
        if slugs is None:
            slugs = [legacy_slug] if legacy_slug else []
        slugs = list(dict.fromkeys(slugs))
        if not slugs:
            raise serializers.ValidationError("حداقل یک دسته‌بندی انتخاب کنید")
        categories_by_slug = {
            category.slug: category
            for category in Category.objects.filter(slug__in=slugs)
        }
        if len(categories_by_slug) != len(slugs):
            raise serializers.ValidationError("یک یا چند دسته‌بندی یافت نشد")
        data["categories"] = [categories_by_slug[slug] for slug in slugs]

        brand_slug = data.pop("brandSlug", None)
        if brand_slug:
            brand = Brand.objects.filter(slug=brand_slug).first()
            if brand is None:
                raise serializers.ValidationError("برند یافت نشد")
            data["brand"] = brand
        else:
            data["brand"] = None

        old_price = data.get("oldPrice")
        if old_price is not None and old_price <= data["price"]:
            raise serializers.ValidationError(
                "قیمت قبل باید بیشتر از قیمت فروش باشد"
            )
        return data


class AdminProductListView(ShopAdminRequiredMixin, APIView):
    def get(self, request):
        qs = (
            Product.objects.select_related("category", "brand")
            .prefetch_related("categories", "images")
            .order_by("-created_at")
        )
        search = request.query_params.get("search", "")
        if search:
            try:
                qs = filter_by_search(
                    qs,
                    search,
                    fields=(
                        "title",
                        "title_en",
                        "brand__name",
                        "category__title",
                        "categories__title",
                    ),
                    include_pk=True,
                ).distinct()
            except SearchQueryTooLong as exc:
                return fail(str(exc), 422)

        page = positive_page(request.query_params.get("page"))
        if page is None:
            return fail("پارامتر صفحه‌بندی نامعتبر است", 422)
        per_page = 15
        total = qs.count()
        rows = qs[(page - 1) * per_page : page * per_page]

        return ok(
            {
                "products": [product_dto(p) for p in rows],
                "total": total,
                "page": page,
                "pages": math.ceil(total / per_page) or 1,
            }
        )

    def post(self, request):
        ser = ProductWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = dict(ser.validated_data)
        specification_items = data.pop("specification_items")
        recommendation_ids = data.pop("recommendation_ids")
        try:
            with transaction.atomic():
                product = save_product_with_specifications(
                    product=Product(),
                    data=data,
                    specification_items=specification_items,
                )
                replace_product_recommendations(product, recommendation_ids or [])
        except RecommendationValidationError as exc:
            return fail(str(exc), 422)
        product = (
            Product.objects.select_related("category", "brand")
            .prefetch_related(
                "categories",
                "images",
                product_specification_prefetch(),
                product_recommendation_prefetch(),
            )
            .get(pk=product.pk)
        )
        return ok(
            {"product": admin_created_product_dto(product)}, status=201
        )


class AdminProductDetailView(ShopAdminRequiredMixin, APIView):
    def _get(self, pk: int) -> Product | None:
        return (
            Product.objects.select_related("category", "brand")
            .prefetch_related(
                "categories",
                "images",
                product_specification_prefetch(),
                product_recommendation_prefetch(),
            )
            .filter(pk=pk)
            .first()
        )

    def get(self, request, pk: int):
        product = self._get(pk)
        if product is None:
            return fail("محصول یافت نشد", 404)
        return ok({"product": admin_product_dto(product)})

    def patch(self, request, pk: int):
        product = self._get(pk)
        if product is None:
            return fail("محصول یافت نشد", 404)
        ser = ProductWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = dict(ser.validated_data)
        specification_items = data.pop("specification_items")
        recommendation_ids = data.pop("recommendation_ids")
        try:
            with transaction.atomic():
                product = save_product_with_specifications(
                    product=product,
                    data=data,
                    specification_items=specification_items,
                )
                if recommendation_ids is not None:
                    replace_product_recommendations(product, recommendation_ids)
        except RecommendationValidationError as exc:
            return fail(str(exc), 422)
        return ok({"product": admin_product_dto(self._get(pk))})

    def delete(self, request, pk: int):
        product = self._get(pk)
        if product is None:
            return fail("محصول یافت نشد", 404)
        if product.order_items.exists():
            # محصول دارای سابقه‌ی سفارش حذف نمی‌شود؛ ناموجودش کنید
            return fail(
                "این محصول در سفارش‌ها استفاده شده و قابل حذف نیست؛ موجودی را صفر کنید",
                409,
            )
        for img in product.images.all():
            img.image.delete(save=False)
        product.delete()
        return ok({"deleted": True})


class ProductVisibilitySerializer(serializers.Serializer):
    isActive = serializers.BooleanField()


class AdminProductVisibilityView(ShopAdminRequiredMixin, APIView):
    def patch(self, request, pk: int):
        serializer = ProductVisibilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = (
            Product.objects.select_related("category", "brand")
            .prefetch_related(
                "categories",
                "images",
                product_specification_prefetch(),
                product_recommendation_prefetch(),
            )
            .filter(pk=pk)
            .first()
        )
        if product is None:
            return fail("محصول یافت نشد", 404)
        product.is_active = serializer.validated_data["isActive"]
        product.save(update_fields=["is_active"])
        return ok({"product": admin_product_dto(product)})


class ProductBestSellerSerializer(serializers.Serializer):
    isBestSeller = serializers.BooleanField()
    position = serializers.IntegerField(min_value=0, required=False)


class AdminProductBestSellerView(ShopAdminRequiredMixin, APIView):
    """انتخاب/حذف دستی محصول از بخش «پرفروش‌ترین‌ها» — مستقل از آمار فروش واقعی"""

    def patch(self, request, pk: int):
        serializer = ProductBestSellerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = (
            Product.objects.select_related("category", "brand")
            .prefetch_related(
                "categories",
                "images",
                product_specification_prefetch(),
                product_recommendation_prefetch(),
            )
            .filter(pk=pk)
            .first()
        )
        if product is None:
            return fail("محصول یافت نشد", 404)
        product.is_best_seller = serializer.validated_data["isBestSeller"]
        update_fields = ["is_best_seller"]
        if "position" in serializer.validated_data:
            product.best_seller_position = serializer.validated_data["position"]
            update_fields.append("best_seller_position")
        product.save(update_fields=update_fields)
        return ok({"product": admin_product_dto(product)})


class ProductIncredibleSerializer(serializers.Serializer):
    isIncredible = serializers.BooleanField()
    position = serializers.IntegerField(min_value=0, required=False)


class AdminProductIncredibleView(ShopAdminRequiredMixin, APIView):
    """انتخاب/حذف دستی محصول از بخش «شگفت‌انگیزها» — مستقل از داشتن تخفیف"""

    def patch(self, request, pk: int):
        serializer = ProductIncredibleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = (
            Product.objects.select_related("category", "brand")
            .prefetch_related(
                "categories",
                "images",
                product_specification_prefetch(),
                product_recommendation_prefetch(),
            )
            .filter(pk=pk)
            .first()
        )
        if product is None:
            return fail("محصول یافت نشد", 404)
        product.is_incredible = serializer.validated_data["isIncredible"]
        update_fields = ["is_incredible"]
        if "position" in serializer.validated_data:
            product.incredible_position = serializer.validated_data["position"]
            update_fields.append("incredible_position")
        product.save(update_fields=update_fields)
        return ok({"product": admin_product_dto(product)})


class AdminProductImageView(ShopAdminRequiredMixin, APIView):
    """آپلود تصویر محصول (multipart/form-data با فیلد file)"""

    def post(self, request, pk: int):
        product = Product.objects.filter(pk=pk).first()
        if product is None:
            return fail("محصول یافت نشد", 404)
        file = request.FILES.get("file")
        if file is None:
            return fail("فایل تصویر ارسال نشده است", 422)
        if file.size > 5 * 1024 * 1024:
            return fail("حجم تصویر حداکثر ۵ مگابایت باشد", 422)
        try:
            image = Image.open(file)
            image.verify()
            file.seek(0)
        except (UnidentifiedImageError, OSError):
            return fail("فایل ارسال‌شده تصویر معتبر نیست", 422)
        order = (product.images.count() or 0)
        ProductImage.objects.create(
            product=product, image=file, alt=product.title, order=order
        )
        return ok(
            {
                "product": admin_product_dto(
                    Product.objects.select_related("category", "brand")
                    .prefetch_related(
                        "categories",
                        "images",
                        product_specification_prefetch(),
                        product_recommendation_prefetch(),
                    )
                    .get(pk=pk)
                )
            },
            status=201,
        )


class AdminProductImageDetailView(ShopAdminRequiredMixin, APIView):
    def delete(self, request, pk: int, image_id: int):
        img = ProductImage.objects.filter(pk=image_id, product_id=pk).first()
        if img is None:
            return fail("تصویر یافت نشد", 404)
        img.image.delete(save=False)
        img.delete()
        return ok({"deleted": True})


# ─── کاربران ─────────────────────────────────────────────────


class AdminUserListView(ShopAdminRequiredMixin, APIView):
    def get(self, request):
        qs = User.objects.annotate(orders_count=Count("orders")).order_by(
            "-date_joined"
        )
        # مدیر اجرایی فقط مشتری‌ها را می‌بیند؛ حساب‌های مدیریتی (سوپریوزر،
        # مدیر اجرایی، کارمند و مدیر سئو) از دید او پنهان می‌مانند.
        if is_manager_admin(request.user):
            qs = qs.filter(
                is_staff=False,
                is_superuser=False,
                is_manager_admin=False,
                is_seo_manager=False,
            )
        search = request.query_params.get("search", "")
        if search:
            try:
                qs = filter_by_search(qs, search, fields=("phone", "name"))
            except SearchQueryTooLong as exc:
                return fail(str(exc), 422)

        page = positive_page(request.query_params.get("page"))
        if page is None:
            return fail("پارامتر صفحه‌بندی نامعتبر است", 422)
        per_page = 15
        total = qs.count()
        rows = qs[(page - 1) * per_page : page * per_page]

        return ok(
            {
                "users": [
                    {
                        "id": u.id,
                        "phone": u.phone,
                        "name": u.name or None,
                        "isStaff": u.is_staff,
                        "isManagerAdmin": u.is_manager_admin,
                        "isSeoManager": u.is_seo_manager,
                        "isSuperuser": u.is_superuser,
                        "isActive": u.is_active,
                        "dateJoined": u.date_joined.isoformat(),
                        "ordersCount": u.orders_count,
                    }
                    for u in rows
                ],
                "total": total,
                "page": page,
                "pages": math.ceil(total / per_page) or 1,
            }
        )


# ─── دیدگاه‌ها ───────────────────────────────────────────────


def admin_comment_row(
    comment: ProductComment,
    verified_pairs: set[tuple[int, int]] | None = None,
) -> dict:
    return {
        "id": comment.id,
        "content": comment.content,
        "type": comment.comment_type,
        "status": comment.moderation_status,
        "parentId": comment.parent_id,
        "createdAt": comment.created_at.isoformat(),
        "updatedAt": comment.updated_at.isoformat(),
        "author": comment.user.name or comment.user.phone,
        "productId": comment.product_id,
        "productTitle": comment.product.title,
        "isAdminResponse": bool(comment.user.is_staff),
        "isVerifiedPurchase": (comment.product_id, comment.user_id)
        in (verified_pairs or set()),
    }


class AdminCommentListView(ShopAdminRequiredMixin, APIView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        qs = ProductComment.objects.select_related("user", "product").order_by(
            "-created_at"
        )
        moderation_status = request.query_params.get("status")
        if moderation_status:
            valid_statuses = {
                value for value, _ in ProductComment.ModerationStatus.choices
            }
            if moderation_status not in valid_statuses:
                return fail("وضعیت بررسی نامعتبر است", 422)
            qs = qs.filter(moderation_status=moderation_status)

        page = positive_page(request.query_params.get("page"))
        if page is None:
            return fail("پارامتر صفحه‌بندی نامعتبر است", 422)
        per_page = 15
        total = qs.count()
        rows = list(qs[(page - 1) * per_page : page * per_page])
        verified_pairs = verified_purchase_pairs(
            {(comment.product_id, comment.user_id) for comment in rows}
        )

        return ok(
            {
                "comments": [
                    admin_comment_row(comment, verified_pairs) for comment in rows
                ],
                "total": total,
                "page": page,
                "pages": math.ceil(total / per_page) or 1,
            }
        )


class CommentModerationSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=ProductComment.ModerationStatus.choices
    )


class AdminCommentDetailView(ShopAdminRequiredMixin, APIView):
    @extend_schema(
        request=CommentModerationSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    def patch(self, request, pk: int):
        comment = ProductComment.objects.select_related("user", "product").filter(
            pk=pk
        ).first()
        if comment is None:
            return fail("دیدگاه یافت نشد", 404)

        serializer = CommentModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment.moderation_status = serializer.validated_data["status"]
        comment.save(update_fields=["moderation_status", "updated_at"])
        verified_pairs = verified_purchase_pairs(
            {(comment.product_id, comment.user_id)}
        )
        return ok({"comment": admin_comment_row(comment, verified_pairs)})

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def delete(self, request, pk: int):
        comment = ProductComment.objects.filter(pk=pk).first()
        if comment is None:
            return fail("دیدگاه یافت نشد", 404)
        comment.delete()
        return ok({"deleted": True})


class AdminResponseSerializer(serializers.Serializer):
    content = serializers.CharField(min_length=2, max_length=2000)


class AdminCommentResponseView(ShopAdminRequiredMixin, APIView):
    @extend_schema(
        request=AdminResponseSerializer,
        responses={201: OpenApiTypes.OBJECT},
    )
    def post(self, request, pk: int):
        parent = ProductComment.objects.select_related("product").filter(
            pk=pk,
            moderation_status=ProductComment.ModerationStatus.APPROVED,
        ).first()
        if parent is None:
            return fail("دیدگاه تاییدشده یافت نشد", 404)

        serializer = AdminResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = ProductComment.objects.create(
            product=parent.product,
            user=request.user,
            parent=parent,
            content=serializer.validated_data["content"].strip(),
            comment_type=parent.comment_type,
            moderation_status=ProductComment.ModerationStatus.APPROVED,
        )
        response = ProductComment.objects.select_related("user", "product").get(
            pk=response.pk
        )
        verified_pairs = verified_purchase_pairs(
            {(response.product_id, response.user_id)}
        )
        return ok(
            {"comment": admin_comment_row(response, verified_pairs)}, status=201
        )
