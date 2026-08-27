from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import Address
from carts.models import Cart, CartItem
from catalog.models import Category, Product
from notifications.services.sms import (
    SmsDeliveryError,
    send_new_order_admin_sms,
    send_order_status_changed_sms,
)

from .models import Order, OrderItem
from .admin import OrderAdmin
from .services import (
    schedule_new_order_admin_sms,
    schedule_order_status_changed_sms,
)


User = get_user_model()

TEST_IPPANEL = {
    "NEW_ORDER_PATTERN_CODE": "3v0og6lgz3ixp8i",
    "ORDER_STATUS_PATTERN_CODE": "fivdiyj4psxj94k",
}


@override_settings(IPPANEL=TEST_IPPANEL)
class OrderSmsServiceTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            phone="09120000001", name="مشتری"
        )
        self.superuser = User.objects.create_user(
            phone="09120000101", is_staff=True, is_superuser=True
        )
        self.manager = User.objects.create_user(
            phone="09120000102",
            is_staff=True,
            is_manager_admin=True,
            can_access_seo=True,
        )
        self.regular_admin = User.objects.create_user(
            phone="09120000103", is_staff=True
        )
        self.seo_admin = User.objects.create_user(
            phone="09120000104", is_seo_manager=True
        )
        self.inactive_admin = User.objects.create_user(
            phone="09120000105", is_staff=True, is_active=False
        )

    def test_new_order_recipient_matrix_and_exact_pattern_payload(self):
        backend = Mock()

        with patch(
            "notifications.services.sms.get_sms_backend", return_value=backend
        ):
            send_new_order_admin_sms(
                order_id=42,
                order_number="GS-42",
                customer_name="زهرا محمدی",
                order_total=1_250_000,
            )

        payload = {
            "order_number": "GS-42",
            "customer_name": "زهرا محمدی",
            "order_total": "1250000",
        }
        backend.send_pattern.assert_has_calls(
            [
                call(
                    phone,
                    "3v0og6lgz3ixp8i",
                    payload,
                    sms_type="new_order_admin",
                    order_id=42,
                )
                for phone in (
                    "+989120000101",
                    "+989120000102",
                    "+989120000103",
                )
            ],
            any_order=True,
        )
        self.assertEqual(backend.send_pattern.call_count, 3)

    def test_new_order_deduplicates_equivalent_phone_formats(self):
        queryset = Mock()
        queryset.filter.return_value = queryset
        queryset.values_list.return_value = [
            "09121234567",
            "989121234567",
            "+989121234567",
            "invalid-phone",
        ]
        fake_user_model = Mock()
        fake_user_model.objects.filter.return_value = queryset
        backend = Mock()

        with (
            patch(
                "notifications.services.sms.get_user_model",
                return_value=fake_user_model,
            ),
            patch(
                "notifications.services.sms.get_sms_backend",
                return_value=backend,
            ),
        ):
            send_new_order_admin_sms(
                order_id=7,
                order_number="GS-7",
                customer_name="مشتری",
                order_total=80_000,
            )

        backend.send_pattern.assert_called_once_with(
            "+989121234567",
            "3v0og6lgz3ixp8i",
            {
                "order_number": "GS-7",
                "customer_name": "مشتری",
                "order_total": "80000",
            },
            sms_type="new_order_admin",
            order_id=7,
        )

    def test_one_provider_failure_does_not_stop_other_admins(self):
        backend = Mock()
        backend.send_pattern.side_effect = [
            SmsDeliveryError("provider unavailable"),
            None,
            None,
        ]

        with (
            patch(
                "notifications.services.sms.get_sms_backend",
                return_value=backend,
            ),
            self.assertLogs("notifications.services.sms", level="ERROR"),
        ):
            send_new_order_admin_sms(
                order_id=9,
                order_number="GS-9",
                customer_name="مشتری",
                order_total=90_000,
            )

        self.assertEqual(backend.send_pattern.call_count, 3)

    def test_status_sms_uses_exact_owner_pattern_and_persian_label(self):
        other_customer = User.objects.create_user(phone="09120000201")
        backend = Mock()

        with patch(
            "notifications.services.sms.get_sms_backend", return_value=backend
        ):
            send_order_status_changed_sms(
                order_id=51,
                owner_id=self.customer.pk,
                order_number="GS-51",
                order_status="ارسال شده",
            )

        backend.send_pattern.assert_called_once_with(
            "+989120000001",
            "fivdiyj4psxj94k",
            {"order_number": "GS-51", "order_status": "ارسال شده"},
            sms_type="order_status_changed",
            order_id=51,
        )
        self.assertNotIn(
            f"+98{other_customer.phone[1:]}",
            [item.args[0] for item in backend.send_pattern.call_args_list],
        )

    def test_status_sms_goes_to_owner_even_when_owner_has_an_admin_role(self):
        backend = Mock()

        with patch(
            "notifications.services.sms.get_sms_backend", return_value=backend
        ):
            send_order_status_changed_sms(
                order_id=52,
                owner_id=self.regular_admin.pk,
                order_number="GS-52",
                order_status="تحویل شده",
            )

        backend.send_pattern.assert_called_once_with(
            "+989120000103",
            "fivdiyj4psxj94k",
            {"order_number": "GS-52", "order_status": "تحویل شده"},
            sms_type="order_status_changed",
            order_id=52,
        )

    def test_missing_or_invalid_owner_phone_is_skipped_safely(self):
        invalid_owner = SimpleNamespace(
            phone="not-a-phone",
            is_superuser=False,
            is_seo_manager=False,
            is_manager_admin=False,
            is_staff=False,
        )
        fake_user_model = Mock()
        fake_user_model.objects.filter.return_value.first.side_effect = [
            None,
            invalid_owner,
        ]
        get_backend = Mock()

        with (
            patch(
                "notifications.services.sms.get_user_model",
                return_value=fake_user_model,
            ),
            patch("notifications.services.sms.get_sms_backend", get_backend),
            self.assertLogs("notifications.services.sms", level="INFO"),
        ):
            for owner_id in (999_001, 999_002):
                send_order_status_changed_sms(
                    order_id=53,
                    owner_id=owner_id,
                    order_number="GS-53",
                    order_status="لغو شده",
                )

        get_backend.assert_not_called()


class OrderNotificationSchedulingTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            phone="09121111111", name="نام حساب"
        )
        self.order = Order.objects.create(
            code="GS-SCHEDULE",
            user=self.owner,
            full_name="  نام تحویل گیرنده  ",
            phone=self.owner.phone,
            province="تهران",
            city="تهران",
            address="خیابان آزمایشی شماره ده",
            items_price=250_000,
            total_price=250_000,
        )

    def test_new_order_customer_name_fallback_order(self):
        with patch("orders.services.send_new_order_admin_sms") as sender:
            with self.captureOnCommitCallbacks(execute=True):
                schedule_new_order_admin_sms(self.order)
                self.order.full_name = "   "
                schedule_new_order_admin_sms(self.order)
                self.order.user.name = "   "
                schedule_new_order_admin_sms(self.order)

        base = {
            "order_id": self.order.pk,
            "order_number": self.order.code,
            "order_total": self.order.total_price,
        }
        self.assertEqual(
            sender.call_args_list,
            [
                call(customer_name="نام تحویل گیرنده", **base),
                call(customer_name="نام حساب", **base),
                call(customer_name=self.owner.phone, **base),
            ],
        )

    def test_unchanged_status_does_not_register_or_send(self):
        with patch("orders.services.send_order_status_changed_sms") as sender:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                scheduled = schedule_order_status_changed_sms(
                    self.order, Order.Status.PENDING
                )

        self.assertFalse(scheduled)
        self.assertEqual(callbacks, [])
        sender.assert_not_called()

    def test_each_real_transition_captures_its_own_persian_status(self):
        with patch("orders.services.send_order_status_changed_sms") as sender:
            with self.captureOnCommitCallbacks(execute=True):
                self.order.status = Order.Status.PAID
                self.order.save(update_fields=["status"])
                schedule_order_status_changed_sms(
                    self.order, Order.Status.PENDING
                )

                self.order.status = Order.Status.SHIPPED
                self.order.save(update_fields=["status"])
                schedule_order_status_changed_sms(self.order, Order.Status.PAID)
                sender.assert_not_called()

        common = {
            "order_id": self.order.pk,
            "owner_id": self.owner.pk,
            "order_number": self.order.code,
        }
        self.assertEqual(
            sender.call_args_list,
            [
                call(order_status="پرداخت شده", **common),
                call(order_status="ارسال شده", **common),
            ],
        )

    def test_django_admin_sends_only_for_a_real_status_change(self):
        order_admin = OrderAdmin(Order, AdminSite())
        with patch("orders.services.send_order_status_changed_sms") as sender:
            self.order.full_name = "نام ویرایش شده"
            with self.captureOnCommitCallbacks(execute=True) as unchanged_callbacks:
                order_admin.save_model(None, self.order, Mock(), change=True)

            self.order.status = Order.Status.PAID
            with self.captureOnCommitCallbacks(execute=True) as changed_callbacks:
                order_admin.save_model(None, self.order, Mock(), change=True)

        self.assertEqual(unchanged_callbacks, [])
        self.assertEqual(len(changed_callbacks), 1)
        sender.assert_called_once_with(
            order_id=self.order.pk,
            owner_id=self.owner.pk,
            order_number=self.order.code,
            order_status="پرداخت شده",
        )

    def test_rolled_back_transaction_discards_both_callbacks(self):
        rolled_back_code = "GS-ROLLED-BACK"
        with (
            patch("orders.services.send_new_order_admin_sms") as new_order_sender,
            patch(
                "orders.services.send_order_status_changed_sms"
            ) as status_sender,
        ):
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                with transaction.atomic():
                    rolled_back_order = Order.objects.create(
                        code=rolled_back_code,
                        user=self.owner,
                        full_name="سفارش برگشتی",
                        phone=self.owner.phone,
                        province="تهران",
                        city="تهران",
                        address="خیابان آزمایشی شماره ده",
                        items_price=100_000,
                        total_price=100_000,
                    )
                    schedule_new_order_admin_sms(rolled_back_order)
                    self.order.status = Order.Status.PAID
                    self.order.save(update_fields=["status"])
                    schedule_order_status_changed_sms(
                        self.order, Order.Status.PENDING
                    )
                    transaction.set_rollback(True)

        self.assertEqual(callbacks, [])
        self.assertFalse(Order.objects.filter(code=rolled_back_code).exists())
        new_order_sender.assert_not_called()
        status_sender.assert_not_called()


class OrderNotificationIntegrationTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            phone="09122222222", name="خریدار"
        )
        self.admin = User.objects.create_user(
            phone="09123333333", is_staff=True
        )
        self.category = Category.objects.create(slug="sms-tools", title="ابزار")
        self.product = Product.objects.create(
            title="بیل",
            category=self.category,
            price=100_000,
            stock=10,
        )
        self.address = Address.objects.create(
            user=self.customer,
            title="خانه",
            full_name="تحویل گیرنده",
            phone=self.customer.phone,
            province="تهران",
            city="تهران",
            address="خیابان آزمایشی شماره ده",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.customer)

    def create_order(self, *, code="GS-INTEGRATION"):
        order = Order.objects.create(
            code=code,
            user=self.customer,
            full_name="تحویل گیرنده",
            phone=self.customer.phone,
            province="تهران",
            city="تهران",
            address="خیابان آزمایشی شماره ده",
            items_price=200_000,
            total_price=200_000,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            title=self.product.title,
            price=self.product.price,
            qty=2,
        )
        return order

    def test_checkout_notification_runs_only_after_commit(self):
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(cart=cart, product=self.product, qty=2)

        with patch("orders.services.send_new_order_admin_sms") as sender:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                response = self.client.post(
                    "/api/orders",
                    {"addressId": self.address.pk},
                    format="json",
                )
                sender.assert_not_called()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(callbacks), 1)
        order = Order.objects.get(user=self.customer)
        sender.assert_called_once_with(
            order_id=order.pk,
            order_number=order.code,
            customer_name=self.address.full_name,
            order_total=order.total_price,
        )

    def test_customer_cancellation_notifies_owner_after_commit(self):
        order = self.create_order()

        with patch("orders.services.send_order_status_changed_sms") as sender:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                response = self.client.post(f"/api/orders/{order.pk}")
                sender.assert_not_called()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(callbacks), 1)
        sender.assert_called_once_with(
            order_id=order.pk,
            owner_id=self.customer.pk,
            order_number=order.code,
            order_status="لغو شده",
        )

    def test_admin_patch_skips_same_status_and_sends_each_transition(self):
        order = self.create_order()
        self.client.force_authenticate(self.admin)

        with patch("orders.services.send_order_status_changed_sms") as sender:
            with self.captureOnCommitCallbacks(execute=True) as unchanged_callbacks:
                unchanged = self.client.patch(
                    f"/api/admin/orders/{order.pk}",
                    {"status": Order.Status.PENDING},
                    format="json",
                )
            with self.captureOnCommitCallbacks(execute=True) as paid_callbacks:
                paid = self.client.patch(
                    f"/api/admin/orders/{order.pk}",
                    {"status": Order.Status.PAID},
                    format="json",
                )
                sender.assert_not_called()
            with self.captureOnCommitCallbacks(execute=True) as shipped_callbacks:
                shipped = self.client.patch(
                    f"/api/admin/orders/{order.pk}",
                    {"status": Order.Status.SHIPPED},
                    format="json",
                )

        self.assertEqual(unchanged.status_code, 200)
        self.assertEqual(paid.status_code, 200)
        self.assertEqual(shipped.status_code, 200)
        self.assertEqual(unchanged_callbacks, [])
        self.assertEqual(len(paid_callbacks), 1)
        self.assertEqual(len(shipped_callbacks), 1)
        common = {
            "order_id": order.pk,
            "owner_id": self.customer.pk,
            "order_number": order.code,
        }
        self.assertEqual(
            sender.call_args_list,
            [
                call(order_status="پرداخت شده", **common),
                call(order_status="ارسال شده", **common),
            ],
        )
