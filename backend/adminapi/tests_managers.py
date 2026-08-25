"""نقش «مدیر اجرایی»: دسترسی کسب‌وکار، مرز ناحیه‌ی سیستمی، و ضد ارتقای نقش

سه چیز اینجا سنجیده می‌شود:
1. مدیر اجرایی واقعاً کل داشبورد کسب‌وکار را دارد؛
2. هیچ‌کدام از ناحیه‌های سطح‌سیستم (ساخت نقش ممتاز، ادمین جنگو، پنل سئو) را ندارد؛
3. از هیچ مسیری نمی‌تواند نقش خودش یا دیگری را ارتقا دهد.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError
from django.test import TestCase
from rest_framework.test import APIClient

User = get_user_model()

MANAGERS_URL = "/api/admin/managers"
SEO_ADMINS_URL = "/api/admin/seo-admins"

# داشبورد کسب‌وکار — مدیر اجرایی باید همه‌ی این‌ها را داشته باشد
BUSINESS_ENDPOINTS = [
    "/api/admin/stats",
    "/api/admin/orders",
    "/api/admin/users",
    "/api/admin/products",
    "/api/admin/categories",
    "/api/admin/brands",
    "/api/admin/specifications",
    "/api/admin/comments",
    "/api/admin/blog/posts",
    "/api/admin/home/sections",
    "/api/admin/content/pages",
]

# ناحیه‌ی توسعه‌دهنده/سیستمی — فقط سوپریوزر
DEVELOPER_ENDPOINTS = [MANAGERS_URL, SEO_ADMINS_URL]


class ManagerAdminRoleTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            phone="09120000601", password="x", name="مدیر سیستم"
        )
        self.manager = User.objects.create_user(
            phone="09120000602",
            name="مدیر اجرایی",
            is_staff=True,
            is_manager_admin=True,
        )
        self.staff = User.objects.create_user(
            phone="09120000603", name="کارمند", is_staff=True
        )
        self.seo_admin = User.objects.create_user(
            phone="09120000604", name="مدیر سئو", is_seo_manager=True
        )
        self.customer = User.objects.create_user(phone="09120000605")
        self.root = self.client_for(self.superuser)

    def client_for(self, user) -> APIClient:
        client = APIClient()
        client.force_authenticate(user)
        return client

    @property
    def non_developer_roles(self) -> dict:
        return {
            "anonymous": APIClient(),
            "customer": self.client_for(self.customer),
            "staff": self.client_for(self.staff),
            "manager-admin": self.client_for(self.manager),
            "seo-admin": self.client_for(self.seo_admin),
        }

    # ─── دسترسی کسب‌وکار ─────────────────────────────────────

    def test_manager_admin_can_use_the_whole_business_dashboard(self):
        client = self.client_for(self.manager)
        for url in BUSINESS_ENDPOINTS:
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, 200)

    def test_manager_admin_can_write_business_data(self):
        response = self.client_for(self.manager).post(
            "/api/admin/categories",
            {"slug": "manager-made", "title": "دسته‌ی مدیر"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_customer_and_anonymous_cannot_reach_the_business_dashboard(self):
        for role, client in {
            "anonymous": APIClient(),
            "customer": self.client_for(self.customer),
            "seo-admin": self.client_for(self.seo_admin),
        }.items():
            for url in BUSINESS_ENDPOINTS:
                with self.subTest(role=role, url=url):
                    self.assertEqual(client.get(url).status_code, 403)

    # ─── مرز ناحیه‌ی سئو ─────────────────────────────────────

    def test_manager_admin_cannot_reach_the_seo_panel(self):
        client = self.client_for(self.manager)
        for url in (
            "/api/admin/seo/overview",
            "/api/admin/seo/settings",
            "/api/admin/seo/redirects",
        ):
            with self.subTest(url=url):
                response = client.get(url)
                self.assertEqual(response.status_code, 403)
                self.assertFalse(response.data["ok"])

    def test_existing_seo_rule_is_unchanged(self):
        """قاعده‌ی قبلی دست‌نخورده: سوپریوزر نه، مدیر سئو بله"""
        self.assertEqual(
            self.root.get("/api/admin/seo/overview").status_code, 403
        )
        self.assertEqual(
            self.client_for(self.seo_admin)
            .get("/api/admin/seo/overview")
            .status_code,
            200,
        )

    # ─── ناحیه‌ی توسعه‌دهنده ─────────────────────────────────

    def test_only_the_superuser_reaches_developer_endpoints(self):
        for url in DEVELOPER_ENDPOINTS:
            with self.subTest(url=url, role="superuser"):
                self.assertEqual(self.root.get(url).status_code, 200)
        for role, client in self.non_developer_roles.items():
            for url in DEVELOPER_ENDPOINTS:
                with self.subTest(url=url, role=role):
                    response = client.get(url)
                    self.assertEqual(response.status_code, 403)
                    self.assertFalse(response.data["ok"])

    def test_django_admin_is_developer_only(self):
        """ادمین جنگو (جدول کاربران، OTP، گروه‌ها) ناحیه‌ی سیستمی است"""
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get("/admin/").status_code, 200)

        for user in (self.manager, self.staff):
            with self.subTest(user=user.name):
                self.client.force_login(user)
                response = self.client.get("/admin/")
                # ادمین جنگو به‌جای نمایش، به صفحه‌ی ورودش ریدایرکت می‌کند
                self.assertEqual(response.status_code, 302)
                self.assertIn("/admin/login", response["Location"])

    # ─── ساخت نقش ممتاز ──────────────────────────────────────

    def test_superuser_can_create_a_manager_admin(self):
        response = self.root.post(
            MANAGERS_URL,
            {"phone": "09121230101", "name": "مدیر تازه"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        created = User.objects.get(phone="09121230101")
        self.assertTrue(created.is_manager_admin)
        self.assertTrue(created.is_staff)
        self.assertFalse(created.is_superuser)
        self.assertFalse(created.is_seo_manager)

    def test_created_manager_admin_gets_business_access_only(self):
        self.root.post(MANAGERS_URL, {"phone": "09121230102"}, format="json")
        client = self.client_for(User.objects.get(phone="09121230102"))
        self.assertEqual(client.get("/api/admin/orders").status_code, 200)
        self.assertEqual(client.get("/api/admin/seo/overview").status_code, 403)
        self.assertEqual(client.get(MANAGERS_URL).status_code, 403)

    def test_nobody_else_can_create_a_manager_admin(self):
        for role, client in self.non_developer_roles.items():
            with self.subTest(role=role):
                response = client.post(
                    MANAGERS_URL, {"phone": "09129990100"}, format="json"
                )
                self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(phone="09129990100").exists())

    def test_manager_admin_cannot_create_a_seo_admin(self):
        response = self.client_for(self.manager).post(
            SEO_ADMINS_URL, {"phone": "09129990101"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(phone="09129990101").exists())

    def test_manager_admin_cannot_create_another_manager_admin(self):
        response = self.client_for(self.manager).post(
            MANAGERS_URL, {"phone": "09129990102"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(phone="09129990102").exists())

    def test_seo_admin_cannot_create_a_manager_admin(self):
        response = self.client_for(self.seo_admin).post(
            MANAGERS_URL, {"phone": "09129990103"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(phone="09129990103").exists())

    def test_superuser_phone_cannot_become_a_manager_admin(self):
        response = self.root.post(
            MANAGERS_URL, {"phone": self.superuser.phone}, format="json"
        )
        self.assertEqual(response.status_code, 409)
        self.superuser.refresh_from_db()
        self.assertFalse(self.superuser.is_manager_admin)

    def test_seo_admin_phone_cannot_become_a_manager_admin(self):
        response = self.root.post(
            MANAGERS_URL, {"phone": self.seo_admin.phone}, format="json"
        )
        self.assertEqual(response.status_code, 409)
        self.seo_admin.refresh_from_db()
        self.assertFalse(self.seo_admin.is_manager_admin)
        self.assertTrue(self.seo_admin.is_seo_manager)

    def test_manager_admin_phone_cannot_become_a_seo_admin(self):
        response = self.root.post(
            SEO_ADMINS_URL, {"phone": self.manager.phone}, format="json"
        )
        self.assertEqual(response.status_code, 409)
        self.manager.refresh_from_db()
        self.assertFalse(self.manager.is_seo_manager)
        self.assertTrue(self.manager.is_manager_admin)

    def test_existing_staff_is_promoted_and_keeps_the_account(self):
        response = self.root.post(
            MANAGERS_URL, {"phone": self.staff.phone}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.is_manager_admin)
        self.assertTrue(self.staff.is_staff)

    def test_duplicate_manager_admin_is_rejected(self):
        response = self.root.post(
            MANAGERS_URL, {"phone": self.manager.phone}, format="json"
        )
        self.assertEqual(response.status_code, 409)

    # ─── ویرایش و لغو ────────────────────────────────────────

    def test_superuser_can_edit_and_deactivate_a_manager_admin(self):
        detail = f"{MANAGERS_URL}/{self.manager.id}"
        self.assertEqual(
            self.root.patch(
                detail, {"name": "نام تازه"}, format="json"
            ).status_code,
            200,
        )
        self.assertEqual(
            self.root.patch(
                detail, {"isActive": False}, format="json"
            ).status_code,
            200,
        )
        self.manager.refresh_from_db()
        self.assertEqual(self.manager.name, "نام تازه")
        self.assertFalse(self.manager.is_active)
        self.assertEqual(
            self.client_for(self.manager).get("/api/admin/orders").status_code,
            403,
        )

    def test_revoking_keeps_the_account_but_closes_the_dashboard(self):
        response = self.root.delete(f"{MANAGERS_URL}/{self.manager.id}")
        self.assertEqual(response.status_code, 200, response.data)
        self.manager.refresh_from_db()
        self.assertFalse(self.manager.is_manager_admin)
        self.assertFalse(self.manager.is_staff)
        self.assertTrue(self.manager.is_active)
        self.assertEqual(
            self.client_for(self.manager).get("/api/admin/orders").status_code,
            403,
        )

    def test_manager_admin_cannot_edit_or_revoke_privileged_accounts(self):
        client = self.client_for(self.manager)
        for url in (
            f"{MANAGERS_URL}/{self.manager.id}",
            f"{SEO_ADMINS_URL}/{self.seo_admin.id}",
        ):
            with self.subTest(url=url):
                self.assertEqual(
                    client.patch(
                        url, {"isActive": False}, format="json"
                    ).status_code,
                    403,
                )
                self.assertEqual(client.delete(url).status_code, 403)
        self.manager.refresh_from_db()
        self.seo_admin.refresh_from_db()
        self.assertTrue(self.manager.is_active)
        self.assertTrue(self.seo_admin.is_seo_manager)


class PrivilegeEscalationTests(TestCase):
    """مدیر اجرایی نباید از هیچ مسیری نقش بگیرد یا نقش بدهد"""

    def setUp(self):
        self.manager = User.objects.create_user(
            phone="09120000701",
            name="مدیر اجرایی",
            is_staff=True,
            is_manager_admin=True,
        )
        self.victim = User.objects.create_user(phone="09120000702")
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.manager)

    def test_profile_patch_ignores_injected_role_fields(self):
        """اندپوینت پروفایل فقط نام را می‌پذیرد و بقیه را دور می‌ریزد"""
        response = self.client_api.patch(
            "/api/auth/profile",
            {
                "name": "مدیر",
                "is_superuser": True,
                "isSuperuser": True,
                "is_staff": True,
                "is_seo_manager": True,
                "is_manager_admin": True,
                "user_type": "seo-admin",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.manager.refresh_from_db()
        self.assertFalse(self.manager.is_superuser)
        self.assertFalse(self.manager.is_seo_manager)
        self.assertTrue(self.manager.is_manager_admin)

    def test_role_payloads_on_privileged_endpoints_are_refused(self):
        """حتی با دست‌کاری بدنه‌ی درخواست، مجوز پیش از هر چیز رد می‌کند"""
        attempts = [
            (MANAGERS_URL, {"phone": "09129991000", "user_type": "manager-admin"}),
            (SEO_ADMINS_URL, {"phone": "09129991001", "user_type": "seo-admin"}),
            (
                MANAGERS_URL,
                {"phone": self.manager.phone, "isSuperuser": True},
            ),
        ]
        for url, payload in attempts:
            with self.subTest(url=url, payload=payload):
                response = self.client_api.post(url, payload, format="json")
                self.assertEqual(response.status_code, 403)
        self.manager.refresh_from_db()
        self.assertFalse(self.manager.is_superuser)
        self.assertFalse(User.objects.filter(phone="09129991000").exists())
        self.assertFalse(User.objects.filter(phone="09129991001").exists())

    def test_manager_admin_cannot_promote_another_user(self):
        for url in (MANAGERS_URL, SEO_ADMINS_URL):
            with self.subTest(url=url):
                response = self.client_api.post(
                    url, {"phone": self.victim.phone}, format="json"
                )
                self.assertEqual(response.status_code, 403)
        self.victim.refresh_from_db()
        self.assertFalse(self.victim.is_manager_admin)
        self.assertFalse(self.victim.is_seo_manager)
        self.assertFalse(self.victim.is_staff)

    def test_user_listing_is_read_only(self):
        """فهرست کاربران هیچ مسیر نوشتنی ندارد که بتوان نقش را از آن عوض کرد"""
        for method in ("post", "patch", "put", "delete"):
            with self.subTest(method=method):
                handler = getattr(self.client_api, method)
                response = handler(
                    "/api/admin/users",
                    {"id": self.victim.id, "isStaff": True},
                    format="json",
                )
                self.assertEqual(response.status_code, 405)
        self.victim.refresh_from_db()
        self.assertFalse(self.victim.is_staff)


class ManagerRoleInvariantTests(TestCase):
    """قیدهای مدل: مدیر اجرایی همیشه staff است و هرگز سوپریوزر/سئو نیست"""

    def test_manager_admin_cannot_be_superuser(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                phone="09120000801",
                is_staff=True,
                is_superuser=True,
                is_manager_admin=True,
            )

    def test_manager_admin_must_be_staff(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                phone="09120000802", is_manager_admin=True
            )

    def test_manager_admin_cannot_be_seo_manager(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                phone="09120000803",
                is_staff=True,
                is_manager_admin=True,
                is_seo_manager=True,
            )

    def test_database_constraint_blocks_bulk_update_bypass(self):
        """دور زدن save() هم با قید دیتابیس متوقف می‌شود"""
        manager = User.objects.create_user(
            phone="09120000804", is_staff=True, is_manager_admin=True
        )
        for payload in ({"is_superuser": True}, {"is_staff": False}):
            # هر تلاش اتمیک خودش را دارد: خطای قید، تراکنش را می‌شکند
            with self.subTest(payload=payload):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    User.objects.filter(pk=manager.pk).update(**payload)
