"""تست‌های مجوز مدیریت کاربران — جدول توانایی‌ها به‌صورت اجرایی

هر تست یک سطر از جدول §۲۷ صورت‌مسئله را می‌بندد. اصل کار روی «حمله‌ی مستقیم به
API» است نه رفتار UI: هر جا فرانت چیزی را پنهان می‌کند، اینجا همان درخواست
دست‌ساز فرستاده می‌شود تا مطمئن شویم بک‌اند خودش رد می‌کند.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.roles import Role
from orders.models import Order

User = get_user_model()

USERS_URL = "/api/admin/users"
SEO_URL = "/api/admin/seo/overview"
SEO_ADMINS_URL = "/api/admin/seo-admins"
MANAGERS_URL = "/api/admin/managers"


class RoleFixtureMixin:
    """یک نمونه از هر نقش + کلاینت احرازشده"""

    def setUp(self):
        super().setUp()
        self.superuser = User.objects.create_superuser(
            phone="09120001001", password="x", name="مدیر سیستم"
        )
        self.manager = User.objects.create_user(
            phone="09120001002",
            name="مدیر اجرایی",
            is_staff=True,
            is_manager_admin=True,
        )
        self.seo_manager = User.objects.create_user(
            phone="09120001003",
            name="مدیر اجرایی با سئو",
            is_staff=True,
            is_manager_admin=True,
            can_access_seo=True,
        )
        self.regular = User.objects.create_user(
            phone="09120001004", name="مدیر عادی", is_staff=True
        )
        self.seo_admin = User.objects.create_user(
            phone="09120001005", name="مدیر سئو", is_seo_manager=True
        )
        self.customer = User.objects.create_user(
            phone="09120001006", name="مشتری"
        )

    def client_for(self, user) -> APIClient:
        client = APIClient()
        client.force_authenticate(user)
        return client

    def create_user_as(self, actor, phone: str, role: Role, **extra):
        return self.client_for(actor).post(
            USERS_URL, {"phone": phone, "role": role.value, **extra}, format="json"
        )

    def listed_phones(self, actor, **params) -> list[str]:
        response = self.client_for(actor).get(USERS_URL, params)
        self.assertEqual(response.status_code, 200, response.data)
        return [row["phone"] for row in response.json()["data"]["users"]]


# ─── ۱. مدیر سیستم ───────────────────────────────────────────


class SuperuserCapabilityTests(RoleFixtureMixin, TestCase):
    def test_sees_every_user_including_other_superusers(self):
        other_root = User.objects.create_superuser(
            phone="09120001007", password="x"
        )
        phones = self.listed_phones(self.superuser)
        self.assertIn(other_root.phone, phones)
        self.assertIn(self.manager.phone, phones)
        self.assertIn(self.seo_admin.phone, phones)
        self.assertIn(self.customer.phone, phones)

    def test_can_create_every_role(self):
        cases = {
            "09120002001": Role.SUPERUSER,
            "09120002002": Role.MANAGER_ADMIN,
            "09120002003": Role.REGULAR_ADMIN,
            "09120002004": Role.SEO_ADMIN,
            "09120002005": Role.CUSTOMER,
        }
        for phone, role in cases.items():
            with self.subTest(role=role.value):
                response = self.create_user_as(self.superuser, phone, role)
                self.assertEqual(response.status_code, 201, response.data)
                self.assertEqual(response.json()["data"]["user"]["role"], role.value)

    def test_created_superuser_really_is_a_django_superuser(self):
        self.create_user_as(self.superuser, "09120002006", Role.SUPERUSER)
        created = User.objects.get(phone="09120002006")
        self.assertTrue(created.is_superuser)
        self.assertTrue(created.is_staff)

    def test_can_change_any_role(self):
        response = self.client_for(self.superuser).patch(
            f"{USERS_URL}/{self.customer.pk}",
            {"role": Role.MANAGER_ADMIN.value},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_manager_admin)
        self.assertTrue(self.customer.is_staff)

    def test_can_grant_and_revoke_manager_seo_access(self):
        client = self.client_for(self.superuser)
        granted = client.patch(
            f"{MANAGERS_URL}/{self.manager.pk}",
            {"canAccessSeo": True},
            format="json",
        )
        self.assertEqual(granted.status_code, 200, granted.data)
        self.manager.refresh_from_db()
        self.assertTrue(self.manager.can_access_seo)

        revoked = client.patch(
            f"{MANAGERS_URL}/{self.manager.pk}",
            {"canAccessSeo": False},
            format="json",
        )
        self.assertEqual(revoked.status_code, 200, revoked.data)
        self.manager.refresh_from_db()
        self.assertFalse(self.manager.can_access_seo)

    def test_can_reach_seo_and_dashboard_apis(self):
        client = self.client_for(self.superuser)
        self.assertEqual(client.get(SEO_URL).status_code, 200)
        self.assertEqual(client.get("/api/admin/stats").status_code, 200)

    def test_can_delete_a_user(self):
        response = self.client_for(self.superuser).delete(
            f"{USERS_URL}/{self.customer.pk}"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(User.objects.filter(pk=self.customer.pk).exists())

    def test_cannot_delete_or_demote_their_own_account(self):
        """محافظت از قفل‌شدن سیستم: آخرین در پشت سر خودش بسته نمی‌شود"""
        client = self.client_for(self.superuser)
        self.assertEqual(
            client.delete(f"{USERS_URL}/{self.superuser.pk}").status_code, 403
        )
        demote = client.patch(
            f"{USERS_URL}/{self.superuser.pk}",
            {"role": Role.CUSTOMER.value},
            format="json",
        )
        self.assertEqual(demote.status_code, 403)
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_superuser)


# ─── ۲. مدیر اجرایی بدون دسترسی سئو ──────────────────────────


class ManagerWithoutSeoTests(RoleFixtureMixin, TestCase):
    def test_can_use_normal_dashboard(self):
        self.assertEqual(
            self.client_for(self.manager).get("/api/admin/stats").status_code, 200
        )

    def test_cannot_reach_seo_endpoints(self):
        self.assertEqual(
            self.client_for(self.manager).get(SEO_URL).status_code, 403
        )

    def test_cannot_create_a_seo_admin(self):
        response = self.create_user_as(self.manager, "09120003001", Role.SEO_ADMIN)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(phone="09120003001").exists())

    def test_cannot_use_the_seo_admin_management_endpoint(self):
        client = self.client_for(self.manager)
        self.assertEqual(client.get(SEO_ADMINS_URL).status_code, 403)
        created = client.post(
            SEO_ADMINS_URL, {"phone": "09120003002"}, format="json"
        )
        self.assertEqual(created.status_code, 403)
        self.assertFalse(User.objects.filter(phone="09120003002").exists())

    def test_cannot_grant_seo_access_to_themselves(self):
        client = self.client_for(self.manager)
        # نه از مسیر مدیریت مدیران (کلاً بسته است)...
        self.assertEqual(
            client.patch(
                f"{MANAGERS_URL}/{self.manager.pk}",
                {"canAccessSeo": True},
                format="json",
            ).status_code,
            403,
        )
        # ...نه از مسیر مدیریت کاربران (خودش اصلاً در دیدش نیست)
        self.assertEqual(
            client.patch(
                f"{USERS_URL}/{self.manager.pk}",
                {"canAccessSeo": True},
                format="json",
            ).status_code,
            404,
        )
        self.manager.refresh_from_db()
        self.assertFalse(self.manager.can_access_seo)

    def test_cannot_create_a_manager_admin(self):
        response = self.create_user_as(
            self.manager, "09120003003", Role.MANAGER_ADMIN
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(phone="09120003003").exists())

    def test_cannot_create_a_superuser(self):
        response = self.create_user_as(
            self.manager, "09120003004", Role.SUPERUSER
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(phone="09120003004").exists())

    def test_cannot_see_superuser_accounts(self):
        self.assertNotIn(self.superuser.phone, self.listed_phones(self.manager))

    def test_direct_superuser_lookup_returns_not_found(self):
        """۴۰۴ عمدی است: وجود حساب ممتاز هم نباید فاش شود"""
        response = self.client_for(self.manager).get(
            f"{USERS_URL}/{self.superuser.pk}"
        )
        self.assertEqual(response.status_code, 404)

    def test_direct_superuser_write_is_refused(self):
        client = self.client_for(self.manager)
        for method, payload in (
            ("patch", {"name": "دستکاری"}),
            ("delete", None),
        ):
            with self.subTest(method=method):
                handler = getattr(client, method)
                response = (
                    handler(f"{USERS_URL}/{self.superuser.pk}")
                    if payload is None
                    else handler(
                        f"{USERS_URL}/{self.superuser.pk}", payload, format="json"
                    )
                )
                self.assertEqual(response.status_code, 404)
        self.superuser.refresh_from_db()
        self.assertEqual(self.superuser.name, "مدیر سیستم")

    def test_can_create_a_regular_admin(self):
        response = self.create_user_as(
            self.manager, "09120003005", Role.REGULAR_ADMIN
        )
        self.assertEqual(response.status_code, 201, response.data)
        created = User.objects.get(phone="09120003005")
        self.assertTrue(created.is_staff)
        self.assertFalse(created.is_manager_admin)
        self.assertFalse(created.is_superuser)

    def test_can_create_a_customer(self):
        response = self.create_user_as(
            self.manager, "09120003006", Role.CUSTOMER
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(User.objects.get(phone="09120003006").is_staff)

    def test_can_deactivate_a_customer_but_not_delete(self):
        client = self.client_for(self.manager)
        deactivated = client.patch(
            f"{USERS_URL}/{self.customer.pk}", {"isActive": False}, format="json"
        )
        self.assertEqual(deactivated.status_code, 200, deactivated.data)
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)

        deleted = client.delete(f"{USERS_URL}/{self.customer.pk}")
        self.assertEqual(deleted.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.customer.pk).exists())


# ─── ۳. مدیر اجرایی با دسترسی سئو ────────────────────────────


class ManagerWithSeoTests(RoleFixtureMixin, TestCase):
    def test_can_reach_seo_endpoints(self):
        self.assertEqual(
            self.client_for(self.seo_manager).get(SEO_URL).status_code, 200
        )

    def test_can_create_a_seo_admin(self):
        response = self.create_user_as(
            self.seo_manager, "09120004001", Role.SEO_ADMIN
        )
        self.assertEqual(response.status_code, 201, response.data)
        created = User.objects.get(phone="09120004001")
        self.assertTrue(created.is_seo_manager)
        self.assertFalse(created.is_staff)

    def test_can_manage_seo_admin_accounts(self):
        client = self.client_for(self.seo_manager)
        self.assertEqual(client.get(SEO_ADMINS_URL).status_code, 200)
        renamed = client.patch(
            f"{SEO_ADMINS_URL}/{self.seo_admin.pk}",
            {"name": "سارا"},
            format="json",
        )
        self.assertEqual(renamed.status_code, 200, renamed.data)

    def test_still_cannot_create_a_manager_admin(self):
        response = self.create_user_as(
            self.seo_manager, "09120004002", Role.MANAGER_ADMIN
        )
        self.assertEqual(response.status_code, 403)

    def test_still_cannot_create_a_superuser(self):
        response = self.create_user_as(
            self.seo_manager, "09120004003", Role.SUPERUSER
        )
        self.assertEqual(response.status_code, 403)

    def test_cannot_grant_seo_access_to_another_manager(self):
        client = self.client_for(self.seo_manager)
        self.assertEqual(
            client.patch(
                f"{MANAGERS_URL}/{self.manager.pk}",
                {"canAccessSeo": True},
                format="json",
            ).status_code,
            403,
        )
        # مدیر اجرایی دیگر اصلاً در دید او نیست
        self.assertEqual(
            client.patch(
                f"{USERS_URL}/{self.manager.pk}",
                {"canAccessSeo": True},
                format="json",
            ).status_code,
            404,
        )
        self.manager.refresh_from_db()
        self.assertFalse(self.manager.can_access_seo)

    def test_cannot_create_a_manager_with_seo_access_prefilled(self):
        """حتی اگر canAccessSeo را در بدنه‌ی ساخت جا بدهد"""
        response = self.create_user_as(
            self.seo_manager,
            "09120004004",
            Role.REGULAR_ADMIN,
            canAccessSeo=True,
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(phone="09120004004").exists())

    def test_still_cannot_see_or_modify_superusers(self):
        self.assertNotIn(
            self.superuser.phone, self.listed_phones(self.seo_manager)
        )
        self.assertEqual(
            self.client_for(self.seo_manager)
            .get(f"{USERS_URL}/{self.superuser.pk}")
            .status_code,
            404,
        )


# ─── ۴. مدیر عادی ────────────────────────────────────────────


class RegularAdminTests(RoleFixtureMixin, TestCase):
    def test_sees_only_customers(self):
        self.assertEqual(
            self.listed_phones(self.regular), [self.customer.phone]
        )

    def test_cannot_see_any_admin_account(self):
        for hidden in (
            self.superuser,
            self.manager,
            self.seo_manager,
            self.seo_admin,
        ):
            with self.subTest(phone=hidden.phone):
                self.assertEqual(
                    self.client_for(self.regular)
                    .get(f"{USERS_URL}/{hidden.pk}")
                    .status_code,
                    404,
                )

    def test_cannot_see_other_regular_admins(self):
        other = User.objects.create_user(phone="09120005001", is_staff=True)
        self.assertNotIn(other.phone, self.listed_phones(self.regular))

    def test_can_create_a_customer(self):
        response = self.create_user_as(
            self.regular, "09120005002", Role.CUSTOMER
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_cannot_create_any_admin_role(self):
        cases = {
            "09120005003": Role.SUPERUSER,
            "09120005004": Role.MANAGER_ADMIN,
            "09120005005": Role.REGULAR_ADMIN,
            "09120005006": Role.SEO_ADMIN,
        }
        for phone, role in cases.items():
            with self.subTest(role=role.value):
                response = self.create_user_as(self.regular, phone, role)
                self.assertEqual(response.status_code, 403)
                self.assertFalse(User.objects.filter(phone=phone).exists())

    def test_cannot_delete_a_customer(self):
        response = self.client_for(self.regular).delete(
            f"{USERS_URL}/{self.customer.pk}"
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.customer.pk).exists())

    def test_cannot_deactivate_a_customer(self):
        """قاعده‌ی کسب‌وکاری‌ای برای این کار وجود ندارد، پس بسته است"""
        response = self.client_for(self.regular).patch(
            f"{USERS_URL}/{self.customer.pk}", {"isActive": False}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_active)

    def test_can_edit_basic_customer_information(self):
        response = self.client_for(self.regular).patch(
            f"{USERS_URL}/{self.customer.pk}", {"name": "نام تازه"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.name, "نام تازه")

    def test_cannot_change_a_customer_role(self):
        for role in (Role.REGULAR_ADMIN, Role.MANAGER_ADMIN, Role.SUPERUSER):
            with self.subTest(role=role.value):
                response = self.client_for(self.regular).patch(
                    f"{USERS_URL}/{self.customer.pk}",
                    {"role": role.value},
                    format="json",
                )
                self.assertEqual(response.status_code, 403)
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_staff)
        self.assertFalse(self.customer.is_superuser)

    def test_cannot_promote_a_customer_they_just_created(self):
        """مسیر دومرحله‌ای: بساز، بعد ارتقا بده"""
        created = self.create_user_as(
            self.regular, "09120005007", Role.CUSTOMER
        )
        self.assertEqual(created.status_code, 201)
        victim_id = created.json()["data"]["user"]["id"]

        promoted = self.client_for(self.regular).patch(
            f"{USERS_URL}/{victim_id}",
            {"role": Role.MANAGER_ADMIN.value},
            format="json",
        )
        self.assertEqual(promoted.status_code, 403)
        self.assertFalse(User.objects.get(pk=victim_id).is_staff)

    def test_cannot_access_seo(self):
        self.assertEqual(
            self.client_for(self.regular).get(SEO_URL).status_code, 403
        )

    def test_cannot_use_privileged_management_endpoints(self):
        client = self.client_for(self.regular)
        for url in (MANAGERS_URL, SEO_ADMINS_URL):
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, 403)

    def test_cannot_edit_their_own_account_through_user_management(self):
        response = self.client_for(self.regular).patch(
            f"{USERS_URL}/{self.regular.pk}",
            {"role": Role.MANAGER_ADMIN.value},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.regular.refresh_from_db()
        self.assertFalse(self.regular.is_manager_admin)


# ─── ۵. مدیر سئو ─────────────────────────────────────────────


class SeoAdminTests(RoleFixtureMixin, TestCase):
    def test_can_access_seo(self):
        self.assertEqual(
            self.client_for(self.seo_admin).get(SEO_URL).status_code, 200
        )

    def test_cannot_reach_general_admin_sections(self):
        client = self.client_for(self.seo_admin)
        for url in (
            "/api/admin/stats",
            "/api/admin/orders",
            "/api/admin/products",
            "/api/admin/comments",
        ):
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, 403)

    def test_cannot_enumerate_users(self):
        response = self.client_for(self.seo_admin).get(USERS_URL)
        self.assertEqual(response.status_code, 403)

    def test_cannot_read_a_single_user_record(self):
        response = self.client_for(self.seo_admin).get(
            f"{USERS_URL}/{self.customer.pk}"
        )
        self.assertEqual(response.status_code, 403)

    def test_cannot_create_users(self):
        response = self.create_user_as(
            self.seo_admin, "09120006001", Role.CUSTOMER
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(phone="09120006001").exists())

    def test_cannot_manage_seo_admin_accounts(self):
        """دسترسی به داده‌ی سئو یعنی داده، نه ساختن حساب"""
        client = self.client_for(self.seo_admin)
        self.assertEqual(client.get(SEO_ADMINS_URL).status_code, 403)
        self.assertEqual(client.get(MANAGERS_URL).status_code, 403)

    def test_can_read_their_own_profile(self):
        response = self.client_for(self.seo_admin).get("/api/auth/me")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["data"]["user"]["role"], Role.SEO_ADMIN.value
        )


# ─── ۶. مشتری ────────────────────────────────────────────────


class CustomerTests(RoleFixtureMixin, TestCase):
    def test_cannot_reach_admin_apis(self):
        client = self.client_for(self.customer)
        for url in (USERS_URL, "/api/admin/stats", "/api/admin/orders"):
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, 403)

    def test_cannot_reach_seo_apis(self):
        self.assertEqual(
            self.client_for(self.customer).get(SEO_URL).status_code, 403
        )

    def test_cannot_reach_user_management_detail(self):
        response = self.client_for(self.customer).get(
            f"{USERS_URL}/{self.superuser.pk}"
        )
        self.assertEqual(response.status_code, 403)

    def test_anonymous_is_rejected_too(self):
        self.assertEqual(APIClient().get(USERS_URL).status_code, 403)


# ─── ۷. حمله‌ی مستقیم به فیلدهای حساس ────────────────────────


class PrivilegeEscalationFieldTests(RoleFixtureMixin, TestCase):
    """فیلدهای خطرناک نباید از بدنه‌ی درخواست به مدل برسند"""

    DANGEROUS_PAYLOAD = {
        "is_superuser": True,
        "isSuperuser": True,
        "is_staff": True,
        "isStaff": True,
        "is_manager_admin": True,
        "isManagerAdmin": True,
        "is_seo_manager": True,
        "can_access_seo": True,
        "groups": [1],
        "user_permissions": [1],
        "is_active": False,
    }

    def test_create_ignores_dangerous_flags(self):
        response = self.client_for(self.manager).post(
            USERS_URL,
            {"phone": "09120007001", **self.DANGEROUS_PAYLOAD},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

        created = User.objects.get(phone="09120007001")
        self.assertFalse(created.is_superuser)
        self.assertFalse(created.is_staff)
        self.assertFalse(created.is_manager_admin)
        self.assertFalse(created.is_seo_manager)
        self.assertFalse(created.can_access_seo)
        self.assertTrue(created.is_active)
        self.assertEqual(created.groups.count(), 0)
        self.assertEqual(created.user_permissions.count(), 0)

    def test_update_ignores_dangerous_flags(self):
        response = self.client_for(self.manager).patch(
            f"{USERS_URL}/{self.customer.pk}",
            self.DANGEROUS_PAYLOAD,
            format="json",
        )
        # هیچ فیلد شناخته‌شده‌ای در بدنه نیست، پس «تغییری ارسال نشده»
        self.assertEqual(response.status_code, 422)

        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_superuser)
        self.assertFalse(self.customer.is_staff)
        self.assertTrue(self.customer.is_active)

    def test_role_string_outside_the_enum_is_refused(self):
        response = self.client_for(self.manager).post(
            USERS_URL,
            {"phone": "09120007002", "role": "SUPERUSER"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(phone="09120007002").exists())

    def test_profile_endpoint_cannot_change_role(self):
        """مسیر پروفایل شخصی هم راه فراری نیست"""
        response = self.client_for(self.regular).patch(
            "/api/auth/profile",
            {
                "name": "خودارتقا",
                "isStaff": True,
                "is_superuser": True,
                "canAccessSeo": True,
                "role": Role.SUPERUSER.value,
            },
            format="json",
        )
        self.assertIn(response.status_code, (200, 422))
        self.regular.refresh_from_db()
        self.assertFalse(self.regular.is_superuser)
        self.assertFalse(self.regular.is_manager_admin)
        self.assertFalse(self.regular.can_access_seo)

    def test_seo_access_cannot_be_attached_to_a_non_manager(self):
        """قید مدل و ویو هر دو جلویش را می‌گیرند"""
        response = self.client_for(self.superuser).post(
            USERS_URL,
            {
                "phone": "09120007003",
                "role": Role.REGULAR_ADMIN.value,
                "canAccessSeo": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertFalse(User.objects.filter(phone="09120007003").exists())

    def test_demoting_a_manager_clears_their_seo_access(self):
        """توانایی افزوده روی نقشی که دیگر وجود ندارد نمی‌ماند"""
        response = self.client_for(self.superuser).patch(
            f"{USERS_URL}/{self.seo_manager.pk}",
            {"role": Role.REGULAR_ADMIN.value},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.seo_manager.refresh_from_db()
        self.assertFalse(self.seo_manager.can_access_seo)
        self.assertFalse(self.seo_manager.is_manager_admin)

    def test_deactivated_admin_loses_every_permission_immediately(self):
        client = self.client_for(self.manager)
        self.assertEqual(client.get(USERS_URL).status_code, 200)

        self.manager.is_active = False
        self.manager.save(update_fields=["is_active"])

        self.assertEqual(client.get(USERS_URL).status_code, 403)


# ─── ۸. سناریوهای پایانی صورت‌مسئله ──────────────────────────


class EndToEndScenarioTests(RoleFixtureMixin, TestCase):
    """سناریوهای A تا E — همان مسیری که کاربر واقعی طی می‌کند"""

    def test_scenario_a_manager_without_seo(self):
        """سوپریوزر «جان» را مدیر اجرایی بدون سئو می‌سازد"""
        created = self.client_for(self.superuser).post(
            MANAGERS_URL,
            {"phone": "09121110001", "name": "جان", "canAccessSeo": False},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        john = User.objects.get(phone="09121110001")
        john_client = self.client_for(john)

        self.assertEqual(john_client.get("/api/admin/stats").status_code, 200)
        self.assertEqual(
            self.create_user_as(john, "09121110002", Role.REGULAR_ADMIN).status_code,
            201,
        )
        self.assertEqual(
            self.create_user_as(john, "09121110003", Role.CUSTOMER).status_code,
            201,
        )
        self.assertEqual(john_client.get(SEO_URL).status_code, 403)
        self.assertEqual(
            self.create_user_as(john, "09121110004", Role.SEO_ADMIN).status_code,
            403,
        )
        self.assertNotIn(self.superuser.phone, self.listed_phones(john))
        self.assertEqual(
            self.create_user_as(john, "09121110005", Role.MANAGER_ADMIN).status_code,
            403,
        )

    def test_scenario_b_granting_seo_access_takes_effect_immediately(self):
        john = User.objects.create_user(
            phone="09121110010", name="جان", is_staff=True, is_manager_admin=True
        )
        # نشست واقعی، چون ادعا این است که دسترسی «بلافاصله» و بدون ورود دوباره
        # باز می‌شود؛ force_authenticate شیء کاربر را در حافظه نگه می‌دارد و
        # تغییر دیتابیس را نشان نمی‌دهد.
        self.client.force_login(john)
        self.assertEqual(self.client.get(SEO_URL).status_code, 403)

        granted = self.client_for(self.superuser).patch(
            f"{MANAGERS_URL}/{john.pk}", {"canAccessSeo": True}, format="json"
        )
        self.assertEqual(granted.status_code, 200, granted.data)

        self.assertEqual(self.client.get(SEO_URL).status_code, 200)
        john.refresh_from_db()
        john_client = self.client_for(john)
        self.assertEqual(
            self.create_user_as(john, "09121110011", Role.SEO_ADMIN).status_code,
            201,
        )
        # ولی مرزهای بالاتر همچنان بسته‌اند
        self.assertNotIn(self.superuser.phone, self.listed_phones(john))
        self.assertEqual(
            self.create_user_as(john, "09121110012", Role.SUPERUSER).status_code,
            403,
        )
        self.assertEqual(
            self.create_user_as(john, "09121110013", Role.MANAGER_ADMIN).status_code,
            403,
        )
        self.assertEqual(
            john_client.patch(
                f"{MANAGERS_URL}/{self.manager.pk}",
                {"canAccessSeo": True},
                format="json",
            ).status_code,
            403,
        )

    def test_scenario_c_seo_admin_sees_only_seo(self):
        john = User.objects.create_user(
            phone="09121110020",
            is_staff=True,
            is_manager_admin=True,
            can_access_seo=True,
        )
        created = self.create_user_as(john, "09121110021", Role.SEO_ADMIN)
        self.assertEqual(created.status_code, 201, created.data)

        sara = User.objects.get(phone="09121110021")
        sara_client = self.client_for(sara)
        self.assertEqual(sara_client.get(SEO_URL).status_code, 200)
        for url in (
            "/api/admin/orders",
            USERS_URL,
            "/api/admin/stats",
            MANAGERS_URL,
        ):
            with self.subTest(url=url):
                self.assertEqual(sara_client.get(url).status_code, 403)

    def test_scenario_d_regular_admin_created_by_a_manager(self):
        john = User.objects.create_user(
            phone="09121110030", is_staff=True, is_manager_admin=True
        )
        sara = User.objects.create_user(
            phone="09121110031", is_seo_manager=True
        )
        created = self.create_user_as(john, "09121110032", Role.REGULAR_ADMIN)
        self.assertEqual(created.status_code, 201, created.data)

        alex = User.objects.get(phone="09121110032")
        alex_client = self.client_for(alex)

        self.assertEqual(alex_client.get(USERS_URL).status_code, 200)
        self.assertEqual(
            self.create_user_as(alex, "09121110033", Role.CUSTOMER).status_code,
            201,
        )
        visible = self.listed_phones(alex)
        for hidden in (john, sara, self.superuser):
            self.assertNotIn(hidden.phone, visible)
        self.assertEqual(
            self.create_user_as(alex, "09121110034", Role.REGULAR_ADMIN).status_code,
            403,
        )
        self.assertEqual(
            alex_client.delete(f"{USERS_URL}/{self.customer.pk}").status_code, 403
        )
        self.assertEqual(
            alex_client.patch(
                f"{USERS_URL}/{self.customer.pk}",
                {"role": Role.REGULAR_ADMIN.value},
                format="json",
            ).status_code,
            403,
        )

    def test_scenario_e_customer_hitting_the_admin_api(self):
        response = self.client_for(self.customer).get(USERS_URL)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.data["ok"])


# ─── ۹. حذف و تاریخچه ────────────────────────────────────────


class UserDeletionTests(RoleFixtureMixin, TestCase):
    def test_deleting_a_customer_with_orders_is_refused_not_crashed(self):
        """تاریخچه‌ی سفارش محافظت‌شده است؛ پاسخ باید کنترل‌شده باشد"""
        Order.objects.create(
            user=self.customer,
            full_name="مشتری",
            phone=self.customer.phone,
            province="تهران",
            city="تهران",
            address="خیابان",
            items_price=1000,
            total_price=1000,
        )
        response = self.client_for(self.superuser).delete(
            f"{USERS_URL}/{self.customer.pk}"
        )
        # Order.user با on_delete=PROTECT بسته شده است
        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.data["ok"])
        self.assertTrue(User.objects.filter(pk=self.customer.pk).exists())

    def test_a_customer_without_history_is_really_deleted(self):
        response = self.client_for(self.superuser).delete(
            f"{USERS_URL}/{self.customer.pk}"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(User.objects.filter(pk=self.customer.pk).exists())
