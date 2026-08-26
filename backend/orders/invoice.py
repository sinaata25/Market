"""Build official order invoices exclusively from stored purchase snapshots."""

from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Order


PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


class InvoiceConfigurationError(RuntimeError):
    """Raised when a required local branding asset is unavailable."""


def to_persian_digits(value: object) -> str:
    return str(value).translate(PERSIAN_DIGITS)


def format_amount(value: int) -> str:
    return to_persian_digits(f"{value:,}".replace(",", "٬"))


def format_invoice_datetime(value) -> str:
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return to_persian_digits(value.strftime("%Y/%m/%d - %H:%M"))


def _asset_uri(setting_name: str) -> str:
    path = Path(getattr(settings, setting_name, ""))
    if not path.is_file():
        raise InvoiceConfigurationError(
            f"{setting_name} does not point to a readable file: {path}"
        )
    return path.resolve().as_uri()


def build_invoice_context(order: Order) -> dict:
    """Return presentation data while retaining raw snapshot values for auditing."""
    store_name = settings.INVOICE_STORE_NAME
    if not store_name:
        raise InvoiceConfigurationError("INVOICE_STORE_NAME must not be empty")

    lines = []
    # Keep repeat downloads deterministic even though OrderItem has no model
    # ordering; sorting the prefetched objects avoids an extra database query.
    items = sorted(order.items.all(), key=lambda item: item.pk)
    for index, item in enumerate(items, start=1):
        # ``price`` is the paid unit price snapshot. ``old_price`` is only the
        # pre-discount snapshot and is never replaced with the current product.
        # Checkout treats a legacy zero ``old_price`` as "no list price" when
        # calculating ``items_price``; mirror that snapshot meaning here.
        list_price = item.old_price or item.price
        unit_discount = max(list_price - item.price, 0)
        line_total = item.price * item.qty
        lines.append(
            {
                "position": to_persian_digits(index),
                "title": item.title,
                "qty": item.qty,
                "qty_display": to_persian_digits(item.qty),
                "list_price": list_price,
                "list_price_display": format_amount(list_price),
                "unit_discount": unit_discount,
                "unit_discount_display": format_amount(unit_discount),
                "unit_price": item.price,
                "unit_price_display": format_amount(item.price),
                "line_total": line_total,
                "line_total_display": format_amount(line_total),
            }
        )

    address_parts = [order.province, order.city, order.address]
    full_address = "، ".join(part.strip() for part in address_parts if part.strip())
    issued_at = format_invoice_datetime(order.created_at)

    return {
        "document_title": f"فاکتور {order.invoice_number}",
        "store_name": store_name,
        "logo_uri": _asset_uri("INVOICE_LOGO_PATH"),
        "regular_font_uri": _asset_uri("INVOICE_FONT_REGULAR_PATH"),
        "bold_font_uri": _asset_uri("INVOICE_FONT_BOLD_PATH"),
        "invoice_number": order.invoice_number,
        "order_code": order.code,
        # Issuance is deterministic and does not mutate an order on download.
        "issued_at": issued_at,
        "ordered_at": issued_at,
        "status": order.status,
        "status_label": order.get_status_display(),
        "total_label": (
            "مبلغ نهایی پرداخت‌شده"
            if order.status == Order.Status.PAID
            else (
                "مبلغ نهایی سفارش لغوشده"
                if order.status == Order.Status.CANCELED
                else (
                    "مبلغ نهایی سفارش"
                    if order.status
                    in {Order.Status.SHIPPED, Order.Status.DELIVERED}
                    else "مبلغ نهایی قابل پرداخت"
                )
            )
        ),
        "customer": {
            "full_name": order.full_name,
            "phone": order.phone,
            "phone_display": to_persian_digits(order.phone),
            "address": full_address,
            "postal_code": order.postal_code,
            "postal_code_display": to_persian_digits(order.postal_code),
        },
        "lines": lines,
        # These totals are intentionally read verbatim from the order snapshot.
        "summary": {
            "items_price": order.items_price,
            "items_price_display": format_amount(order.items_price),
            "discount": order.discount,
            "discount_display": format_amount(order.discount),
            "shipping_price": order.shipping_price,
            "shipping_price_display": format_amount(order.shipping_price),
            "total_price": order.total_price,
            "total_price_display": format_amount(order.total_price),
        },
    }


def render_invoice_pdf(order: Order) -> bytes:
    """Render an A4, RTL, multi-page PDF fully in memory."""
    from weasyprint import HTML, default_url_fetcher
    from weasyprint.text.fonts import FontConfiguration

    context = build_invoice_context(order)
    html = render_to_string("orders/invoice.html", context)
    allowed_assets = {
        uri
        for uri in (
            context["logo_uri"],
            context["regular_font_uri"],
            context["bold_font_uri"],
        )
        if uri
    }

    def fetch_local_invoice_asset(url: str, *args, **kwargs):
        if url not in allowed_assets:
            raise ValueError("Invoice templates may only load configured local assets")
        return default_url_fetcher(url, *args, **kwargs)

    return HTML(
        string=html,
        base_url=Path(settings.BASE_DIR).resolve().as_uri(),
        url_fetcher=fetch_local_invoice_asset,
    ).write_pdf(
        font_config=FontConfiguration(),
        optimize_images=True,
    )
