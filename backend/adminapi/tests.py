from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Category, Product


PRODUCT_RESPONSE_KEYS = {
    "image",
    "images",
    "id",
    "title",
    "titleEn",
    "category",
    "categorySlug",
    "price",
    "oldPrice",
    "rating",
    "ratingCount",
    "badge",
    "colors",
    "features",
    "specs",
    "description",
    "warranty",
    "stock",
}


class AdminApiContractTests(TestCase):
    def setUp(self):
        admin = get_user_model().objects.create_user(
            phone="09121234567", is_staff=True
        )
        self.client = APIClient()
        self.client.force_authenticate(admin)
        self.category = Category.objects.create(slug="tools", title="ابزار")

    def product_payload(self, **overrides):
        payload = {
            "title": "بیل باغبانی",
            "categorySlug": self.category.slug,
            "price": 100_000,
            "stock": 4,
        }
        payload.update(overrides)
        return payload

    def test_invalid_page_returns_validation_error(self):
        response = self.client.get("/api/admin/products?page=not-a-number")

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["ok"], False)

    def test_product_create_and_list_use_current_contract(self):
        created = self.client.post(
            "/api/admin/products", self.product_payload(), format="json"
        )
        listed = self.client.get("/api/admin/products")

        self.assertEqual(created.status_code, 201)
        self.assertEqual(
            set(created.data["data"]["product"]), PRODUCT_RESPONSE_KEYS
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(
            set(listed.data["data"]["products"][0]), PRODUCT_RESPONSE_KEYS
        )

    def test_product_update_and_retrieve_use_current_contract(self):
        product = Product.objects.create(
            title="بیل باغبانی",
            category=self.category,
            price=100_000,
            stock=4,
        )

        updated = self.client.patch(
            f"/api/admin/products/{product.id}",
            self.product_payload(title="بیل باغبانی حرفه‌ای", price=125_000),
            format="json",
        )
        retrieved = self.client.get(f"/api/admin/products/{product.id}")

        expected_keys = PRODUCT_RESPONSE_KEYS | {"imageItems"}
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            set(updated.data["data"]["product"]), expected_keys
        )
        self.assertEqual(
            updated.data["data"]["product"]["title"],
            "بیل باغبانی حرفه‌ای",
        )
        self.assertEqual(retrieved.status_code, 200)
        self.assertEqual(
            set(retrieved.data["data"]["product"]), expected_keys
        )

    def test_low_stock_rows_use_current_contract(self):
        Product.objects.create(
            title="بیل باغبانی",
            category=self.category,
            price=100_000,
            stock=4,
        )

        response = self.client.get("/api/admin/stats")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.data["data"]["lowStock"][0]),
            {"id", "title", "stock"},
        )
