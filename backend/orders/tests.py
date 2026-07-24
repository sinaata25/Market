from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Category, Product

from .models import Order, OrderItem


class OrderCancellationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(phone="09121234567")
        category = Category.objects.create(
            slug="tools", title="ابزار", emoji="🌿"
        )
        self.product = Product.objects.create(
            title="بیل", category=category, price=100_000, emoji="🌿", stock=3
        )
        self.order = Order.objects.create(
            code="GS-TEST",
            user=self.user,
            full_name="کاربر آزمایشی",
            phone=self.user.phone,
            province="تهران",
            city="تهران",
            address="خیابان آزمایشی شماره ده",
            items_price=200_000,
            total_price=200_000,
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            title=self.product.title,
            price=self.product.price,
            qty=2,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_cancel_restores_stock_only_once(self):
        first = self.client.post(f"/api/orders/{self.order.id}")
        second = self.client.post(f"/api/orders/{self.order.id}")

        self.product.refresh_from_db()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(self.product.stock, 5)

    def test_admin_cancel_restores_stock_and_canceled_order_is_terminal(self):
        admin = get_user_model().objects.create_user(
            phone="09120000000", is_staff=True
        )
        self.client.force_authenticate(admin)

        canceled = self.client.patch(
            f"/api/admin/orders/{self.order.id}",
            {"status": Order.Status.CANCELED},
            format="json",
        )
        reopened = self.client.patch(
            f"/api/admin/orders/{self.order.id}",
            {"status": Order.Status.PENDING},
            format="json",
        )

        self.product.refresh_from_db()
        self.assertEqual(canceled.status_code, 200)
        self.assertEqual(reopened.status_code, 409)
        self.assertEqual(self.product.stock, 5)
