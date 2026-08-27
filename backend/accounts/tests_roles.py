"""نقش‌های مدیریتی در سطح حساب کاربری: DTO ورود و دستورهای مدیریتی"""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.roles import (
    Role,
    can_access_seo,
    can_change_role,
    can_create_role,
    can_delete_user,
    can_grant_seo_access,
    can_manage_account_state,
    creatable_roles,
    is_developer_admin,
    is_manager_admin,
    is_regular_admin,
    is_seo_admin,
    is_shop_admin,
    manageable_roles,
    role_of,
    role_of_record,
)
from accounts.selectors import visible_users_for

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
            "regular-admin": (self.staff, False, True, False, False),
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

    def test_role_of_names_exactly_one_role_per_user(self):
        expected = {
            self.seo_admin: Role.SEO_ADMIN,
            self.staff: Role.REGULAR_ADMIN,
            self.manager: Role.MANAGER_ADMIN,
            self.superuser: Role.SUPERUSER,
            self.customer: Role.CUSTOMER,
        }
        for user, role in expected.items():
            with self.subTest(role=role.value):
                self.assertEqual(role_of(user), role)
                self.assertEqual(role_of_record(user), role)

    def test_regular_admin_is_plain_staff_only(self):
        self.assertTrue(is_regular_admin(self.staff))
        for user in (self.manager, self.superuser, self.seo_admin, self.customer):
            with self.subTest(user=str(user)):
                self.assertFalse(is_regular_admin(user))

    def test_role_of_record_still_names_a_deactivated_account(self):
        """کاربرِ درخواست‌دهنده بی‌نقش می‌شود، ولی ردیفِ فهرست نقشش را دارد"""
        self.manager.is_active = False
        self.manager.save(update_fields=["is_active"])
        self.assertIsNone(role_of(self.manager))
        self.assertEqual(role_of_record(self.manager), Role.MANAGER_ADMIN)

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


class SeoAccessCapabilityTests(TestCase):
    """``can_access_seo`` — سه گروه مجاز و نه یکی بیشتر"""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            phone="09120000601", password="x"
        )
        self.seo_admin = User.objects.create_user(
            phone="09120000602", is_seo_manager=True
        )
        self.manager = User.objects.create_user(
            phone="09120000603", is_staff=True, is_manager_admin=True
        )
        self.seo_manager = User.objects.create_user(
            phone="09120000604",
            is_staff=True,
            is_manager_admin=True,
            can_access_seo=True,
        )
        self.regular = User.objects.create_user(
            phone="09120000605", is_staff=True
        )
        self.customer = User.objects.create_user(phone="09120000606")

    def test_who_can_reach_the_seo_branch(self):
        allowed = {
            "superuser": self.superuser,
            "seo-admin": self.seo_admin,
            "manager-with-seo": self.seo_manager,
        }
        denied = {
            "manager-without-seo": self.manager,
            "regular-admin": self.regular,
            "customer": self.customer,
            "anonymous": None,
        }
        for label, user in allowed.items():
            with self.subTest(role=label):
                self.assertTrue(can_access_seo(user))
        for label, user in denied.items():
            with self.subTest(role=label):
                self.assertFalse(can_access_seo(user))

    def test_only_the_superuser_controls_the_grant(self):
        self.assertTrue(can_grant_seo_access(self.superuser))
        for user in (
            self.seo_manager,
            self.manager,
            self.regular,
            self.seo_admin,
            self.customer,
        ):
            with self.subTest(user=str(user)):
                self.assertFalse(can_grant_seo_access(user))

    def test_database_rejects_the_flag_on_a_non_manager(self):
        """قید دیتابیس حتی دور زدن با update خام را هم می‌بندد"""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.filter(pk=self.regular.pk).update(
                    can_access_seo=True
                )
        self.regular.refresh_from_db()
        self.assertFalse(self.regular.can_access_seo)

    def test_the_flag_alone_does_nothing_without_the_manager_role(self):
        """لایه‌ی دوم: حتی اگر فلگ روی شیء بنشیند، نقش مبناست"""
        self.regular.can_access_seo = True  # فقط در حافظه
        self.assertFalse(can_access_seo(self.regular))

    def test_model_validation_rejects_the_flag_on_a_non_manager(self):
        self.regular.can_access_seo = True
        with self.assertRaises(ValidationError):
            self.regular.save(update_fields=["can_access_seo"])


class CreationMatrixTests(TestCase):
    """جدول §۱۱ — چه نقشی چه نقشی می‌سازد"""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            phone="09120000701", password="x"
        )
        self.manager = User.objects.create_user(
            phone="09120000702", is_staff=True, is_manager_admin=True
        )
        self.seo_manager = User.objects.create_user(
            phone="09120000703",
            is_staff=True,
            is_manager_admin=True,
            can_access_seo=True,
        )
        self.regular = User.objects.create_user(
            phone="09120000704", is_staff=True
        )
        self.seo_admin = User.objects.create_user(
            phone="09120000705", is_seo_manager=True
        )
        self.customer = User.objects.create_user(phone="09120000706")

    def test_creation_matrix(self):
        expected = {
            "superuser": (
                self.superuser,
                {
                    Role.SUPERUSER,
                    Role.MANAGER_ADMIN,
                    Role.REGULAR_ADMIN,
                    Role.SEO_ADMIN,
                    Role.CUSTOMER,
                },
            ),
            "manager-without-seo": (
                self.manager,
                {Role.REGULAR_ADMIN, Role.CUSTOMER},
            ),
            "manager-with-seo": (
                self.seo_manager,
                {Role.REGULAR_ADMIN, Role.SEO_ADMIN, Role.CUSTOMER},
            ),
            "regular-admin": (self.regular, {Role.CUSTOMER}),
            "seo-admin": (self.seo_admin, set()),
            "customer": (self.customer, set()),
        }
        for label, (actor, allowed) in expected.items():
            with self.subTest(role=label):
                self.assertEqual(set(creatable_roles(actor)), allowed)
                for role in Role:
                    self.assertEqual(
                        can_create_role(actor, role), role in allowed
                    )

    def test_visibility_matrix(self):
        expected = {
            "superuser": (
                self.superuser,
                {
                    Role.SUPERUSER,
                    Role.MANAGER_ADMIN,
                    Role.REGULAR_ADMIN,
                    Role.SEO_ADMIN,
                    Role.CUSTOMER,
                },
            ),
            "manager-without-seo": (
                self.manager,
                {Role.REGULAR_ADMIN, Role.CUSTOMER},
            ),
            "manager-with-seo": (
                self.seo_manager,
                {Role.REGULAR_ADMIN, Role.SEO_ADMIN, Role.CUSTOMER},
            ),
            "regular-admin": (self.regular, {Role.CUSTOMER}),
            "seo-admin": (self.seo_admin, set()),
            "customer": (self.customer, set()),
        }
        for label, (actor, allowed) in expected.items():
            with self.subTest(role=label):
                self.assertEqual(set(manageable_roles(actor)), allowed)

    def test_selector_returns_exactly_the_visible_roles(self):
        """سلکتور و جدول نقش‌ها نباید از هم واگرا شوند"""
        for actor in (
            self.superuser,
            self.manager,
            self.seo_manager,
            self.regular,
            self.seo_admin,
            self.customer,
        ):
            with self.subTest(actor=str(actor)):
                roles = {
                    role_of_record(user)
                    for user in visible_users_for(actor)
                }
                self.assertTrue(roles <= set(manageable_roles(actor)))
                # هر کاربری که نقشش مجاز است واقعاً در کوئری هست
                self.assertEqual(
                    visible_users_for(actor).count(),
                    User.objects.filter(
                        pk__in=[
                            u.pk
                            for u in User.objects.all()
                            if role_of_record(u) in manageable_roles(actor)
                        ]
                    ).count(),
                )

    def test_nobody_changes_their_own_role(self):
        for actor in (self.superuser, self.manager, self.regular):
            with self.subTest(actor=str(actor)):
                self.assertFalse(
                    can_change_role(actor, actor, Role.SUPERUSER)
                )
                self.assertFalse(can_manage_account_state(actor, actor))
                self.assertFalse(can_delete_user(actor, actor))

    def test_only_the_superuser_hard_deletes(self):
        self.assertTrue(can_delete_user(self.superuser, self.customer))
        for actor in (self.manager, self.seo_manager, self.regular):
            with self.subTest(actor=str(actor)):
                self.assertFalse(can_delete_user(actor, self.customer))

    def test_regular_admin_never_manages_account_state(self):
        self.assertFalse(
            can_manage_account_state(self.regular, self.customer)
        )
        self.assertTrue(can_manage_account_state(self.manager, self.customer))
