from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from rest_framework.test import APIClient

from .models import Category, Product


class ProductBulkApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(slug="tools", title="ابزار")

    def make_product(self, title: str, *, active: bool = True) -> Product:
        return Product.objects.create(
            title=title,
            category=self.category,
            price=100_000,
            stock=2,
            is_active=active,
        )

    def test_bulk_endpoint_preserves_order_and_deduplicates_ids(self):
        first = self.make_product("اول")
        second = self.make_product("دوم")
        third = self.make_product("سوم")

        response = self.client.get(
            f"/api/products/by-ids?ids={third.id},{first.id},{third.id},{second.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["data"]["items"]],
            [third.id, first.id, second.id],
        )

    def test_bulk_endpoint_omits_inactive_deleted_and_unknown_products(self):
        visible = self.make_product("نمایان")
        inactive = self.make_product("پنهان", active=False)
        deleted = self.make_product("حذف‌شده")
        deleted_id = deleted.id
        deleted.delete()

        response = self.client.get(
            f"/api/products/by-ids?ids={inactive.id},{deleted_id},999999,{visible.id}"
        )

        self.assertEqual(
            [item["id"] for item in response.data["data"]["items"]],
            [visible.id],
        )

    def test_bulk_endpoint_validates_ids_and_limit(self):
        malformed = self.client.get("/api/products/by-ids?ids=1,nope")
        too_many = self.client.get(
            "/api/products/by-ids?ids=" + ",".join(str(i) for i in range(1, 17))
        )

        self.assertEqual(malformed.status_code, 422)
        self.assertEqual(too_many.status_code, 422)

    def test_bulk_endpoint_uses_a_constant_number_of_product_queries(self):
        products = [self.make_product(f"محصول {index}") for index in range(10)]
        ids = ",".join(str(product.id) for product in products)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(f"/api/products/by-ids?ids={ids}")

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(queries), 4)
