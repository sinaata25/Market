# Orders app contributor guide

## Responsibility

`orders` converts the authenticated user's cart into an immutable purchase
snapshot, decrements stock transactionally, lists owned orders, and supports
customer cancellation with exactly-once stock restoration.

## Module map

- `models.py`: order header, status machine, and snapshot line items.
- `views.py`: validation, checkout transaction, DTOs, listing/detail/cancellation.
- `admin.py`: Django admin inspection of orders and inline items.
- `tests.py`: cancellation and stock-restoration invariants.
- `invoice.py`: immutable invoice context and in-process PDF rendering.
- `templates/orders/invoice.html`: print-friendly A4/RTL invoice presentation.
- `test_invoices.py`: invoice snapshot, permission, response, and rendering tests.

## Data model

`Order` belongs to a user and has a unique human-facing code. Delivery fields are
copied onto the order so later profile-address edits do not rewrite purchase
history. `items_price`, `discount`, `shipping_price`, and `total_price` are integer
toman snapshots. Status choices are the allowed state vocabulary; canceled is
terminal in current behavior.

Delivery snapshots also include nullable official `province_code` and `city_code`
values. Existing orders retain their historic strings with null codes. New manual
checkout locations are validated by the application-owned 1404 reference dataset;
saved legacy addresses remain usable and copy their strings/codes as-is.

`OrderItem` stores the product foreign key plus copied `title` and `price`. The
copies preserve what was purchased if catalog title/price later changes. Product
deletion is protected/nullable according to the model relationship; contributor
code should use snapshot fields for historical display and accounting.

## Input validation

`CreateOrderSerializer` validates recipient, province/city membership,
sufficiently detailed address, and optional postal code. It accepts official
`provinceId`/`cityId` codes while retaining validated name-only compatibility.
Input serializers are the trust boundary for shape, but product price/stock and
totals always come from the database.

## Checkout transaction

`OrderListCreateView.post()` requires authentication and a non-empty current cart.
Inside one `transaction.atomic()` block it:

1. Re-reads cart lines and locks product rows with `select_for_update()`.
2. Verifies every requested quantity against current stock.
3. Computes prices from locked products, never from request/cart response values.
4. Generates a unique order code and creates the order header.
5. Creates snapshot `OrderItem` rows.
6. Decrements product stock.
7. Deletes consumed cart items only after order creation succeeds.

`OutOfStock` provides a controlled rollback/error path. Any exception in the
atomic block must leave stock, order, items, and cart mutually consistent. Keep
external payment/network calls outside this transaction; a future payment flow
needs an explicit pending/idempotency design rather than holding locks over I/O.

`new_order_code()` provides a short display code. Database uniqueness is the final
authority; if generation strategy changes, handle collisions without exposing a
partial order.

## Cancellation

The order detail POST action cancels an eligible owned order. It locks the order,
checks that it is not already canceled/terminal, locks related product rows, adds
each snapshot quantity back with database expressions, and changes status in the
same transaction. Locking and the status check ensure retries restore stock only
once. Admin cancellation follows the same invariant in `adminapi`; changes must
keep both paths aligned.

## DTO and endpoints

`order_dto()` returns camelCase order data and snapshot line items. Keep historical
fields sourced from `OrderItem`, not current product data.

- `GET /api/orders`: authenticated user's orders only.
- `POST /api/orders`: create from the current cart.
- `GET /api/orders/<id>`: retrieve only an order owned by the user.
- `POST /api/orders/<id>`: cancel an eligible owned order.
- `GET /api/orders/<id>/invoice`: download the owner's invoice PDF; staff may
  download any order using the same endpoint.

## Official PDF invoices

Invoices are rendered locally with WeasyPrint; no order/customer data is sent to
an external service. Install Python packages from `requirements.txt` and ensure
the deployment image includes Pango, Fontconfig, and HarfBuzz (including the
HarfBuzz subset library used for embedded fonts). The renderer requires the
configured logo plus regular/bold Vazirmatn font files. Monorepo defaults point
to `frontend/public`; separately packaged deployments must set the absolute
`INVOICE_LOGO_PATH`, `INVOICE_FONT_REGULAR_PATH`, and
`INVOICE_FONT_BOLD_PATH`. `INVOICE_STORE_NAME` overrides the storefront name.

The invoice number is `INV-<order code>`. The underlying order code is database
unique, unguessable, and read-only in Django admin, so all existing and future
orders receive a stable unique invoice number without a migration or a write at
download time. The order timestamp is the deterministic issue date.

Every financial value comes from `Order` and `OrderItem`: header subtotal,
discount, shipping, total, item title, old/list unit price, final unit price, and
quantity. Current `Product` values are never read. Tax, payment transaction, and
legal registration details are deliberately absent because this project has no
such persisted fields.

All ownership queries must include `user=request.user`. Staff management uses the
separate `/api/admin/orders` surface.

## Safe change checklist

1. Never trust client-submitted totals, prices, titles, or stock.
2. Lock product/order rows and keep all database mutations in one atomic block.
3. Store historical display/accounting values on `Order`/`OrderItem`.
4. Make cancellation idempotent and restore stock exactly once.
5. Keep user queries ownership-scoped.
6. Design payment integrations around idempotency and short transactions.
7. Run `./.venv/bin/python manage.py test orders --verbosity 2`.
