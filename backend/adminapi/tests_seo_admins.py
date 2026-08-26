"""مدیریت حساب‌های «مدیر سئو» — فقط سوپریوزر

ساخت/ویرایش/فعال‌سازی مدیر سئو یک عملیات مدیریتیِ حساس است؛ این تست‌ها هم
جدول دسترسی و هم اثر واقعی هر عملیات روی دیتابیس را می‌سنجند.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

User = get_user_model()

LIST_URL = "/api/admin/seo-admins"


class SeoAdminManagementTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            phone="09120000301", password="x", name="سوپریوزر"
        )
        self.staff = User.objects.create_user(
            phone="09120000302", name="مدیر فروشگاه", is_staff=True
        )
        self.seo_admin = User.objects.create_user(
            phone="09120000303", name="مدیر سئو", is_seo_manager=True
        )
        self.customer = User.objects.create_user(phone="09120000304")
        self.root = self.client_for(self.superuser)

    def client_for(self, user) -> APIClient:
        client = APIClient()
        client.force_authenticate(user)
        return client

    @property
    def forbidden_roles(self) -> dict:
        return {
            "anonymous": APIClient(),
            "customer": self.client_for(self.customer),
            "staff": self.client_for(self.staff),
            "seo-admin": self.client_for(self.seo_admin),
        }

    # ─── ساخت ────────────────────────────────────────────────

    def test_superuser_can_create_seo_admin(self):
        response = self.root.post(
            LIST_URL,
            {"phone": "09121110001", "name": "سئوکار تازه"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        created = User.objects.get(phone="09121110001")
        self.assertTrue(created.is_seo_manager)
        self.assertFalse(created.is_staff)
        self.assertFalse(created.is_superuser)
        self.assertEqual(response.data["data"]["seoAdmin"]["name"], "سئوکار تازه")

    def test_created_seo_admin_can_use_the_seo_panel_immediately(self):
        self.root.post(LIST_URL, {"phone": "09121110002"}, format="json")
        created = User.objects.get(phone="09121110002")
        client = self.client_for(created)
        self.assertEqual(
            client.get("/api/admin/seo/overview").status_code, 200
        )
        self.assertEqual(client.get("/api/admin/stats").status_code, 403)

    def test_phone_is_normalized_before_creating(self):
        response = self.root.post(
            LIST_URL, {"phone": "+989121110003"}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(User.objects.filter(phone="09121110003").exists())

    def test_invalid_phone_is_rejected(self):
        response = self.root.post(LIST_URL, {"phone": "12345"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["ok"])

    def test_existing_customer_is_promoted_and_keeps_the_account(self):
        response = self.root.post(
            LIST_URL,
            {"phone": self.customer.phone, "name": "مشتری ارتقایافته"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_seo_manager)
        self.assertEqual(self.customer.name, "مشتری ارتقایافته")

    def test_shop_admin_phone_cannot_become_seo_admin(self):
        response = self.root.post(
            LIST_URL, {"phone": self.staff.phone}, format="json"
        )
        self.assertEqual(response.status_code, 409)
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_seo_manager)
        self.assertTrue(self.staff.is_staff)

    def test_superuser_phone_cannot_become_seo_admin(self):
        response = self.root.post(
            LIST_URL, {"phone": self.superuser.phone}, format="json"
        )
        self.assertEqual(response.status_code, 409)
        self.superuser.refresh_from_db()
        self.assertFalse(self.superuser.is_seo_manager)

    def test_duplicate_seo_admin_is_rejected(self):
        response = self.root.post(
            LIST_URL, {"phone": self.seo_admin.phone}, format="json"
        )
        self.assertEqual(response.status_code, 409)

    # ─── جدول دسترسی ─────────────────────────────────────────

    def test_only_superuser_may_create_a_seo_admin(self):
        for role, client in self.forbidden_roles.items():
            with self.subTest(role=role):
                response = client.post(
                    LIST_URL, {"phone": "09129990000"}, format="json"
                )
                self.assertEqual(response.status_code, 403)
                self.assertFalse(response.data["ok"])
        self.assertFalse(User.objects.filter(phone="09129990000").exists())

    def test_only_superuser_may_list_edit_or_revoke(self):
        detail = f"{LIST_URL}/{self.seo_admin.id}"
        for role, client in self.forbidden_roles.items():
            with self.subTest(role=role):
                self.assertEqual(client.get(LIST_URL).status_code, 403)
                self.assertEqual(
                    client.patch(
                        detail, {"name": "دستکاری"}, format="json"
                    ).status_code,
                    403,
                )
                self.assertEqual(client.delete(detail).status_code, 403)
        self.seo_admin.refresh_from_db()
        self.assertTrue(self.seo_admin.is_seo_manager)
        self.assertEqual(self.seo_admin.name, "مدیر سئو")

    def test_seo_admin_cannot_create_another_seo_admin(self):
        response = self.client_for(self.seo_admin).post(
            LIST_URL, {"phone": "09129990001"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(phone="09129990001").exists())

    # ─── فهرست ───────────────────────────────────────────────

    def test_list_returns_only_seo_admins(self):
        response = self.root.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        phones = [row["phone"] for row in response.data["data"]["seoAdmins"]]
        self.assertEqual(phones, [self.seo_admin.phone])

    # ─── ویرایش و وضعیت ──────────────────────────────────────

    def test_superuser_can_edit_name_and_phone(self):
        response = self.root.patch(
            f"{LIST_URL}/{self.seo_admin.id}",
            {"name": "نام تازه", "phone": "09121110009"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.seo_admin.refresh_from_db()
        self.assertEqual(self.seo_admin.name, "نام تازه")
        self.assertEqual(self.seo_admin.phone, "09121110009")

    def test_editing_to_a_taken_phone_is_rejected(self):
        response = self.root.patch(
            f"{LIST_URL}/{self.seo_admin.id}",
            {"phone": self.customer.phone},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.seo_admin.refresh_from_db()
        self.assertEqual(self.seo_admin.phone, "09120000303")

    def test_empty_patch_is_rejected(self):
        response = self.root.patch(
            f"{LIST_URL}/{self.seo_admin.id}", {}, format="json"
        )
        self.assertEqual(response.status_code, 422)

    def test_deactivating_a_seo_admin_closes_the_seo_panel(self):
        client = self.client_for(self.seo_admin)
        self.assertEqual(
            client.get("/api/admin/seo/overview").status_code, 200
        )

        response = self.root.patch(
            f"{LIST_URL}/{self.seo_admin.id}", {"isActive": False}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.seo_admin.refresh_from_db()
        self.assertFalse(self.seo_admin.is_active)
        self.assertEqual(
            self.client_for(self.seo_admin)
            .get("/api/admin/seo/overview")
            .status_code,
            403,
        )

    def test_reactivating_restores_access(self):
        self.seo_admin.is_active = False
        self.seo_admin.save(update_fields=["is_active"])
        self.root.patch(
            f"{LIST_URL}/{self.seo_admin.id}", {"isActive": True}, format="json"
        )
        self.seo_admin.refresh_from_db()
        self.assertTrue(self.seo_admin.is_active)
        self.assertEqual(
            self.client_for(self.seo_admin)
            .get("/api/admin/seo/overview")
            .status_code,
            200,
        )

    # ─── لغو نقش ─────────────────────────────────────────────

    def test_revoking_keeps_the_account_but_closes_the_seo_panel(self):
        response = self.root.delete(f"{LIST_URL}/{self.seo_admin.id}")
        self.assertEqual(response.status_code, 200, response.data)
        self.seo_admin.refresh_from_db()
        self.assertFalse(self.seo_admin.is_seo_manager)
        self.assertTrue(self.seo_admin.is_active)  # حساب حذف نمی‌شود
        self.assertEqual(
            self.client_for(self.seo_admin)
            .get("/api/admin/seo/overview")
            .status_code,
            403,
        )

    def test_managing_a_non_seo_user_returns_404(self):
        for method in ("patch", "delete"):
            with self.subTest(method=method):
                url = f"{LIST_URL}/{self.customer.id}"
                response = (
                    self.root.patch(url, {"name": "x"}, format="json")
                    if method == "patch"
                    else self.root.delete(url)
                )
                self.assertEqual(response.status_code, 404)
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_seo_manager)
