from io import BytesIO
from tempfile import TemporaryDirectory

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
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
        self.media_dir = TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_override.enable()
        admin = get_user_model().objects.create_user(
            phone="09121234567", is_staff=True
        )
        self.client = APIClient()
        self.client.force_authenticate(admin)
        self.category = Category.objects.create(slug="tools", title="ابزار")

    def tearDown(self):
        self.media_override.disable()
        self.media_dir.cleanup()
        super().tearDown()

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

    def test_new_product_can_receive_an_image_after_creation(self):
        created = self.client.post(
            "/api/admin/products", self.product_payload(), format="json"
        )
        product_id = created.data["data"]["product"]["id"]
        image_bytes = BytesIO()
        Image.new("RGB", (2, 2), color="green").save(image_bytes, format="PNG")
        upload = SimpleUploadedFile(
            "product.png", image_bytes.getvalue(), content_type="image/png"
        )

        response = self.client.post(
            f"/api/admin/products/{product_id}/image",
            {"file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        product = response.data["data"]["product"]
        self.assertEqual(len(product["imageItems"]), 1)
        self.assertEqual(product["images"], [product["imageItems"][0]["url"]])

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
