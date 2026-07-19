from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import serializers
from rest_framework.views import APIView

from catalog.models import Product
from common.responses import fail, ok

from .services import cart_dto, get_current_cart, get_or_create_cart


@method_decorator(ensure_csrf_cookie, name="get")
class CartView(APIView):
    """سبد خرید جاری (مهمان یا کاربر)"""

    def get(self, request):
        return ok({"cart": cart_dto(get_current_cart(request))})


class AddItemSerializer(serializers.Serializer):
    productId = serializers.IntegerField(
        error_messages={"required": "شناسه محصول الزامی است"}
    )
    qty = serializers.IntegerField(min_value=1, max_value=99, default=1)


class CartItemsView(APIView):
    """افزودن کالا به سبد (اگر بود، تعدادش زیاد می‌شود)"""

    def post(self, request):
        ser = AddItemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        product_id = ser.validated_data["productId"]
        qty = ser.validated_data["qty"]

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return fail("محصول یافت نشد", 404)
        if product.stock < 1:
            return fail("موجودی این کالا تمام شده است", 409)

        cart = get_or_create_cart(request)
        existing = cart.items.filter(product=product).first()
        new_qty = (existing.qty if existing else 0) + qty

        if new_qty > product.stock:
            return fail(f"حداکثر موجودی این کالا {product.stock} عدد است", 409)

        if existing:
            existing.qty = new_qty
            existing.save(update_fields=["qty"])
        else:
            cart.items.create(product=product, qty=qty)

        return ok({"cart": cart_dto(get_current_cart(request))}, status=201)


class QtySerializer(serializers.Serializer):
    qty = serializers.IntegerField(
        min_value=1, max_value=99, error_messages={"required": "تعداد الزامی است"}
    )


class CartItemDetailView(APIView):
    """تغییر تعداد یا حذف یک قلم — فقط اقلام سبد جاری"""

    def _find_item(self, request, item_id: int):
        cart = get_current_cart(request)
        if cart is None:
            return None
        return cart.items.filter(pk=item_id).select_related("product").first()

    def patch(self, request, pk: int):
        item = self._find_item(request, pk)
        if item is None:
            return fail("قلم سبد یافت نشد", 404)

        ser = QtySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        qty = ser.validated_data["qty"]

        if qty > item.product.stock:
            return fail(f"حداکثر موجودی این کالا {item.product.stock} عدد است", 409)

        item.qty = qty
        item.save(update_fields=["qty"])
        return ok({"cart": cart_dto(get_current_cart(request))})

    def delete(self, request, pk: int):
        item = self._find_item(request, pk)
        if item is None:
            return fail("قلم سبد یافت نشد", 404)
        item.delete()
        return ok({"cart": cart_dto(get_current_cart(request))})
