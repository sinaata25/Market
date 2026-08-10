from io import BytesIO
from tempfile import TemporaryDirectory

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from rest_framework.test import APIClient

from catalog.models import Category, Product, ProductComment


PRODUCT_RESPONSE_KEYS = {
    "image",
    "images",
    "id",
    "title",
    "titleEn",
    "category",
    "categorySlug",
    "categories",
    "categorySlugs",
    "brand",
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
    "isActive",
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

    def test_product_can_be_assigned_to_multiple_categories(self):
        second_category = Category.objects.create(
            slug="irrigation", title="آبیاری"
        )
        created = self.client.post(
            "/api/admin/products",
            self.product_payload(
                categorySlugs=[self.category.slug, second_category.slug]
            ),
            format="json",
        )

        self.assertEqual(created.status_code, 201)
        product_data = created.data["data"]["product"]
        self.assertEqual(
            product_data["categorySlugs"],
            [self.category.slug, second_category.slug],
        )
        product = Product.objects.get(pk=product_data["id"])
        self.assertEqual(product.category, self.category)
        self.assertEqual(
            set(product.categories.values_list("slug", flat=True)),
            {self.category.slug, second_category.slug},
        )

        filtered = self.client.get(
            f"/api/products?category={second_category.slug}"
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.data["data"]["total"], 1)

        protected = self.client.delete(
            f"/api/admin/categories/{second_category.id}"
        )
        self.assertEqual(protected.status_code, 409)

        updated = self.client.patch(
            f"/api/admin/products/{product.id}",
            self.product_payload(categorySlugs=[second_category.slug]),
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.category, second_category)
        self.assertEqual(list(product.categories.all()), [second_category])

    def test_product_visibility_controls_public_access(self):
        created = self.client.post(
            "/api/admin/products", self.product_payload(), format="json"
        )
        product_id = created.data["data"]["product"]["id"]

        hidden = self.client.patch(
            f"/api/admin/products/{product_id}/visibility",
            {"isActive": False},
            format="json",
        )

        self.assertEqual(hidden.status_code, 200)
        self.assertEqual(hidden.data["data"]["product"]["isActive"], False)
        self.assertEqual(self.client.get("/api/products").data["data"]["total"], 0)
        self.assertEqual(self.client.get(f"/api/products/{product_id}").status_code, 404)
        self.assertEqual(
            self.client.post(
                "/api/cart/items",
                {"productId": product_id, "qty": 1},
                format="json",
            ).status_code,
            404,
        )

        shown = self.client.patch(
            f"/api/admin/products/{product_id}/visibility",
            {"isActive": True},
            format="json",
        )
        self.assertEqual(shown.status_code, 200)
        self.assertEqual(shown.data["data"]["product"]["isActive"], True)
        self.assertEqual(self.client.get(f"/api/products/{product_id}").status_code, 200)

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

    def test_category_crud_uses_admin_contract(self):
        created = self.client.post(
            "/api/admin/categories",
            {
                "title": "آبیاری",
                "slug": "irrigation",
                "parentIds": [self.category.id],
            },
            format="json",
        )

        self.assertEqual(created.status_code, 201)
        category = created.data["data"]["category"]
        self.assertEqual(
            set(category),
            {
                "id",
                "slug",
                "title",
                "icon",
                "sub",
                "parents",
                "isTopLevel",
                "isActive",
                "effectiveIsActive",
                "productCount",
            },
        )
        self.assertEqual(category["isActive"], True)
        self.assertEqual(category["effectiveIsActive"], True)
        self.assertEqual(category["isTopLevel"], False)
        self.assertEqual(category["parents"][0]["id"], self.category.id)
        self.assertEqual(category["productCount"], 0)

        category_id = category["id"]
        updated = self.client.patch(
            f"/api/admin/categories/{category_id}",
            {
                "title": "تجهیزات آبیاری",
                "isActive": False,
            },
            format="json",
        )
        listed = self.client.get("/api/admin/categories")
        public = self.client.get("/api/categories")

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(
            updated.data["data"]["category"]["title"], "تجهیزات آبیاری"
        )
        self.assertEqual(updated.data["data"]["category"]["isActive"], False)
        self.assertEqual(
            updated.data["data"]["category"]["effectiveIsActive"], False
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data["data"]["categories"]), 2)
        self.assertEqual(
            [item["slug"] for item in public.data["data"]["categories"]],
            [self.category.slug],
        )

        deleted = self.client.delete(f"/api/admin/categories/{category_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(Category.objects.filter(pk=category_id).exists())

    def test_category_validation_and_protected_delete_are_controlled(self):
        duplicate = self.client.post(
            "/api/admin/categories",
            {"title": self.category.title, "slug": "other", "parentIds": []},
            format="json",
        )
        Product.objects.create(
            title="بیل",
            category=self.category,
            price=100_000,
        )
        protected = self.client.delete(
            f"/api/admin/categories/{self.category.id}"
        )

        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(duplicate.data["ok"], False)
        self.assertEqual(protected.status_code, 409)
        self.assertEqual(protected.data["ok"], False)
        self.assertTrue(Category.objects.filter(pk=self.category.id).exists())

    def test_shared_subcategory_visibility_and_cycle_validation(self):
        second_parent = Category.objects.create(
            slug="irrigation", title="آبیاری"
        )
        child = Category.objects.create(slug="pumps", title="پمپ آب")
        child.parents.set([self.category, second_parent])
        product = Product.objects.create(
            title="پمپ آب",
            category=child,
            price=100_000,
        )
        product.categories.add(child)

        public = self.client.get("/api/categories").data["data"]["categories"]
        by_slug = {item["slug"]: item for item in public}
        self.assertEqual(by_slug["pumps"]["isTopLevel"], False)
        self.assertEqual(by_slug["tools"]["sub"][0]["slug"], "pumps")
        self.assertEqual(by_slug["irrigation"]["sub"][0]["slug"], "pumps")
        self.assertEqual(
            self.client.get("/api/products?category=tools").data["data"]["total"],
            1,
        )
        self.assertEqual(
            self.client.get("/api/products?category=irrigation").data["data"][
                "total"
            ],
            1,
        )

        self.client.patch(
            f"/api/admin/categories/{self.category.id}",
            {"isActive": False},
            format="json",
        )
        visible_slugs = {
            item["slug"]
            for item in self.client.get("/api/categories").data["data"][
                "categories"
            ]
        }
        self.assertEqual(visible_slugs, {"irrigation", "pumps"})

        self.client.patch(
            f"/api/admin/categories/{second_parent.id}",
            {"isActive": False},
            format="json",
        )
        self.assertEqual(
            self.client.get("/api/categories").data["data"]["categories"], []
        )

        self.client.patch(
            f"/api/admin/categories/{self.category.id}",
            {"isActive": True},
            format="json",
        )
        restored_slugs = {
            item["slug"]
            for item in self.client.get("/api/categories").data["data"][
                "categories"
            ]
        }
        self.assertEqual(restored_slugs, {"tools", "pumps"})

        self.client.patch(
            f"/api/admin/categories/{child.id}",
            {"isActive": False},
            format="json",
        )
        explicitly_hidden = {
            item["slug"]
            for item in self.client.get("/api/categories").data["data"][
                "categories"
            ]
        }
        self.assertEqual(explicitly_hidden, {"tools"})

        cycle = self.client.patch(
            f"/api/admin/categories/{second_parent.id}",
            {"parentIds": [child.id]},
            format="json",
        )
        self.assertEqual(cycle.status_code, 400)
        self.assertEqual(cycle.data["ok"], False)

    def test_nested_subcategory_requires_an_active_path_from_a_root(self):
        child = Category.objects.create(slug="garden", title="باغبانی")
        grandchild = Category.objects.create(slug="shovels", title="بیل‌ها")
        child.parents.add(self.category)
        grandchild.parents.add(child)

        visible = {
            item["slug"]
            for item in self.client.get("/api/categories").data["data"][
                "categories"
            ]
        }
        self.assertEqual(visible, {"tools", "garden", "shovels"})

        self.client.patch(
            f"/api/admin/categories/{child.id}",
            {"isActive": False},
            format="json",
        )
        visible = {
            item["slug"]
            for item in self.client.get("/api/categories").data["data"][
                "categories"
            ]
        }
        self.assertEqual(visible, {"tools"})

    def test_non_staff_cannot_manage_categories(self):
        non_staff = get_user_model().objects.create_user(phone="09120000000")
        client = APIClient()
        client.force_authenticate(non_staff)

        response = client.get("/api/admin/categories")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["ok"], False)

    def test_category_icon_can_be_uploaded_and_removed(self):
        image_bytes = BytesIO()
        Image.new("RGBA", (2, 2), color="green").save(image_bytes, format="PNG")
        upload = SimpleUploadedFile(
            "category.png", image_bytes.getvalue(), content_type="image/png"
        )

        uploaded = self.client.post(
            f"/api/admin/categories/{self.category.id}/icon",
            {"file": upload},
            format="multipart",
        )

        self.assertEqual(uploaded.status_code, 201)
        self.assertTrue(uploaded.data["data"]["category"]["icon"])
        self.category.refresh_from_db()
        self.assertTrue(self.category.icon.name.endswith(".png"))

        with self.captureOnCommitCallbacks(execute=True):
            removed = self.client.delete(
                f"/api/admin/categories/{self.category.id}/icon"
            )
        self.assertEqual(removed.status_code, 200)
        self.category.refresh_from_db()
        self.assertFalse(self.category.icon)

    def test_admin_can_approve_reject_and_filter_comments(self):
        product = Product.objects.create(
            title="بیل", category=self.category, price=100_000
        )
        reviewer = get_user_model().objects.create_user(phone="09121111111")
        comment = ProductComment.objects.create(
            product=product,
            user=reviewer,
            content="دیدگاه در انتظار تایید مدیر",
        )

        listed = self.client.get("/api/admin/comments?status=pending")
        self.assertEqual(
            listed.data["data"]["comments"][0]["status"], "pending"
        )

        approved = self.client.patch(
            f"/api/admin/comments/{comment.id}",
            {"status": "approved"},
            format="json",
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.data["data"]["comment"]["status"], "approved")

        rejected = self.client.patch(
            f"/api/admin/comments/{comment.id}",
            {"status": "rejected"},
            format="json",
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.data["data"]["comment"]["status"], "rejected")
