# Orders app contributor guide

## Responsibility

`orders` converts the authenticated user's cart into an immutable purchase
snapshot, decrements stock transactionally, lists owned orders, and supports
customer cancellation with exactly-once stock restoration.

## Module map

- `models.py`: order header, status machine, and snapshot line items.
- `views.py`: validation, checkout transaction, DTOs, listing/detail/cancellation.
- `notifications.py`: post-commit admin/customer SMS delivery.
- `signals.py`: detects creation and persisted status transitions.
- `admin.py`: Django admin inspection of orders and inline items.
- `tests.py`: cancellation and stock-restoration invariants.

## Data model

`Order` belongs to a user and has a unique human-facing code. Delivery fields are
copied onto the order so later profile-address edits do not rewrite purchase
history. `items_price`, `discount`, `shipping_price`, and `total_price` are integer
toman snapshots. Status choices are the allowed state vocabulary; canceled is
terminal in current behavior.

`OrderItem` stores the product foreign key plus copied `title` and `price`. The
copies preserve what was purchased if catalog title/price later changes. Product
deletion is protected/nullable according to the model relationship; contributor
code should use snapshot fields for historical display and accounting.

## Input validation

`CreateOrderSerializer` validates recipient, canonical Iranian phone, province,
city, sufficiently detailed address, optional postal code, and payment method.
Cross-field validation rejects unsupported payment choices. Input serializers are
the trust boundary for shape, but product price/stock and totals always come from
the database.

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

## SMS notifications

Creating an order schedules one approved-pattern SMS for every active staff user.
Changing an existing order's status schedules one SMS to the phone copied onto the
order. Initial creation is not treated as a customer-facing status change, and
saving the same status again must not send another message.

Signals register callbacks with `transaction.on_commit()`, so rolled-back orders
or transitions never produce a message and provider I/O never runs while checkout
locks are held. Delivery failure is logged and does not roll back a valid order.
IPPanel does not provide an idempotency key for this endpoint, so uncertain sends
are not retried automatically. A durable retry guarantee would require a
transactional outbox and a worker.

The IPPanel account needs two separately approved patterns. The new-order pattern
uses `customer_name` and `order_code`; the status pattern uses `order_code` and
`status`. Configure their codes with `IPPANEL_NEW_ORDER_PATTERN_CODE` and
`IPPANEL_ORDER_STATUS_PATTERN_CODE`, then opt in with `ORDER_SMS_ENABLED=true`.
The feature defaults off so an existing deployment can receive the code before
its approved patterns are provisioned. Status writes must use `Order.save()`;
queryset bulk updates and raw SQL bypass Django signals.

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
