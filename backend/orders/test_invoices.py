from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from catalog.models import Category, Product

from .invoice import build_invoice_context, render_invoice_pdf
from .models import Order, OrderItem


class InvoiceTestCase(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(phone="09121234567")
        self.other_customer = get_user_model().objects.create_user(
            phone="09121111111"
        )
        self.staff = get_user_model().objects.create_user(
            phone="09120000000",
            is_staff=True,
        )
        category = Category.objects.create(slug="garden-tools", title="ابزار باغبانی")
        self.shovel = Product.objects.create(
            title="بیل باغبانی حرفه‌ای مدل Green X200",
            category=category,
            price=500_000,
            old_price=600_000,
            stock=10,
        )
        self.saw = Product.objects.create(
            title="اره هرس دستی",
            category=category,
            price=300_000,
            stock=10,
        )
        self.order = Order.objects.create(
            code="GS-INVOICE-001",
            status=Order.Status.PENDING,
            user=self.owner,
            full_name="نیما کشاورز آزمایشی",
            phone=self.owner.phone,
            province="تهران",
            city="تهران",
            address=(
                "خیابان کشاورز، بعد از چهارراه ولیعصر، کوچه باغ بلند، "
                "ساختمان شماره ۱۲۳، طبقه چهارم، واحد دوازدهم"
            ),
            postal_code="1412345678",
            items_price=1_500_000,
            discount=200_000,
            shipping_price=60_000,
            total_price=1_360_000,
        )
        self.shovel_line = OrderItem.objects.create(
            order=self.order,
            product=self.shovel,
            title=self.shovel.title,
            price=500_000,
            old_price=600_000,
            qty=2,
        )
        self.saw_line = OrderItem.objects.create(
            order=self.order,
            product=self.saw,
            title=self.saw.title,
            price=300_000,
            qty=1,
        )
        self.client = APIClient()


class InvoiceContextAndRenderingTests(InvoiceTestCase):
    def test_context_uses_all_stored_financial_snapshots(self):
        original_title = self.shovel_line.title
        self.saw_line.old_price = 0
        self.saw_line.save(update_fields=["old_price"])
        self.shovel.title = "نام جدید کاتالوگ"
        self.shovel.price = 9_000_000
        self.shovel.old_price = None
        self.shovel.save(update_fields=["title", "price", "old_price"])

        context = build_invoice_context(self.order)

        self.assertEqual(len(context["lines"]), 2)
        self.assertEqual(context["lines"][0]["title"], original_title)
        self.assertEqual(context["lines"][0]["list_price"], 600_000)
        self.assertEqual(context["lines"][0]["unit_discount"], 100_000)
        self.assertEqual(context["lines"][0]["unit_price"], 500_000)
        self.assertEqual(context["lines"][0]["line_total"], 1_000_000)
        self.assertEqual(context["lines"][1]["list_price"], 300_000)
        self.assertEqual(context["lines"][1]["unit_discount"], 0)
        self.assertEqual(context["summary"]["items_price"], 1_500_000)
        self.assertEqual(context["summary"]["discount"], 200_000)
        self.assertEqual(context["summary"]["shipping_price"], 60_000)
        self.assertEqual(context["summary"]["total_price"], 1_360_000)

    def test_real_pdf_generation_supports_persian_and_mixed_unicode(self):
        pdf = render_invoice_pdf(self.order)

        self.assertIsInstance(pdf, bytes)
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreater(len(pdf), 10_000)

    def test_invoice_number_is_stable_unique_derivative_of_order_code(self):
        self.assertEqual(self.order.invoice_number, "INV-GS-INVOICE-001")
        self.order.refresh_from_db()
        self.assertEqual(self.order.invoice_number, "INV-GS-INVOICE-001")


class InvoiceDownloadPermissionTests(InvoiceTestCase):
    def test_customer_can_download_own_invoice_with_pdf_headers(self):
        self.client.force_authenticate(self.owner)

        response = self.client.get(f"/api/orders/{self.order.pk}/invoice")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="invoice-INV-GS-INVOICE-001.pdf"',
        )
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertIn("Cookie", response["Vary"])
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertGreater(len(response.content), 10_000)

    @patch("orders.views.render_invoice_pdf")
    def test_customer_cannot_download_another_customers_invoice(self, render):
        self.client.force_authenticate(self.other_customer)

        response = self.client.get(f"/api/orders/{self.order.pk}/invoice")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, {"ok": False, "error": "سفارش یافت نشد"})
        render.assert_not_called()

    @patch("orders.views.render_invoice_pdf", return_value=b"%PDF-1.7 staff")
    def test_staff_can_download_any_customers_invoice(self, render):
        self.client.force_authenticate(self.staff)

        response = self.client.get(f"/api/orders/{self.order.pk}/invoice")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        render.assert_called_once()

    @patch("orders.views.render_invoice_pdf")
    def test_missing_order_returns_standard_api_error(self, render):
        self.client.force_authenticate(self.owner)

        response = self.client.get("/api/orders/999999/invoice")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, {"ok": False, "error": "سفارش یافت نشد"})
        render.assert_not_called()

    def test_anonymous_request_returns_standard_authentication_error(self):
        response = self.client.get(f"/api/orders/{self.order.pk}/invoice")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, {"ok": False, "error": "ابتدا وارد شوید"})

    @patch("orders.views.render_invoice_pdf", side_effect=RuntimeError("renderer failed"))
    def test_render_failure_returns_standard_api_error(self, render):
        self.client.force_authenticate(self.owner)

        with self.assertLogs("orders.views", level="ERROR"):
            response = self.client.get(f"/api/orders/{self.order.pk}/invoice")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.data,
            {"ok": False, "error": "ساخت فایل فاکتور ممکن نشد"},
        )
        render.assert_called_once()

    @override_settings(INVOICE_LOGO_PATH=Path(settings.BASE_DIR) / "missing-logo.png")
    def test_missing_required_brand_asset_returns_controlled_api_error(self):
        self.client.force_authenticate(self.owner)

        with self.assertLogs("orders.views", level="ERROR"):
            response = self.client.get(f"/api/orders/{self.order.pk}/invoice")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data["ok"], False)
        self.assertEqual(response.data["error"], "ساخت فایل فاکتور ممکن نشد")
