from unittest.mock import call, patch

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.sms import SmsDeliveryError, SmsDeliveryResult
from carts.models import Cart, CartItem
from catalog.models import Category, Product

from .models import Order, OrderItem


class OrderCancellationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(phone="09121234567")
        category = Category.objects.create(slug="tools", title="ابزار")
        self.product = Product.objects.create(
            title="بیل", category=category, price=100_000, stock=3
        )
        self.order = Order.objects.create(
            code="GS-TEST",
            user=self.user,
            full_name="کاربر آزمایشی",
            phone=self.user.phone,
            province="تهران",
            city="تهران",
            address="خیابان آزمایشی شماره ده",
            items_price=200_000,
            total_price=200_000,
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            title=self.product.title,
            price=self.product.price,
            qty=2,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_cancel_restores_stock_only_once(self):
        first = self.client.post(f"/api/orders/{self.order.id}")
        second = self.client.post(f"/api/orders/{self.order.id}")

        self.product.refresh_from_db()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(self.product.stock, 5)

    def test_admin_cancel_restores_stock_and_canceled_order_is_terminal(self):
        admin = get_user_model().objects.create_user(
            phone="09120000000", is_staff=True
        )
        self.client.force_authenticate(admin)

        canceled = self.client.patch(
            f"/api/admin/orders/{self.order.id}",
            {"status": Order.Status.CANCELED},
            format="json",
        )
        reopened = self.client.patch(
            f"/api/admin/orders/{self.order.id}",
            {"status": Order.Status.PENDING},
            format="json",
        )

        self.product.refresh_from_db()
        self.assertEqual(canceled.status_code, 200)
        self.assertEqual(reopened.status_code, 409)
        self.assertEqual(self.product.stock, 5)


TEST_ORDER_SMS_IPPANEL = {
    "NEW_ORDER_PATTERN_CODE": "new-order-pattern",
    "ORDER_STATUS_PATTERN_CODE": "order-status-pattern",
}


@override_settings(
    ORDER_SMS_ENABLED=True,
    IPPANEL=TEST_ORDER_SMS_IPPANEL,
)
class OrderSmsNotificationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            phone="09121234567", name="خریدار"
        )
        category = Category.objects.create(slug="sms-tools", title="ابزار پیامک")
        self.product = Product.objects.create(
            title="دریل",
            category=category,
            price=1_000_000,
            stock=20,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def create_order(self, *, code: str = "GS-SMS") -> Order:
        return Order.objects.create(
            code=code,
            user=self.user,
            full_name="خریدار آزمایشی",
            phone=self.user.phone,
            province="تهران",
            city="تهران",
            address="خیابان آزمایشی شماره بیست",
            items_price=self.product.price,
            total_price=self.product.price,
        )

    def add_cart_item(self) -> None:
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, qty=1)

    def checkout_payload(self) -> dict:
        return {
            "fullName": "خریدار آزمایشی",
            "province": "تهران",
            "city": "تهران",
            "address": "خیابان آزمایشی شماره بیست",
        }

    @patch("orders.notifications.send_pattern_sms")
    def test_checkout_notifies_every_active_staff_admin_only(self, send_sms):
        first_admin = get_user_model().objects.create_user(
            phone="09120000001", is_staff=True
        )
        second_admin = get_user_model().objects.create_user(
            phone="09120000002", is_staff=True
        )
        get_user_model().objects.create_user(
            phone="09120000003", is_staff=True, is_active=False
        )
        get_user_model().objects.create_user(
            phone="09120000004", is_seo_manager=True
        )
        self.add_cart_item()

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/orders", self.checkout_payload(), format="json"
            )

        self.assertEqual(response.status_code, 201)
        order = Order.objects.get()
        params = {
            "customer_name": "خریدار آزمایشی",
            "order_code": order.code,
        }
        self.assertEqual(send_sms.call_count, 2)
        send_sms.assert_has_calls(
            [
                call(first_admin.phone, "new-order-pattern", params),
                call(second_admin.phone, "new-order-pattern", params),
            ],
            any_order=True,
        )

    @patch("orders.notifications.send_pattern_sms")
    def test_one_admin_delivery_failure_does_not_skip_the_others_or_fail_checkout(
        self, send_sms
    ):
        first_admin = get_user_model().objects.create_user(
            phone="09120000001", is_staff=True
        )
        second_admin = get_user_model().objects.create_user(
            phone="09120000002", is_staff=True
        )
        attempted_phones = []

        def deliver(phone, _pattern, _params):
            attempted_phones.append(phone)
            if phone == first_admin.phone:
                raise SmsDeliveryError("provider unavailable")
            return SmsDeliveryResult("42")

        send_sms.side_effect = deliver
        self.add_cart_item()

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/orders", self.checkout_payload(), format="json"
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Order.objects.count(), 1)
        self.assertCountEqual(
            attempted_phones,
            [first_admin.phone, second_admin.phone],
        )

    @patch("orders.notifications.send_pattern_sms")
    def test_rolled_back_order_does_not_notify_admins(self, send_sms):
        get_user_model().objects.create_user(phone="09120000001", is_staff=True)

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    self.create_order(code="GS-ROLLBACK")
                    raise RuntimeError("force rollback")

        self.assertEqual(callbacks, [])
        send_sms.assert_not_called()
        self.assertFalse(Order.objects.filter(code="GS-ROLLBACK").exists())

    @override_settings(ORDER_SMS_ENABLED=False, IPPANEL={})
    @patch("orders.notifications.send_pattern_sms")
    def test_disabled_notifications_need_no_patterns_and_schedule_nothing(
        self, send_sms
    ):
        get_user_model().objects.create_user(phone="09120000001", is_staff=True)

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            order = self.create_order(code="GS-DISABLED")
            order.status = Order.Status.PAID
            order.save(update_fields=["status"])

        self.assertEqual(callbacks, [])
        send_sms.assert_not_called()

    @patch("orders.notifications.send_pattern_sms")
    def test_only_a_real_status_transition_notifies_the_customer(self, send_sms):
        order = self.create_order()

        with self.captureOnCommitCallbacks(execute=True):
            order.status = Order.Status.PAID
            order.save(update_fields=["status"])

        send_sms.assert_called_once_with(
            self.user.phone,
            "order-status-pattern",
            {"order_code": order.code, "status": Order.Status.PAID.label},
        )

        send_sms.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            order.save(update_fields=["status"])
            order.full_name = "نام ویرایش‌شده"
            order.save(update_fields=["full_name"])

        send_sms.assert_not_called()

    @patch("orders.notifications.send_pattern_sms")
    def test_admin_api_status_update_notifies_snapshot_phone(self, send_sms):
        order = self.create_order()
        admin = get_user_model().objects.create_user(
            phone="09120000001", is_staff=True
        )
        self.client.force_authenticate(admin)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                f"/api/admin/orders/{order.id}",
                {"status": Order.Status.SHIPPED},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        send_sms.assert_called_once_with(
            order.phone,
            "order-status-pattern",
            {"order_code": order.code, "status": Order.Status.SHIPPED.label},
        )

    @patch("orders.notifications.send_pattern_sms")
    def test_customer_cancellation_sends_canceled_status_once(self, send_sms):
        order = self.create_order()
        OrderItem.objects.create(
            order=order,
            product=self.product,
            title=self.product.title,
            price=self.product.price,
            qty=1,
        )

        with self.captureOnCommitCallbacks(execute=True):
            first = self.client.post(f"/api/orders/{order.id}")
        with self.captureOnCommitCallbacks(execute=True):
            second = self.client.post(f"/api/orders/{order.id}")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        send_sms.assert_called_once_with(
            order.phone,
            "order-status-pattern",
            {"order_code": order.code, "status": Order.Status.CANCELED.label},
        )
