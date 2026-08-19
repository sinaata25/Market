from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from .models import Category, Product, ProductSpecification, SpecificationKey


class ProductSpecificationApiTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            phone="09121111111", is_staff=True
        )
        self.customer = get_user_model().objects.create_user(phone="09122222222")
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.category = Category.objects.create(slug="tools", title="ابزار")

    def product_payload(self, title="محصول آزمایشی", **overrides):
        payload = {
            "title": title,
            "categorySlug": self.category.slug,
            "price": 100_000,
            "stock": 4,
        }
        payload.update(overrides)
        return payload

    def create_key(self, name="ابعاد") -> dict:
        response = self.client.post(
            "/api/admin/specifications", {"name": name}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["data"]["specification"]

    def test_key_creation_normalizes_persian_text_and_rejects_duplicates(self):
        created = self.create_key("  وزن كالا  ")
        duplicate = self.client.post(
            "/api/admin/specifications", {"name": "وزن‌کالا"}, format="json"
        )

        key = SpecificationKey.objects.get(pk=created["id"])
        self.assertEqual(key.name, "وزن کالا")
        self.assertEqual(key.normalized_name, "وزن کالا")
        self.assertEqual(key.slug, "وزن-کالا")
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(SpecificationKey.objects.count(), 1)

    def test_key_search_rename_and_unused_delete(self):
        key = self.create_key("وزن كالا")

        searched = self.client.get("/api/admin/specifications", {"search": "كالا"})
        renamed = self.client.patch(
            f"/api/admin/specifications/{key['id']}",
            {"name": "وزن محصول"},
            format="json",
        )
        deleted = self.client.delete(f"/api/admin/specifications/{key['id']}")

        self.assertEqual(searched.status_code, 200)
        self.assertEqual(len(searched.data["data"]["specifications"]), 1)
        self.assertEqual(renamed.status_code, 200)
        self.assertEqual(
            renamed.data["data"]["specification"]["name"], "وزن محصول"
        )
        self.assertEqual(deleted.status_code, 200)

    def test_only_staff_can_manage_keys_and_product_specifications(self):
        key = self.create_key()
        product = Product.objects.create(
            title="بیل", category=self.category, price=100_000
        )
        for client in (APIClient(), self._customer_client()):
            responses = [
                client.get("/api/admin/specifications"),
                client.post(
                    "/api/admin/specifications", {"name": "وزن"}, format="json"
                ),
                client.patch(
                    f"/api/admin/specifications/{key['id']}",
                    {"name": "وزن"},
                    format="json",
                ),
                client.delete(f"/api/admin/specifications/{key['id']}"),
                client.patch(
                    f"/api/admin/products/{product.id}",
                    self.product_payload(
                        specifications=[
                            {"keyId": key["id"], "value": "10", "position": 0}
                        ]
                    ),
                    format="json",
                ),
            ]
            self.assertTrue(all(response.status_code == 403 for response in responses))
        self.assertFalse(ProductSpecification.objects.exists())

    def _customer_client(self):
        client = APIClient()
        client.force_authenticate(self.customer)
        return client

    def test_same_key_is_reused_with_independent_values_and_detail_contract(self):
        key = self.create_key()
        first = self.client.post(
            "/api/admin/products",
            self.product_payload(
                "محصول A",
                specifications=[
                    {
                        "keyId": key["id"],
                        "value": "20 × 30 سانتی‌متر",
                        "position": 0,
                    }
                ],
            ),
            format="json",
        )
        second = self.client.post(
            "/api/admin/products",
            self.product_payload(
                "محصول B",
                specifications=[
                    {
                        "keyId": key["id"],
                        "value": "40 × 50 سانتی‌متر",
                        "position": 0,
                    }
                ],
            ),
            format="json",
        )

        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)
        first_id = first.data["data"]["product"]["id"]
        second_id = second.data["data"]["product"]["id"]
        rows = ProductSpecification.objects.order_by("product_id")
        self.assertEqual({row.key_id for row in rows}, {key["id"]})
        self.assertEqual(
            [row.value for row in rows],
            ["20 × 30 سانتی‌متر", "40 × 50 سانتی‌متر"],
        )
        key_list = self.client.get("/api/admin/specifications")
        self.assertEqual(
            key_list.data["data"]["specifications"][0]["productCount"], 2
        )

        detail = APIClient().get(f"/api/products/{first_id}")
        self.assertEqual(
            detail.data["data"]["product"]["specifications"],
            [
                {
                    "keyId": key["id"],
                    "name": "ابعاد",
                    "slug": "ابعاد",
                    "value": "20 × 30 سانتی‌متر",
                    "position": 0,
                }
            ],
        )
        self.assertNotIn("specifications", detail.data["data"]["related"][0])

        updated = self.client.patch(
            f"/api/admin/products/{first_id}",
            self.product_payload(
                "محصول A",
                specifications=[
                    {"keyId": key["id"], "value": "30 × 60", "position": 0}
                ],
            ),
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            ProductSpecification.objects.get(product_id=second_id).value,
            "40 × 50 سانتی‌متر",
        )
        removed = self.client.patch(
            f"/api/admin/products/{first_id}",
            self.product_payload("محصول A", specifications=[]),
            format="json",
        )
        self.assertEqual(removed.status_code, 200)
        self.assertFalse(
            ProductSpecification.objects.filter(product_id=first_id).exists()
        )
        self.assertEqual(
            ProductSpecification.objects.get(product_id=second_id).value,
            "40 × 50 سانتی‌متر",
        )
        key_list = self.client.get("/api/admin/specifications")
        self.assertEqual(
            key_list.data["data"]["specifications"][0]["productCount"], 1
        )

    def test_ordering_replacement_removal_and_rename_are_reflected(self):
        dimensions = self.create_key()
        weight = self.create_key("وزن")
        created = self.client.post(
            "/api/admin/products",
            self.product_payload(
                specifications=[
                    {"keyId": dimensions["id"], "value": "20cm", "position": 20},
                    {"keyId": weight["id"], "value": "2kg", "position": 5},
                ]
            ),
            format="json",
        )
        product_id = created.data["data"]["product"]["id"]

        detail = APIClient().get(f"/api/products/{product_id}")
        self.assertEqual(
            [item["keyId"] for item in detail.data["data"]["product"]["specifications"]],
            [weight["id"], dimensions["id"]],
        )

        renamed = self.client.patch(
            f"/api/admin/specifications/{weight['id']}",
            {"name": "وزن محصول"},
            format="json",
        )
        replaced = self.client.patch(
            f"/api/admin/products/{product_id}",
            self.product_payload(
                specifications=[
                    {"keyId": weight["id"], "value": "3kg", "position": 0}
                ]
            ),
            format="json",
        )
        protected = self.client.delete(f"/api/admin/specifications/{weight['id']}")

        self.assertEqual(renamed.status_code, 200)
        self.assertEqual(replaced.status_code, 200)
        specs = replaced.data["data"]["product"]["specifications"]
        self.assertEqual(specs[0]["name"], "وزن محصول")
        self.assertEqual(specs[0]["value"], "3kg")
        self.assertFalse(
            ProductSpecification.objects.filter(
                product_id=product_id, key_id=dimensions["id"]
            ).exists()
        )
        self.assertEqual(protected.status_code, 409)

    def test_omitted_specifications_preserve_rows_and_empty_list_clears_them(self):
        key = self.create_key()
        product = Product.objects.create(
            title="بیل", category=self.category, price=100_000
        )
        ProductSpecification.objects.create(
            product=product, key_id=key["id"], value="10cm", position=0
        )

        preserved = self.client.patch(
            f"/api/admin/products/{product.id}",
            self.product_payload("بیل جدید"),
            format="json",
        )
        cleared = self.client.patch(
            f"/api/admin/products/{product.id}",
            self.product_payload("بیل جدید", specifications=[]),
            format="json",
        )

        self.assertEqual(preserved.status_code, 200)
        self.assertEqual(len(preserved.data["data"]["product"]["specifications"]), 1)
        self.assertEqual(cleared.status_code, 200)
        self.assertFalse(ProductSpecification.objects.filter(product=product).exists())

    def test_invalid_specification_payloads_are_rejected_without_changes(self):
        key = self.create_key()
        invalid_lists = [
            [
                {"keyId": key["id"], "value": "one", "position": 0},
                {"keyId": key["id"], "value": "two", "position": 1},
            ],
            [{"keyId": 999999, "value": "value", "position": 0}],
            [{"keyId": key["id"], "value": "   ", "position": 0}],
            [{"keyId": key["id"], "value": "value", "position": -1}],
        ]
        for specifications in invalid_lists:
            response = self.client.post(
                "/api/admin/products",
                self.product_payload(specifications=specifications),
                format="json",
            )
            self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Product.objects.exists())

    def test_database_constraint_prevents_duplicate_key_on_product(self):
        key = SpecificationKey.objects.create(name="وزن")
        product = Product.objects.create(
            title="بیل", category=self.category, price=100_000
        )
        ProductSpecification.objects.create(
            product=product, key=key, value="1kg", position=0
        )
        with self.assertRaises(ValidationError):
            ProductSpecification.objects.create(
                product=product, key=key, value="2kg", position=1
            )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductSpecification.objects.bulk_create(
                    [
                        ProductSpecification(
                            product=product, key=key, value="3kg", position=2
                        )
                    ]
                )
        with self.assertRaises(ValidationError):
            SpecificationKey.objects.create(name="  وزن  ")

    def test_product_creation_rolls_back_when_specification_write_fails(self):
        key = self.create_key()
        with patch(
            "catalog.models.ProductSpecification.objects.bulk_create",
            side_effect=DatabaseError("write failed"),
        ):
            with self.assertRaises(DatabaseError):
                self.client.post(
                    "/api/admin/products",
                    self.product_payload(
                        title="نباید بماند",
                        specifications=[
                            {"keyId": key["id"], "value": "10cm", "position": 0}
                        ],
                    ),
                    format="json",
                )
        self.assertFalse(Product.objects.filter(title="نباید بماند").exists())

        product = Product.objects.create(
            title="عنوان قبلی", category=self.category, price=100_000
        )
        ProductSpecification.objects.create(
            product=product, key_id=key["id"], value="old", position=0
        )
        with patch(
            "catalog.models.ProductSpecification.objects.bulk_create",
            side_effect=DatabaseError("write failed"),
        ):
            with self.assertRaises(DatabaseError):
                self.client.patch(
                    f"/api/admin/products/{product.id}",
                    self.product_payload(
                        title="عنوان جدید",
                        specifications=[
                            {"keyId": key["id"], "value": "new", "position": 0}
                        ],
                    ),
                    format="json",
                )
        product.refresh_from_db()
        self.assertEqual(product.title, "عنوان قبلی")
        self.assertEqual(product.specifications.get().value, "old")

    def test_only_detail_prefetches_and_serializes_specifications(self):
        key = SpecificationKey.objects.create(name="وزن")
        product = Product.objects.create(
            title="بیل", category=self.category, price=100_000
        )
        ProductSpecification.objects.create(
            product=product, key=key, value="1kg", position=0
        )

        with CaptureQueriesContext(connection) as list_queries:
            listed = APIClient().get("/api/products")
        with CaptureQueriesContext(connection) as detail_queries:
            detailed = APIClient().get(f"/api/products/{product.id}")

        spec_table = "catalog_productspecification"
        self.assertNotIn("specifications", listed.data["data"]["items"][0])
        self.assertEqual(
            sum(spec_table in query["sql"] for query in list_queries.captured_queries),
            0,
        )
        self.assertEqual(
            sum(spec_table in query["sql"] for query in detail_queries.captured_queries),
            1,
        )
        self.assertEqual(
            detailed.data["data"]["product"]["specifications"][0]["value"],
            "1kg",
        )
