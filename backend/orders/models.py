from django.conf import settings
from django.db import models

from catalog.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "در انتظار پرداخت"
        PAID = "PAID", "پرداخت شده"
        SHIPPED = "SHIPPED", "ارسال شده"
        DELIVERED = "DELIVERED", "تحویل شده"
        CANCELED = "CANCELED", "لغو شده"

    code = models.CharField("کد پیگیری", max_length=20, unique=True)
    status = models.CharField(
        "وضعیت", max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)

    # اطلاعات تحویل‌گیرنده (کپی می‌شود تا با ویرایش پروفایل تغییر نکند)
    full_name = models.CharField("نام تحویل‌گیرنده", max_length=100)
    phone = models.CharField("شماره موبایل", max_length=11)
    province = models.CharField("استان", max_length=50)
    city = models.CharField("شهر", max_length=50)
    address = models.TextField("آدرس")
    postal_code = models.CharField("کد پستی", max_length=10, blank=True)

    items_price = models.PositiveIntegerField("جمع قیمت کالاها")
    discount = models.PositiveIntegerField("تخفیف", default=0)
    shipping_price = models.PositiveIntegerField("هزینه ارسال", default=0)
    total_price = models.PositiveIntegerField("مبلغ کل")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="کاربر",
        on_delete=models.PROTECT,
        related_name="orders",
    )

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.code

    @property
    def invoice_number(self) -> str:
        """Stable invoice identifier based on the unique, immutable order code."""
        return f"INV-{self.code}"


class OrderItem(models.Model):
    # عنوان و قیمت در لحظه‌ی خرید کپی می‌شوند
    title = models.CharField("عنوان", max_length=255)
    price = models.PositiveIntegerField("قیمت واحد")
    old_price = models.PositiveIntegerField("قیمت قبل", null=True, blank=True)
    qty = models.PositiveIntegerField("تعداد")

    order = models.ForeignKey(
        Order, verbose_name="سفارش", on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        Product,
        verbose_name="محصول",
        on_delete=models.PROTECT,
        related_name="order_items",
    )

    class Meta:
        verbose_name = "قلم سفارش"
        verbose_name_plural = "اقلام سفارش"

    def __str__(self) -> str:
        return f"{self.title} × {self.qty}"
