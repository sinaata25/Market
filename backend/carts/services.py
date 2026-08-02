"""منطق سبد خرید: سبد مهمان در سشن، سبد کاربر، و ادغام پس از ورود"""

from django.db import transaction

from catalog.dto import product_dto

from .models import Cart, CartItem

SESSION_KEY = "cart_token"


def get_current_cart(request) -> Cart | None:
    """سبد جاری: اول سبد کاربر لاگین‌شده، بعد سبد مهمان از سشن"""
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            return cart

    token = request.session.get(SESSION_KEY)
    if not token:
        return None
    cart = Cart.objects.filter(token=token).first()
    # سبد مهمانی که متعلق به کاربر دیگری است داده نشود
    if cart and cart.user is not None:
        if not request.user.is_authenticated or cart.user_id != request.user.id:
            return None
    return cart


def get_or_create_cart(request) -> Cart:
    """سبد جاری را برمی‌گرداند یا می‌سازد (و توکن مهمان را در سشن می‌گذارد)"""
    cart = get_current_cart(request)
    if cart:
        return cart

    user = request.user if request.user.is_authenticated else None
    cart = Cart.objects.create(user=user)
    request.session[SESSION_KEY] = str(cart.token)
    return cart


@transaction.atomic
def merge_guest_cart_into_user(request, user) -> None:
    """پس از ورود، سبد مهمان به حساب کاربر منتقل/ادغام می‌شود"""
    token = request.session.get(SESSION_KEY)
    if not token:
        return

    # Serialize merges for one account (including two different guest carts),
    # then lock the cart rows before changing their one-to-one ownership/items.
    type(user).objects.select_for_update().get(pk=user.pk)
    guest_cart = Cart.objects.select_for_update().filter(token=token).first()
    if guest_cart is None or guest_cart.user_id == user.id:
        return
    if guest_cart.user_id is not None:
        # متعلق به کاربر دیگری است
        request.session.pop(SESSION_KEY, None)
        return

    user_cart = Cart.objects.select_for_update().filter(user=user).first()
    if user_cart is None:
        # سبد مهمان به کاربر داده می‌شود
        guest_cart.user = user
        guest_cart.save(update_fields=["user"])
        request.session[SESSION_KEY] = str(guest_cart.token)
        return

    # ادغام اقلام سبد مهمان در سبد کاربر
    for item in guest_cart.items.select_for_update().all():
        existing = (
            user_cart.items.select_for_update()
            .filter(product_id=item.product_id)
            .first()
        )
        if existing:
            existing.qty += item.qty
            existing.save(update_fields=["qty"])
        else:
            CartItem.objects.create(
                cart=user_cart, product_id=item.product_id, qty=item.qty
            )
    guest_cart.delete()
    request.session[SESSION_KEY] = str(user_cart.token)


def cart_dto(cart: Cart | None) -> dict:
    """خلاصه‌ی قابل ارسال به کلاینت"""
    items = []
    if cart is not None:
        items = [
            {"id": i.id, "qty": i.qty, "product": product_dto(i.product)}
            for i in cart.items.select_related(
                "product__category"
            ).prefetch_related("product__images")
        ]

    items_price = sum(
        (i["product"]["oldPrice"] or i["product"]["price"]) * i["qty"] for i in items
    )
    total_price = sum(i["product"]["price"] * i["qty"] for i in items)

    return {
        "items": items,
        "itemsCount": sum(i["qty"] for i in items),
        "itemsPrice": items_price,
        "discount": items_price - total_price,
        "totalPrice": total_price,
    }
