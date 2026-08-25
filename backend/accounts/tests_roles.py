"""نقش‌های مدیریتی در سطح حساب کاربری: DTO ورود و دستورهای مدیریتی"""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.permissions import (
    is_developer_admin,
    is_manager_admin,
    is_seo_admin,
    is_shop_admin,
)

User = get_user_model()


class MeEndpointRoleTests(TestCase):
    """فرانت نقش را از همین پاسخ می‌خواند و منو را بر اساس آن می‌سازد"""

    def me(self, user) -> dict:
        client = APIClient()
        client.force_authenticate(user)
        response = client.get("/api/auth/me")
        self.assertEqual(response.status_code, 200)
        return response.data["data"]["user"]

    def test_seo_admin_is_reported_without_staff_flags(self):
        user = User.objects.create_user(phone="09120000401", is_seo_manager=True)
        data = self.me(user)
        self.assertTrue(data["isSeoManager"])
        self.assertFalse(data["isStaff"])
        self.assertFalse(data["isSuperuser"])

    def test_superuser_is_reported_without_the_seo_flag(self):
        user = User.objects.create_superuser(phone="09120000402", password="x")
        data = self.me(user)
        self.assertTrue(data["isStaff"])
        self.assertTrue(data["isSuperuser"])
        self.assertFalse(data["isSeoManager"])

    def test_manager_admin_is_reported_as_staff_without_system_flags(self):
        user = User.objects.create_user(
            phone="09120000404", is_staff=True, is_manager_admin=True
        )
        data = self.me(user)
        self.assertTrue(data["isStaff"])
        self.assertTrue(data["isManagerAdmin"])
        self.assertFalse(data["isSuperuser"])
        self.assertFalse(data["isSeoManager"])

    def test_customer_has_no_admin_flag(self):
        data = self.me(User.objects.create_user(phone="09120000403"))
        self.assertFalse(data["isStaff"])
        self.assertFalse(data["isSuperuser"])
        self.assertFalse(data["isManagerAdmin"])
        self.assertFalse(data["isSeoManager"])


class RolePredicateTests(TestCase):
    """توابع مرجع مجوز — همان جدولی که ویوها به آن تکیه می‌کنند"""

    def setUp(self):
        self.seo_admin = User.objects.create_user(
            phone="09120000501", is_seo_manager=True
        )
        self.staff = User.objects.create_user(phone="09120000502", is_staff=True)
        self.manager = User.objects.create_user(
            phone="09120000505", is_staff=True, is_manager_admin=True
        )
        self.superuser = User.objects.create_superuser(
            phone="09120000503", password="x"
        )
        self.customer = User.objects.create_user(phone="09120000504")

    def test_permission_matrix(self):
        matrix = {
            #                     seo,   shop, manager, developer
            "seo-admin": (self.seo_admin, True, False, False, False),
            "staff": (self.staff, False, True, False, False),
            "manager-admin": (self.manager, False, True, True, False),
            "superuser": (self.superuser, False, True, False, True),
            "customer": (self.customer, False, False, False, False),
        }
        for role, (user, seo, shop, manager, root) in matrix.items():
            with self.subTest(role=role):
                self.assertEqual(is_seo_admin(user), seo)
                self.assertEqual(is_shop_admin(user), shop)
                self.assertEqual(is_manager_admin(user), manager)
                self.assertEqual(is_developer_admin(user), root)

    def test_none_and_inactive_users_have_no_role(self):
        self.seo_admin.is_active = False
        self.manager.is_active = False
        for user in (None, self.seo_admin, self.manager):
            with self.subTest(user=user):
                self.assertFalse(is_seo_admin(user))
                self.assertFalse(is_shop_admin(user))
                self.assertFalse(is_manager_admin(user))
                self.assertFalse(is_developer_admin(user))


class RoleCommandTests(TestCase):
    """دستورهای make_seo/make_admin نباید دو نقش ناسازگار را روی هم بگذارند"""

    def run_command(self, name: str, *args) -> tuple[str, str]:
        out, err = StringIO(), StringIO()
        call_command(name, *args, stdout=out, stderr=err)
        return out.getvalue(), err.getvalue()

    def test_make_seo_creates_a_seo_admin(self):
        self.run_command("make_seo", "09121230001")
        user = User.objects.get(phone="09121230001")
        self.assertTrue(user.is_seo_manager)
        self.assertFalse(user.is_staff)

    def test_make_seo_refuses_a_shop_admin(self):
        staff = User.objects.create_user(phone="09121230002", is_staff=True)
        _out, err = self.run_command("make_seo", staff.phone)
        self.assertIn("مدیر فروشگاه", err)
        staff.refresh_from_db()
        self.assertFalse(staff.is_seo_manager)

    def test_make_admin_refuses_a_seo_admin(self):
        seo = User.objects.create_user(phone="09121230003", is_seo_manager=True)
        _out, err = self.run_command("make_admin", seo.phone)
        self.assertIn("مدیر سئو", err)
        seo.refresh_from_db()
        self.assertFalse(seo.is_staff)

    def test_make_manager_creates_a_business_admin(self):
        self.run_command("make_manager", "09121230005")
        user = User.objects.get(phone="09121230005")
        self.assertTrue(user.is_manager_admin)
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_make_manager_refuses_a_superuser(self):
        root = User.objects.create_superuser(
            phone="09121230006", password="x"
        )
        _out, err = self.run_command("make_manager", root.phone)
        self.assertIn("سوپریوزر", err)
        root.refresh_from_db()
        self.assertFalse(root.is_manager_admin)

    def test_make_manager_refuses_a_seo_admin(self):
        seo = User.objects.create_user(phone="09121230007", is_seo_manager=True)
        _out, err = self.run_command("make_manager", seo.phone)
        self.assertIn("مدیر سئو", err)
        seo.refresh_from_db()
        self.assertFalse(seo.is_manager_admin)

    def test_make_seo_refuses_a_manager_admin(self):
        manager = User.objects.create_user(
            phone="09121230008", is_staff=True, is_manager_admin=True
        )
        _out, err = self.run_command("make_seo", manager.phone)
        self.assertIn("make_manager", err)
        manager.refresh_from_db()
        self.assertFalse(manager.is_seo_manager)

    def test_make_admin_revoke_refuses_a_manager_admin(self):
        """گرفتن staff از مدیر اجرایی نقشش را ناسازگار می‌کند"""
        manager = User.objects.create_user(
            phone="09121230009", is_staff=True, is_manager_admin=True
        )
        _out, err = self.run_command("make_admin", manager.phone, "--revoke")
        self.assertIn("make_manager", err)
        manager.refresh_from_db()
        self.assertTrue(manager.is_staff)
        self.assertTrue(manager.is_manager_admin)

    def test_make_manager_revoke_clears_dashboard_access(self):
        manager = User.objects.create_user(
            phone="09121230010", is_staff=True, is_manager_admin=True
        )
        self.run_command("make_manager", manager.phone, "--revoke")
        manager.refresh_from_db()
        self.assertFalse(manager.is_manager_admin)
        self.assertFalse(manager.is_staff)

    def test_revoking_seo_then_granting_admin_works(self):
        seo = User.objects.create_user(phone="09121230004", is_seo_manager=True)
        self.run_command("make_seo", seo.phone, "--revoke")
        self.run_command("make_admin", seo.phone)
        seo.refresh_from_db()
        self.assertFalse(seo.is_seo_manager)
        self.assertTrue(seo.is_staff)
