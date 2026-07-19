import uuid

from django.conf import settings
from django.db import models

from catalog.models import Product


class Cart(models.Model):
    token = models.UUIDField("توکن", unique=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="کاربر",
        on_delete=models.CASCADE,
        related_name="cart",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    class Meta:
        verbose_name = "سبد خرید"
        verbose_name_plural = "سبدهای خرید"

    def __str__(self) -> str:
        owner = self.user or "مهمان"
        return f"سبد {owner}"


class CartItem(models.Model):
    qty = models.PositiveIntegerField("تعداد", default=1)

    cart = models.ForeignKey(
        Cart, verbose_name="سبد", on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        Product,
        verbose_name="محصول",
        on_delete=models.CASCADE,
        related_name="cart_items",
    )

    class Meta:
        verbose_name = "قلم سبد"
        verbose_name_plural = "اقلام سبد"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"], name="unique_cart_product"
            )
        ]

    def __str__(self) -> str:
        return f"{self.product} × {self.qty}"
