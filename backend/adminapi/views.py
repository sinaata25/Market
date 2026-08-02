"""API های داشبورد مدیریت — فقط برای کاربران is_staff"""

import math
from datetime import timedelta

from PIL import Image, UnidentifiedImageError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Avg, Count, F, IntegerField, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView

from catalog.dto import product_dto
from catalog.models import Category, Product, ProductImage, Review
from common.responses import fail, ok
from orders.models import Order, OrderItem

User = get_user_model()

VALID_STATUSES = [s for s, _ in Order.Status.choices]


def positive_page(value) -> int | None:
    try:
        return max(1, int(value or 1))
    except (TypeError, ValueError):
        return None


class IsStaff(BasePermission):
    """فقط کاربران staff — خطا با قالب یکسان {ok:false, error} برمی‌گردد"""

    message = "دسترسی مدیریتی ندارید"

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )


class StaffRequiredMixin:
    """پیش‌شرط همه‌ی ویوهای ادمین: ورود + دسترسی staff"""

    permission_classes = [IsStaff]


def admin_product_dto(product: Product) -> dict:
    """DTO محصول برای ادمین + شناسه تصاویر (برای حذف)"""
    data = product_dto(product)
    data["imageItems"] = [
        {"id": img.id, "url": img.image.url} for img in product.images.all()
    ]
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


class StatsView(StaffRequiredMixin, APIView):
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
                    "reviews": Review.objects.count(),
                    "avgRating": round(
                        Review.objects.aggregate(a=Avg("rating"))["a"] or 0, 1
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


class AdminOrderListView(StaffRequiredMixin, APIView):
    def get(self, request):
        qs = Order.objects.prefetch_related("items").order_by("-created_at")

        status = request.query_params.get("status")
        if status in VALID_STATUSES:
            qs = qs.filter(status=status)

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(code__icontains=search)
                | Q(full_name__icontains=search)
                | Q(phone__icontains=search)
            )

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


class AdminOrderDetailView(StaffRequiredMixin, APIView):
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


# ─── محصولات ─────────────────────────────────────────────────


class ProductWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    titleEn = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    categorySlug = serializers.CharField()
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

    def validate_categorySlug(self, value):
        try:
            return Category.objects.get(slug=value)
        except Category.DoesNotExist:
            raise serializers.ValidationError("دسته‌بندی یافت نشد")

    def validate(self, data):
        old_price = data.get("oldPrice")
        if old_price is not None and old_price <= data["price"]:
            raise serializers.ValidationError(
                "قیمت قبل باید بیشتر از قیمت فروش باشد"
            )
        return data


def apply_product_data(product: Product, data: dict) -> Product:
    product.title = data["title"]
    product.title_en = data.get("titleEn", "")
    product.category = data["categorySlug"]
    product.price = data["price"]
    product.old_price = data.get("oldPrice")
    product.stock = data["stock"]
    product.badge = data.get("badge", "")
    product.description = data.get("description", "")
    product.warranty = data.get("warranty", "")
    product.save()
    return product


class AdminProductListView(StaffRequiredMixin, APIView):
    def get(self, request):
        qs = (
            Product.objects.select_related("category")
            .prefetch_related("images")
            .order_by("-created_at")
        )
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(title__icontains=search)

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
        product = apply_product_data(Product(), ser.validated_data)
        return ok({"product": product_dto(product)}, status=201)


class AdminProductDetailView(StaffRequiredMixin, APIView):
    def _get(self, pk: int) -> Product | None:
        return (
            Product.objects.select_related("category")
            .prefetch_related("images")
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
        apply_product_data(product, ser.validated_data)
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


class AdminProductImageView(StaffRequiredMixin, APIView):
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
        return ok({"product": admin_product_dto(Product.objects.select_related("category").prefetch_related("images").get(pk=pk))}, status=201)


class AdminProductImageDetailView(StaffRequiredMixin, APIView):
    def delete(self, request, pk: int, image_id: int):
        img = ProductImage.objects.filter(pk=image_id, product_id=pk).first()
        if img is None:
            return fail("تصویر یافت نشد", 404)
        img.image.delete(save=False)
        img.delete()
        return ok({"deleted": True})


# ─── کاربران ─────────────────────────────────────────────────


class AdminUserListView(StaffRequiredMixin, APIView):
    def get(self, request):
        qs = User.objects.annotate(orders_count=Count("orders")).order_by(
            "-date_joined"
        )
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(phone__icontains=search) | Q(name__icontains=search)
            )

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


def recompute_rating(product_id: int):
    agg = Review.objects.filter(product_id=product_id).aggregate(
        avg=Avg("rating"), count=Count("id")
    )
    Product.objects.filter(pk=product_id).update(
        rating=round(agg["avg"] or 0, 1), rating_count=agg["count"]
    )


class AdminReviewListView(StaffRequiredMixin, APIView):
    def get(self, request):
        qs = Review.objects.select_related("user", "product").order_by("-created_at")

        page = positive_page(request.query_params.get("page"))
        if page is None:
            return fail("پارامتر صفحه‌بندی نامعتبر است", 422)
        per_page = 15
        total = qs.count()
        rows = qs[(page - 1) * per_page : page * per_page]

        return ok(
            {
                "reviews": [
                    {
                        "id": r.id,
                        "rating": r.rating,
                        "text": r.text,
                        "createdAt": r.created_at.isoformat(),
                        "author": r.user.name or r.user.phone,
                        "productId": r.product_id,
                        "productTitle": r.product.title,
                    }
                    for r in rows
                ],
                "total": total,
                "page": page,
                "pages": math.ceil(total / per_page) or 1,
            }
        )


class AdminReviewDetailView(StaffRequiredMixin, APIView):
    def delete(self, request, pk: int):
        review = Review.objects.filter(pk=pk).first()
        if review is None:
            return fail("دیدگاه یافت نشد", 404)
        product_id = review.product_id
        review.delete()
        recompute_rating(product_id)
        return ok({"deleted": True})
