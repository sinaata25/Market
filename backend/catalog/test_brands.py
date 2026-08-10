from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.test import TestCase
from rest_framework.test import APIClient

from .brand_pricing import adjust_brand_prices
from .models import Brand, Category, Product


class BrandModelAndPublicApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tools = Category.objects.create(slug="tools", title="ابزار")
        self.irrigation = Category.objects.create(
            slug="irrigation", title="آبیاری"
        )
        self.bosch = Brand.objects.create(name="Bosch", slug="bosch")
        self.makita = Brand.objects.create(name="Makita", slug="makita")
        self.bosch_tool = Product.objects.create(
            title="دریل بوش",
            category=self.tools,
            brand=self.bosch,
            price=1_000,
        )
        self.bosch_irrigation = Product.objects.create(
            title="پمپ بوش",
            category=self.irrigation,
            brand=self.bosch,
            price=2_000,
        )
        self.makita_tool = Product.objects.create(
            title="دریل ماکیتا",
            category=self.tools,
            brand=self.makita,
            price=3_000,
        )
        self.unbranded = Product.objects.create(
            title="بیل بدون برند",
            category=self.tools,
            price=500,
        )

    def test_brand_creation_uniqueness_and_slug_validation(self):
        brand = Brand(
            name="Bosch",
            slug="not a valid slug",
        )
        with self.assertRaises(ValidationError) as context:
            brand.full_clean()

        self.assertIn("name", context.exception.message_dict)
        self.assertIn("slug", context.exception.message_dict)

    def test_product_has_zero_or_one_brand_independent_from_categories(self):
        self.assertIsNone(self.unbranded.brand)
        self.assertEqual(self.bosch_tool.brand, self.bosch)

        self.bosch_tool.categories.add(self.tools, self.irrigation)
        self.bosch_tool.brand = self.makita
        self.bosch_tool.save(update_fields=["brand"])

        self.assertEqual(self.bosch_tool.brand, self.makita)
        self.assertEqual(
            set(self.bosch_tool.categories.values_list("slug", flat=True)),
            {"tools", "irrigation"},
        )

    def test_public_brand_list_only_contains_active_brands(self):
        self.makita.is_active = False
        self.makita.save(update_fields=["is_active"])

        response = self.client.get("/api/brands")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [brand["slug"] for brand in response.data["data"]["brands"]],
            ["bosch"],
        )

    def test_product_brand_filter_is_independent_and_combines_with_category(self):
        by_brand = self.client.get("/api/products?brand=bosch")
        combined = self.client.get("/api/products?brand=bosch&category=tools")

        self.assertEqual(by_brand.data["data"]["total"], 2)
        self.assertEqual(
            {item["id"] for item in by_brand.data["data"]["items"]},
            {self.bosch_tool.id, self.bosch_irrigation.id},
        )
        self.assertEqual(combined.data["data"]["total"], 1)
        self.assertEqual(
            combined.data["data"]["items"][0]["id"], self.bosch_tool.id
        )
        self.assertEqual(
            combined.data["data"]["items"][0]["brand"]["slug"], "bosch"
        )

    def test_unbranded_product_is_serialized_with_null_brand(self):
        response = self.client.get(f"/api/products/{self.unbranded.id}")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["data"]["product"]["brand"])


class BrandAdminAndPricingTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            phone="09121111111", is_staff=True
        )
        self.customer = get_user_model().objects.create_user(
            phone="09122222222"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.category = Category.objects.create(slug="tools", title="ابزار")
        self.bosch = Brand.objects.create(name="Bosch", slug="bosch")
        self.makita = Brand.objects.create(name="Makita", slug="makita")
        self.rounded = Product.objects.create(
            title="محصول نیازمند گرد کردن",
            category=self.category,
            brand=self.bosch,
            price=335,
            old_price=500,
        )
        self.bosch_second = Product.objects.create(
            title="محصول دوم بوش",
            category=self.category,
            brand=self.bosch,
            price=2_000,
        )
        self.other_brand = Product.objects.create(
            title="محصول برند دیگر",
            category=self.category,
            brand=self.makita,
            price=3_000,
        )
        self.unbranded = Product.objects.create(
            title="محصول بدون برند",
            category=self.category,
            price=4_000,
        )

    def test_staff_can_create_update_list_and_delete_unused_brand(self):
        created = self.client.post(
            "/api/admin/brands",
            {
                "name": "DeWalt",
                "slug": "dewalt",
                "description": "ابزار حرفه‌ای",
                "website": "https://www.dewalt.com",
            },
            format="json",
        )
        brand_id = created.data["data"]["brand"]["id"]
        updated = self.client.patch(
            f"/api/admin/brands/{brand_id}",
            {"name": "DEWALT", "isActive": False},
            format="json",
        )
        listed = self.client.get("/api/admin/brands")
        deleted = self.client.delete(f"/api/admin/brands/{brand_id}")

        self.assertEqual(created.status_code, 201)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["data"]["brand"]["isActive"], False)
        self.assertTrue(
            any(
                item["id"] == brand_id
                and item["productCount"] == 0
                and item["website"] == "https://www.dewalt.com"
                for item in listed.data["data"]["brands"]
            )
        )
        self.assertEqual(deleted.status_code, 200)

    def test_duplicate_and_invalid_brand_are_rejected(self):
        duplicate = self.client.post(
            "/api/admin/brands",
            {"name": "Bosch", "slug": "bosch-2"},
            format="json",
        )
        invalid_slug = self.client.post(
            "/api/admin/brands",
            {"name": "Valid name", "slug": "invalid slug"},
            format="json",
        )

        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(invalid_slug.status_code, 400)

    def test_product_write_assigns_and_replaces_single_brand(self):
        created = self.client.post(
            "/api/admin/products",
            {
                "title": "دریل",
                "categorySlug": self.category.slug,
                "brandSlug": self.bosch.slug,
                "price": 1_000,
                "stock": 2,
            },
            format="json",
        )
        product_id = created.data["data"]["product"]["id"]
        updated = self.client.patch(
            f"/api/admin/products/{product_id}",
            {
                "title": "دریل",
                "categorySlug": self.category.slug,
                "brandSlug": self.makita.slug,
                "price": 1_000,
                "stock": 2,
            },
            format="json",
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["data"]["product"]["brand"]["slug"], "bosch")
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(Product.objects.get(pk=product_id).brand, self.makita)

    def test_increase_uses_decimal_rounding_and_only_selected_brand(self):
        response = self.client.post(
            f"/api/admin/brands/{self.bosch.id}/price-adjustment",
            {"operation": "increase", "percentage": "10.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["updatedCount"], 2)
        self.rounded.refresh_from_db()
        self.bosch_second.refresh_from_db()
        self.other_brand.refresh_from_db()
        self.unbranded.refresh_from_db()
        self.assertEqual(self.rounded.price, 369)
        self.assertEqual(self.rounded.old_price, 550)
        self.assertEqual(self.bosch_second.price, 2_200)
        self.assertEqual(self.other_brand.price, 3_000)
        self.assertEqual(self.unbranded.price, 4_000)

    def test_decrease_updates_all_selected_brand_products(self):
        response = self.client.post(
            f"/api/admin/brands/{self.bosch.id}/price-adjustment",
            {"operation": "decrease", "percentage": "15"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.bosch_second.refresh_from_db()
        self.assertEqual(self.bosch_second.price, 1_700)

    def test_invalid_percentages_are_rejected_without_changes(self):
        for value in ["0", "-1", "100"]:
            response = self.client.post(
                f"/api/admin/brands/{self.bosch.id}/price-adjustment",
                {"operation": "decrease", "percentage": value},
                format="json",
            )
            self.assertEqual(response.status_code, 400)

        self.rounded.refresh_from_db()
        self.assertEqual(self.rounded.price, 335)

    def test_customer_cannot_manage_brands_or_adjust_prices(self):
        customer_client = APIClient()
        customer_client.force_authenticate(self.customer)

        brand_list = customer_client.get("/api/admin/brands")
        adjusted = customer_client.post(
            f"/api/admin/brands/{self.bosch.id}/price-adjustment",
            {"operation": "increase", "percentage": "10"},
            format="json",
        )

        self.assertEqual(brand_list.status_code, 403)
        self.assertEqual(adjusted.status_code, 403)

    def test_pricing_service_rolls_back_when_bulk_write_fails(self):
        with patch(
            "django.db.models.query.QuerySet.bulk_update",
            side_effect=DatabaseError("write failed"),
        ):
            with self.assertRaises(DatabaseError):
                adjust_brand_prices(
                    brand=self.bosch,
                    operation="increase",
                    percentage=Decimal("10"),
                )

        self.rounded.refresh_from_db()
        self.bosch_second.refresh_from_db()
        self.assertEqual(self.rounded.price, 335)
        self.assertEqual(self.bosch_second.price, 2_000)
