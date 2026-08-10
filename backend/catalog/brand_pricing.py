from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from .models import Brand, Product


PRICE_QUANTUM = Decimal("1")
VALID_OPERATIONS = {"increase", "decrease"}


def _adjust_amount(amount: int, factor: Decimal) -> int:
    adjusted = (Decimal(amount) * factor).quantize(
        PRICE_QUANTUM, rounding=ROUND_HALF_UP
    )
    if adjusted < 0:
        raise ValueError("قیمت نهایی نمی‌تواند منفی باشد")
    return int(adjusted)


def adjust_brand_prices(
    *, brand: Brand, operation: str, percentage: Decimal
) -> int:
    """Adjust current and old prices for exactly one brand, atomically."""
    percentage = Decimal(percentage)
    if operation not in VALID_OPERATIONS:
        raise ValueError("نوع تغییر قیمت نامعتبر است")
    if percentage <= 0:
        raise ValueError("درصد باید بزرگ‌تر از صفر باشد")
    if operation == "decrease" and percentage >= 100:
        raise ValueError("درصد کاهش باید کمتر از ۱۰۰ باشد")

    direction = Decimal("1") if operation == "increase" else Decimal("-1")
    factor = Decimal("1") + direction * percentage / Decimal("100")

    with transaction.atomic():
        products = list(
            Product.objects.select_for_update().filter(brand_id=brand.id)
        )
        for product in products:
            product.price = _adjust_amount(product.price, factor)
            if product.old_price is not None:
                product.old_price = _adjust_amount(product.old_price, factor)
                if product.old_price <= product.price:
                    product.old_price = product.price + 1
        if products:
            Product.objects.bulk_update(products, ["price", "old_price"])
    return len(products)
