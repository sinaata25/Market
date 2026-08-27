"""ماتریس دسترسی پنل سئو

پنل سئو ناحیه‌ای جداست: فقط «مدیر سئو» به آن راه دارد و سوپریوزر/مدیر فروشگاه
عمداً رد می‌شوند. این تست‌ها همان جدول را مستقیماً روی API می‌سنجند تا پنهان‌کردن
لینک‌ها در فرانت تنها لایه‌ی محافظت نباشد.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Category, Product

from .models import PageMeta, Redirect, SeoSettings

User = get_user_model()

# همه‌ی مسیرهای پنل سئو با متدهای تغییردهنده و خواندنی
SEO_ENDPOINTS = [
    ("get", "/api/admin/seo/overview", None),
    ("get", "/api/admin/seo/pages", None),
    ("get", "/api/admin/seo/meta?type=static&key=/", None),
    ("put", "/api/admin/seo/meta?type=static&key=/", {"metaTitle": "نفوذ"}),
    ("get", "/api/admin/seo/revisions?type=static&key=/", None),
    ("get", "/api/admin/seo/redirects", None),
    (
        "post",
        "/api/admin/seo/redirects",
        {"fromPath": "/a", "toPath": "/b"},
    ),
    ("get", "/api/admin/seo/404s", None),
    ("delete", "/api/admin/seo/404s", None),
    ("get", "/api/admin/seo/images", None),
    ("patch", "/api/admin/seo/images", {"items": [{"id": 1, "alt": "x"}]}),
    ("get", "/api/admin/seo/scan", None),
    ("post", "/api/admin/seo/scan", {}),
    ("get", "/api/admin/seo/settings", None),
    ("put", "/api/admin/seo/settings", {"siteName": "نفوذ"}),
]

# نمونه‌ای از مسیرهای داشبورد فروشگاه که مدیر سئو نباید به آن‌ها برسد
SHOP_ADMIN_ENDPOINTS = [
    ("get", "/api/admin/stats", None),
    ("get", "/api/admin/orders", None),
    ("get", "/api/admin/users", None),
    ("get", "/api/admin/products", None),
    ("get", "/api/admin/categories", None),
    ("get", "/api/admin/comments", None),
    ("get", "/api/admin/seo-admins", None),
    ("get", "/api/admin/managers", None),
    ("get", "/api/admin/blog/posts", None),
    ("get", "/api/admin/content/pages", None),
    ("get", "/api/admin/home/sections", None),
]


def call(client: APIClient, method: str, url: str, payload):
    handler = getattr(client, method)
    if payload is None:
        return handler(url)
    return handler(url, payload, format="json")


class SeoRoleTestMixin:
    """کاربران هر نقش + کلاینت احرازشده"""

    def setUp(self):
        super().setUp()
        self.seo_admin = User.objects.create_user(
            phone="09120000101", name="مدیر سئو", is_seo_manager=True
        )
        self.staff = User.objects.create_user(
            phone="09120000102", name="مدیر فروشگاه", is_staff=True
        )
        self.other_staff = User.objects.create_user(
            phone="09120000103", name="کارمند", is_staff=True
        )
        self.manager = User.objects.create_user(
            phone="09120000106",
            name="مدیر اجرایی",
            is_staff=True,
            is_manager_admin=True,
        )
        self.superuser = User.objects.create_superuser(
            phone="09120000104", password="x", name="سوپریوزر"
        )
        self.customer = User.objects.create_user(phone="09120000105")

    def client_for(self, user) -> APIClient:
        client = APIClient()
        client.force_authenticate(user)
        return client

    @property
    def denied_roles(self) -> dict:
        return {
            "anonymous": APIClient(),
            "customer": self.client_for(self.customer),
            "staff": self.client_for(self.staff),
            "other-staff": self.client_for(self.other_staff),
            "manager-admin": self.client_for(self.manager),
            "superuser": self.client_for(self.superuser),
        }


class SeoPanelAccessTests(SeoRoleTestMixin, TestCase):
    def test_seo_admin_can_use_every_seo_endpoint(self):
        client = self.client_for(self.seo_admin)
        for method, url, payload in SEO_ENDPOINTS:
            if url.endswith("/scan") and method == "post":
                continue  # اسکن به شبکه‌ی بیرونی می‌زند
            with self.subTest(method=method, url=url):
                response = call(client, method, url, payload)
                self.assertLess(response.status_code, 400, response.data)

    def test_page_inventory_search_is_server_paginated_and_normalized(self):
        category = Category.objects.create(slug="farming", title="کشاورزی")
        Product.objects.bulk_create(
            [
                Product(title=f"پمپ کشاورزی {index}", category=category, price=100)
                for index in range(25)
            ]
        )
        client = self.client_for(self.seo_admin)

        first = client.get(
            "/api/admin/seo/pages",
            {"type": "product", "search": "كشاورزي", "page": 1},
        )
        second = client.get(
            "/api/admin/seo/pages",
            {"type": "product", "search": "كشاورزي", "page": 2},
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["data"]["total"], 25)
        self.assertEqual(first.data["data"]["pagesCount"], 2)
        self.assertEqual(len(first.data["data"]["pages"]), 20)
        self.assertEqual(len(second.data["data"]["pages"]), 5)
        self.assertTrue(
            all(
                row["pageType"] == "product"
                for row in first.data["data"]["pages"]
            )
        )

    def test_page_inventory_rejects_malformed_search_parameters(self):
        client = self.client_for(self.seo_admin)

        too_long = client.get(
            "/api/admin/seo/pages", {"search": "x" * 201}
        )
        bad_type = client.get("/api/admin/seo/pages", {"type": "private"})
        huge_page = client.get(
            "/api/admin/seo/pages", {"page": "9" * 100}
        )

        self.assertEqual(too_long.status_code, 422)
        self.assertEqual(bad_type.status_code, 422)
        self.assertEqual(huge_page.status_code, 422)

    def test_every_other_role_is_rejected_from_every_seo_endpoint(self):
        for role, client in self.denied_roles.items():
            for method, url, payload in SEO_ENDPOINTS:
                with self.subTest(role=role, method=method, url=url):
                    response = call(client, method, url, payload)
                    self.assertEqual(response.status_code, 403)
                    self.assertFalse(response.data["ok"])

    def test_superuser_is_rejected_even_though_django_grants_all_perms(self):
        """سوپریوزر has_perm همیشه True است؛ پنل سئو نباید به آن تکیه کند"""
        self.assertTrue(self.superuser.has_perm("seo.change_seosettings"))
        response = self.client_for(self.superuser).get("/api/admin/seo/overview")
        self.assertEqual(response.status_code, 403)

    def test_rejected_write_leaves_data_untouched(self):
        """رد شدن فقط خواندن نیست — نوشتن هم واقعاً انجام نمی‌شود"""
        original = SeoSettings.load().site_name
        for role, client in self.denied_roles.items():
            with self.subTest(role=role):
                response = client.put(
                    "/api/admin/seo/settings",
                    {"siteName": f"دستکاری {role}"},
                    format="json",
                )
                self.assertEqual(response.status_code, 403)
        self.assertEqual(SeoSettings.load().site_name, original)
        self.assertFalse(Redirect.objects.exists())
        self.assertFalse(PageMeta.objects.exists())

    def test_anonymous_access_is_denied(self):
        response = APIClient().get("/api/admin/seo/overview")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.data["ok"])

    def test_inactive_seo_admin_is_denied(self):
        self.seo_admin.is_active = False
        self.seo_admin.save(update_fields=["is_active"])
        response = self.client_for(self.seo_admin).get("/api/admin/seo/overview")
        self.assertEqual(response.status_code, 403)

    def test_revoked_seo_admin_is_denied(self):
        self.seo_admin.is_seo_manager = False
        self.seo_admin.save(update_fields=["is_seo_manager"])
        response = self.client_for(self.seo_admin).get("/api/admin/seo/overview")
        self.assertEqual(response.status_code, 403)

    def test_deleted_seo_admin_session_is_denied(self):
        """نشستِ باز پس از حذف حساب باید بی‌اعتبار شود

        اینجا عمداً از نشست واقعی (force_login) استفاده می‌شود؛
        force_authenticate شیء کاربر را در حافظه نگه می‌دارد و حذف حساب را
        نشان نمی‌دهد.
        """
        self.client.force_login(self.seo_admin)
        self.assertEqual(
            self.client.get("/api/admin/seo/overview").status_code, 200
        )

        self.seo_admin.delete()
        response = self.client.get("/api/admin/seo/overview")
        self.assertEqual(response.status_code, 403)

    def test_inactive_seo_admin_session_is_denied(self):
        """غیرفعال‌سازی، نشست باز را هم می‌بندد"""
        self.client.force_login(self.seo_admin)
        self.assertEqual(
            self.client.get("/api/admin/seo/overview").status_code, 200
        )

        self.seo_admin.is_active = False
        self.seo_admin.save(update_fields=["is_active"])
        response = self.client.get("/api/admin/seo/overview")
        self.assertEqual(response.status_code, 403)

    def test_promoting_seo_admin_to_staff_swaps_the_accessible_area(self):
        """تغییر نقش بلافاصله دسترسی‌ها را جابه‌جا می‌کند"""
        client = self.client_for(self.seo_admin)
        self.assertEqual(client.get("/api/admin/seo/overview").status_code, 200)

        self.seo_admin.is_seo_manager = False
        self.seo_admin.is_staff = True
        self.seo_admin.save(update_fields=["is_seo_manager", "is_staff"])

        self.assertEqual(client.get("/api/admin/seo/overview").status_code, 403)
        self.assertEqual(client.get("/api/admin/stats").status_code, 200)


class SeoAdminBlockedFromShopDashboardTests(SeoRoleTestMixin, TestCase):
    def test_seo_admin_cannot_reach_any_shop_admin_endpoint(self):
        client = self.client_for(self.seo_admin)
        for method, url, payload in SHOP_ADMIN_ENDPOINTS:
            with self.subTest(method=method, url=url):
                response = call(client, method, url, payload)
                self.assertEqual(response.status_code, 403)
                self.assertFalse(response.data["ok"])

    def test_seo_admin_cannot_write_to_shop_admin_endpoints(self):
        client = self.client_for(self.seo_admin)
        response = client.post(
            "/api/admin/categories",
            {"slug": "hack", "title": "نفوذ"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_shop_admin_endpoints_still_work_for_staff(self):
        """سازگاری با گذشته: نقش‌های موجود دست‌نخورده مانده‌اند"""
        for user in (self.staff, self.manager, self.superuser):
            with self.subTest(user=user.name):
                client = self.client_for(user)
                for method, url, payload in SHOP_ADMIN_ENDPOINTS:
                    if url in ("/api/admin/seo-admins", "/api/admin/managers"):
                        continue  # ناحیه‌ی سیستمی — جدا تست می‌شود
                    with self.subTest(url=url):
                        response = call(client, method, url, payload)
                        self.assertEqual(response.status_code, 200)


class SeoPublicEndpointsTests(SeoRoleTestMixin, TestCase):
    """بستن پنل نباید مسیرهای عمومی سئو را خراب کند"""

    def test_public_seo_endpoints_stay_open(self):
        anonymous = APIClient()
        self.assertEqual(
            anonymous.get("/api/seo/meta?type=static&key=/").status_code, 200
        )
        self.assertEqual(
            anonymous.get("/api/seo/resolve?path=/nothing").status_code, 200
        )
        self.assertEqual(self.client.get("/robots.txt").status_code, 200)
        self.assertEqual(self.client.get("/sitemap.xml").status_code, 200)


class SeoRoleExclusivityTests(TestCase):
    """مدیر سئو و مدیر فروشگاه دو نقش ناسازگارند — در مدل و در دیتابیس"""

    def test_cannot_save_user_as_both_seo_admin_and_staff(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                phone="09120000201", is_staff=True, is_seo_manager=True
            )

    def test_cannot_save_user_as_both_seo_admin_and_superuser(self):
        with self.assertRaises(ValidationError):
            User.objects.create_superuser(
                phone="09120000202", password="x", is_seo_manager=True
            )

    def test_promoting_existing_seo_admin_to_staff_is_rejected(self):
        user = User.objects.create_user(phone="09120000203", is_seo_manager=True)
        user.is_staff = True
        with self.assertRaises(ValidationError):
            user.save(update_fields=["is_staff"])

    def test_database_constraint_blocks_bulk_update_bypass(self):
        """حتی دور زدن save() هم با قید دیتابیس متوقف می‌شود"""
        user = User.objects.create_user(phone="09120000204", is_seo_manager=True)
        with self.assertRaises(IntegrityError):
            User.objects.filter(pk=user.pk).update(is_staff=True)
