from django.conf import settings
from django.db import transaction
from rest_framework import serializers
from rest_framework.views import APIView

from carts.services import get_current_cart
from catalog.models import Product
from common.responses import fail, ok

from .models import Order, OrderItem

SHOP = settings.SHOP


class OutOfStock(Exception):
    """موجودی کافی نیست — پیام برای کاربر قابل نمایش است"""


class CreateOrderSerializer(serializers.Serializer):
    fullName = serializers.CharField(
        min_length=3,
        error_messages={
            "required": "نام تحویل‌گیرنده الزامی است",
            "min_length": "نام تحویل‌گیرنده حداقل ۳ حرف باشد",
        },
    )
    province = serializers.CharField(
        min_length=2, error_messages={"required": "استان الزامی است"}
    )
    city = serializers.CharField(
        min_length=2, error_messages={"required": "شهر الزامی است"}
    )
    address = serializers.CharField(
        min_length=10,
        error_messages={
            "required": "آدرس الزامی است",
            "min_length": "آدرس کامل‌تری وارد کنید",
        },
    )
    postalCode = serializers.CharField(required=False, allow_blank=True)


def order_dto(order: Order) -> dict:
    return {
        "id": order.id,
        "code": order.code,
        "status": order.status,
        "createdAt": order.created_at.isoformat(),
        "fullName": order.full_name,
        "province": order.province,
        "city": order.city,
        "itemsPrice": order.items_price,
        "discount": order.discount,
        "shippingPrice": order.shipping_price,
        "totalPrice": order.total_price,
        "items": [
            {"id": i.id, "title": i.title, "price": i.price, "qty": i.qty}
            for i in order.items.all()
        ],
    }


class OrderListCreateView(APIView):
    """ثبت سفارش از روی سبد جاری / فهرست سفارش‌های کاربر"""

    def get(self, request):
        if not request.user.is_authenticated:
            return fail("ابتدا وارد شوید", 401)
        orders = Order.objects.filter(user=request.user).prefetch_related("items")
        return ok({"orders": [order_dto(o) for o in orders]})

    def post(self, request):
        if not request.user.is_authenticated:
            return fail("برای ثبت سفارش ابتدا وارد شوید", 401)

        ser = CreateOrderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        info = ser.validated_data

        cart = get_current_cart(request)
        if cart is None or not cart.items.exists():
            return fail("سبد خرید شما خالی است", 409)

        items = list(cart.items.select_related("product"))

        # محاسبه مبالغ
        items_price = sum(
            (i.product.old_price or i.product.price) * i.qty for i in items
        )
        payable = sum(i.product.price * i.qty for i in items)
        discount = items_price - payable
        shipping_price = (
            0 if payable >= SHOP["FREE_SHIPPING_THRESHOLD"] else SHOP["SHIPPING_PRICE"]
        )
        total_price = payable + shipping_price

        try:
            with transaction.atomic():
                # قفل ردیف‌های محصول، بررسی و کاهش موجودی
                product_ids = [i.product_id for i in items]
                locked = {
                    p.id: p
                    for p in Product.objects.select_for_update().filter(
                        id__in=product_ids
                    )
                }
                for item in items:
                    product = locked[item.product_id]
                    if product.stock < item.qty:
                        raise OutOfStock(f"موجودی «{product.title}» کافی نیست")
                    product.stock -= item.qty
                    product.save(update_fields=["stock"])

                order = Order.objects.create(
                    code=f"GS-{10001 + Order.objects.count()}",
                    user=request.user,
                    full_name=info["fullName"],
                    phone=request.user.phone,
                    province=info["province"],
                    city=info["city"],
                    address=info["address"],
                    postal_code=info.get("postalCode", ""),
                    items_price=items_price,
                    discount=discount,
                    shipping_price=shipping_price,
                    total_price=total_price,
                )
                OrderItem.objects.bulk_create(
                    OrderItem(
                        order=order,
                        product_id=i.product_id,
                        title=i.product.title,
                        price=i.product.price,
                        old_price=i.product.old_price,
                        qty=i.qty,
                    )
                    for i in items
                )

                # سبد خالی می‌شود
                cart.items.all().delete()
        except OutOfStock as e:
            return fail(str(e), 409)

        return ok(
            {"order": {"code": order.code, "totalPrice": order.total_price}},
            status=201,
        )
