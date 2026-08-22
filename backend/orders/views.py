import logging
import secrets

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.utils.cache import patch_vary_headers
from django.utils.http import content_disposition_header
from rest_framework import serializers
from rest_framework.views import APIView

from accounts.models import Address
from carts.services import get_current_cart
from catalog.models import Product
from common.responses import fail, ok
from common.utils import normalize_phone

from .invoice import render_invoice_pdf
from .models import Order, OrderItem

SHOP = settings.SHOP
logger = logging.getLogger(__name__)


class OutOfStock(Exception):
    """موجودی کافی نیست — پیام برای کاربر قابل نمایش است"""


def new_order_code() -> str:
    """کد غیرقابل‌حدس؛ یکتایی نهایی با قید دیتابیس تضمین می‌شود."""
    return f"GS-{secrets.token_hex(6).upper()}"


class CreateOrderSerializer(serializers.Serializer):
    # در صورت ارسال، اطلاعات از دفترچه آدرس کاربر خوانده می‌شود
    addressId = serializers.IntegerField(required=False, allow_null=True)
    fullName = serializers.CharField(
        min_length=3,
        required=False,
        error_messages={
            "required": "نام تحویل‌گیرنده الزامی است",
            "min_length": "نام تحویل‌گیرنده حداقل ۳ حرف باشد",
        },
    )
    province = serializers.CharField(
        min_length=2,
        required=False,
        error_messages={"required": "استان الزامی است"},
    )
    city = serializers.CharField(
        min_length=2,
        required=False,
        error_messages={"required": "شهر الزامی است"},
    )
    address = serializers.CharField(
        min_length=10,
        required=False,
        error_messages={
            "required": "آدرس الزامی است",
            "min_length": "آدرس کامل‌تری وارد کنید",
        },
    )
    postalCode = serializers.CharField(required=False, allow_blank=True)

    def validate_postalCode(self, value):
        value = normalize_phone(value)
        if value and (not value.isdigit() or len(value) != 10):
            raise serializers.ValidationError("کد پستی باید ۱۰ رقم باشد")
        return value

    def validate(self, data):
        # اگر آدرس ذخیره‌شده انتخاب نشده، فیلدهای آدرس الزامی‌اند
        if not data.get("addressId"):
            missing = [
                label
                for field, label in (
                    ("fullName", "نام تحویل‌گیرنده"),
                    ("province", "استان"),
                    ("city", "شهر"),
                    ("address", "آدرس"),
                )
                if not data.get(field)
            ]
            if missing:
                raise serializers.ValidationError(f"{missing[0]} الزامی است")
        return data


def order_dto(order: Order) -> dict:
    return {
        "id": order.id,
        "code": order.code,
        "status": order.status,
        "statusLabel": order.get_status_display(),
        "createdAt": order.created_at.isoformat(),
        "fullName": order.full_name,
        "phone": order.phone,
        "province": order.province,
        "city": order.city,
        "address": order.address,
        "postalCode": order.postal_code,
        "itemsPrice": order.items_price,
        "discount": order.discount,
        "shippingPrice": order.shipping_price,
        "totalPrice": order.total_price,
        "canCancel": order.status == Order.Status.PENDING,
        "items": [
            {
                "id": i.id,
                "title": i.title,
                "price": i.price,
                "oldPrice": i.old_price,
                "qty": i.qty,
                "productId": i.product_id,
            }
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

        # آدرس ذخیره‌شده کاربر جایگزین فیلدهای دستی می‌شود
        if info.get("addressId"):
            addr = Address.objects.filter(
                pk=info["addressId"], user=request.user
            ).first()
            if addr is None:
                return fail("آدرس انتخاب‌شده یافت نشد", 404)
            info = {
                **info,
                "fullName": addr.full_name,
                "province": addr.province,
                "city": addr.city,
                "address": addr.address,
                "postalCode": addr.postal_code,
            }

        cart = get_current_cart(request)
        if cart is None or not cart.items.exists():
            return fail("سبد خرید شما خالی است", 409)

        items = list(cart.items.select_related("product"))
        hidden_product = next(
            (item.product for item in items if not item.product.is_active), None
        )
        if hidden_product is not None:
            return fail(
                f"محصول «{hidden_product.title}» دیگر قابل سفارش نیست؛ آن را از سبد حذف کنید",
                409,
            )

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
                    code=new_order_code(),
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


class OrderDetailView(APIView):
    """جزئیات یک سفارش کاربر + لغو سفارش در انتظار پرداخت"""

    def get(self, request, pk: int):
        if not request.user.is_authenticated:
            return fail("ابتدا وارد شوید", 401)
        order = (
            Order.objects.filter(pk=pk, user=request.user)
            .prefetch_related("items")
            .first()
        )
        if order is None:
            return fail("سفارش یافت نشد", 404)
        return ok({"order": order_dto(order)})

    def post(self, request, pk: int):
        """لغو سفارش — موجودی کالاها برگردانده می‌شود"""
        if not request.user.is_authenticated:
            return fail("ابتدا وارد شوید", 401)
        with transaction.atomic():
            order = (
                Order.objects.select_for_update()
                .filter(pk=pk, user=request.user)
                .prefetch_related("items")
                .first()
            )
            if order is None:
                return fail("سفارش یافت نشد", 404)
            if order.status != Order.Status.PENDING:
                return fail("فقط سفارش در انتظار پرداخت قابل لغو است", 409)
            for item in order.items.all():
                Product.objects.filter(pk=item.product_id).update(
                    stock=F("stock") + item.qty
                )
            order.status = Order.Status.CANCELED
            order.save(update_fields=["status"])

        return ok({"order": order_dto(order)})


class OrderInvoiceView(APIView):
    """Download a snapshot-backed invoice for its owner or a staff user."""

    def get(self, request, pk: int):
        if not request.user.is_authenticated:
            return fail("ابتدا وارد شوید", 401)

        orders = Order.objects.filter(pk=pk).prefetch_related("items")
        if not request.user.is_staff:
            orders = orders.filter(user=request.user)
        order = orders.first()
        if order is None:
            # The same response for absent and foreign orders avoids disclosing IDs.
            return fail("سفارش یافت نشد", 404)

        try:
            pdf = render_invoice_pdf(order)
        except Exception:
            logger.exception("Could not render invoice for order %s", order.pk)
            return fail("ساخت فایل فاکتور ممکن نشد", 500)

        filename = f"invoice-{order.invoice_number}.pdf"
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = content_disposition_header(
            as_attachment=True,
            filename=filename,
        )
        response["Content-Length"] = len(pdf)
        response["Cache-Control"] = "private, no-store"
        response["Pragma"] = "no-cache"
        patch_vary_headers(response, ["Cookie"])
        return response
