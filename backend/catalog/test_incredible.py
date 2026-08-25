"""بخش «شگفت‌انگیزها» — انتخاب دستی مدیر، و فهرست جدای همه‌ی تخفیف‌دارها

قاعده‌ی اصلی: «شگفت‌انگیز» یعنی مدیر آن را انتخاب کرده باشد، نه اینکه محصول
تخفیف داشته باشد. این دو مفهوم عمداً از هم جدا شده‌اند.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Category, Product

User = get_user_model()


class IncredibleApiTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(slug="tools", title="ابزار")
        self.client = APIClient()

    def make_product(
        self,
        title,
        *,
        is_incredible=False,
        position=0,
        is_active=True,
        old_price=None,
    ):
        return Product.objects.create(
            title=title,
            category=self.category,
            price=100_000,
            old_price=old_price,
            is_active=is_active,
            is_incredible=is_incredible,
            incredible_position=position,
        )

    def test_only_admin_selected_products_are_returned(self):
        picked = self.make_product("منتخب مدیر", is_incredible=True)
        self.make_product("محصول عادی")

        response = self.client.get("/api/products?incredible=true")

        self.assertEqual(response.status_code, 200)
        items = response.data["data"]["items"]
        self.assertEqual([item["id"] for item in items], [picked.id])

    def test_discounted_product_is_not_incredible_unless_admin_picks_it(self):
        """تخفیف داشتن به‌تنهایی محصول را شگفت‌انگیز نمی‌کند"""
        self.make_product("تخفیف‌دار ولی انتخاب‌نشده", old_price=200_000)

        incredible = self.client.get("/api/products?incredible=true")
        discounted = self.client.get("/api/products?discounted=true")

        self.assertEqual(incredible.data["data"]["total"], 0)
        self.assertEqual(discounted.data["data"]["total"], 1)

    def test_incredible_product_without_discount_is_still_listed(self):
        """انتخاب مدیر مستقل از تخفیف است"""
        picked = self.make_product("شگفت‌انگیز بدون تخفیف", is_incredible=True)

        response = self.client.get("/api/products?incredible=true")

        self.assertEqual([i["id"] for i in response.data["data"]["items"]], [picked.id])
        self.assertIsNone(response.data["data"]["items"][0]["oldPrice"])

    def test_inactive_incredible_product_is_not_publicly_visible(self):
        self.make_product("غیرفعال", is_incredible=True, is_active=False)

        response = self.client.get("/api/products?incredible=true")

        self.assertEqual(response.data["data"]["total"], 0)

    def test_incredible_sort_respects_admin_position(self):
        third = self.make_product("سوم", is_incredible=True, position=3)
        first = self.make_product("اول", is_incredible=True, position=1)
        second = self.make_product("دوم", is_incredible=True, position=2)

        response = self.client.get(
            "/api/products?incredible=true&sort=incredible"
        )

        items = response.data["data"]["items"]
        self.assertEqual(
            [item["id"] for item in items], [first.id, second.id, third.id]
        )

    def test_incredible_and_best_seller_are_independent_flags(self):
        both = self.make_product("هر دو", is_incredible=True)
        both.is_best_seller = True
        both.save(update_fields=["is_best_seller"])
        only_best = self.make_product("فقط پرفروش")
        only_best.is_best_seller = True
        only_best.save(update_fields=["is_best_seller"])

        incredible = self.client.get("/api/products?incredible=true")
        best = self.client.get("/api/products?bestSeller=true")

        self.assertEqual(
            [i["id"] for i in incredible.data["data"]["items"]], [both.id]
        )
        self.assertEqual(
            sorted(i["id"] for i in best.data["data"]["items"]),
            sorted([both.id, only_best.id]),
        )

    def test_discounted_filter_requires_a_real_price_drop(self):
        """old_price پرشده ولی نه بیشتر از قیمت = تخفیف نیست"""
        self.make_product("قیمت قبلی برابر", old_price=100_000)
        self.make_product("قیمت قبلی کمتر", old_price=50_000)
        real = self.make_product("تخفیف واقعی", old_price=150_000)

        response = self.client.get("/api/products?discounted=true")

        items = response.data["data"]["items"]
        self.assertEqual([item["id"] for item in items], [real.id])

    def test_dto_exposes_curation_fields(self):
        product = self.make_product("منتخب", is_incredible=True, position=4)

        response = self.client.get(f"/api/products/{product.id}")

        data = response.data["data"]["product"]
        self.assertTrue(data["isIncredible"])
        self.assertEqual(data["incrediblePosition"], 4)


class AdminIncredibleApiTests(TestCase):
    """فقط مدیر فروشگاه می‌تواند شگفت‌انگیزها را انتخاب کند"""

    def setUp(self):
        self.category = Category.objects.create(slug="tools", title="ابزار")
        self.product = Product.objects.create(
            title="محصول", category=self.category, price=100_000
        )
        self.admin = User.objects.create_user(phone="09120000901", is_staff=True)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def url(self):
        return f"/api/admin/products/{self.product.id}/incredible"

    def test_admin_can_mark_and_unmark_product_as_incredible(self):
        marked = self.client.patch(
            self.url(), {"isIncredible": True, "position": 2}, format="json"
        )
        self.assertEqual(marked.status_code, 200, marked.data)
        self.assertTrue(marked.data["data"]["product"]["isIncredible"])
        self.assertEqual(marked.data["data"]["product"]["incrediblePosition"], 2)
        self.assertEqual(
            self.client.get("/api/products?incredible=true").data["data"]["total"],
            1,
        )

        unmarked = self.client.patch(
            self.url(), {"isIncredible": False}, format="json"
        )
        self.assertEqual(unmarked.status_code, 200)
        self.assertFalse(unmarked.data["data"]["product"]["isIncredible"])
        # ترتیب حفظ می‌شود تا با انتخاب دوباره از دست نرود
        self.assertEqual(unmarked.data["data"]["product"]["incrediblePosition"], 2)
        self.assertEqual(
            self.client.get("/api/products?incredible=true").data["data"]["total"],
            0,
        )

    def test_hidden_product_can_be_curated_without_becoming_visible(self):
        self.product.is_active = False
        self.product.save(update_fields=["is_active"])

        response = self.client.patch(
            self.url(), {"isIncredible": True}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Product.objects.get(pk=self.product.pk).is_incredible)
        self.assertEqual(
            self.client.get("/api/products?incredible=true").data["data"]["total"],
            0,
        )

    def test_missing_product_returns_404(self):
        response = self.client.patch(
            "/api/admin/products/999999/incredible",
            {"isIncredible": True},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_non_staff_cannot_change_incredible_status(self):
        customer = User.objects.create_user(phone="09120000902")
        seo_admin = User.objects.create_user(
            phone="09120000903", is_seo_manager=True
        )
        clients = {"anonymous": APIClient()}
        for name, user in (("customer", customer), ("seo-admin", seo_admin)):
            client = APIClient()
            client.force_authenticate(user)
            clients[name] = client

        for role, client in clients.items():
            with self.subTest(role=role):
                response = client.patch(
                    self.url(), {"isIncredible": True}, format="json"
                )
                self.assertEqual(response.status_code, 403)
        self.assertFalse(Product.objects.get(pk=self.product.pk).is_incredible)
