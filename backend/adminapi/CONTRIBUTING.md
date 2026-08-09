# Admin API contributor guide

## Responsibility

`adminapi` is the JSON management surface used by the custom frontend dashboard.
It is distinct from Django admin and owns no database models. It orchestrates
models from accounts, catalog, and orders.

## Module map

- `views.py`: permission policy, DTOs, statistics, and all management endpoints.
- `urls.py`: routes under `/api/admin/`.
- `tests.py`: current product/low-stock/pagination contract coverage.
- `apps.py`: normal Django app registration. The empty migrations package exists
  even though this app currently owns no models.

## Authorization boundary

`IsStaff.has_permission()` requires an authenticated user with `is_staff=True`.
`StaffRequiredMixin` applies it consistently to every view. Do not use
`is_seo_manager` here: that role is intentionally isolated to SEO data and must
not gain access to users, orders, revenue, or stock.

When adding an endpoint, inherit `StaffRequiredMixin` before `APIView`. Global DRF
permissions allow anonymous access by default, so omitting the mixin is a security
bug.

## Shared helpers

`positive_page()` converts pagination input and returns `None` for invalid values;
views return the project validation envelope rather than silently accepting bad
input. `admin_product_dto()` extends the canonical public product DTO with image
IDs needed for deletion. `order_row()` returns delivery, totals, status, and
snapshot line items for dashboard tables/details.

## Dashboard statistics

`StatsView` excludes canceled orders from revenue. It aggregates total revenue,
14 daily buckets (including zero-value days), status counts, top products by sold
quantity/revenue, and other operational counts/low-stock data. Database aggregation
is preferred over loading full tables. When changing definitions, make the business
meaning explicit—for example whether canceled/refunded orders count—and update the
frontend labels and tests together.

## Order management

`AdminOrderListView` supports status/search/pagination and prefetches items.
`AdminOrderDetailView.patch()` validates status against `Order.Status.choices`.
Transitioning to canceled restores stock transactionally and only once; a canceled
order is terminal. Product rows are locked/updated consistently with the customer
cancellation flow. Do not implement status changes as an unchecked `update()` or
stock can be restored twice.

## Category and product management

Category management exposes staff-only list/create/update/delete endpoints plus a
separate multipart icon endpoint. Category deletion returns a controlled conflict
while products reference it. Icon replacement/removal uses catalog's deferred,
unreferenced-file cleanup helper; do not delete storage objects before the database
change commits. Staff can toggle `isActive`; inactive categories stay available in
the management API but are omitted from the public category feed.

`ProductWriteSerializer` defines the dashboard write contract, including camelCase
names and JSON content. `validate_categorySlug()` resolves the category and places
the model object in validated data. Cross-field validation enforces price-related
rules. `apply_product_data()` centralizes mapping from API names to model fields so
create and update cannot drift.

- `GET/POST products`: filtered/paginated list and creation.
- `GET/PATCH/DELETE products/<id>`: detail mutation.
- `POST products/<id>/image`: multipart gallery upload.
- `DELETE products/<id>/images/<image-id>`: deletion scoped to its product.

List responses use `product_dto()`; detail responses use `admin_product_dto()`.
Bulk queries select category and prefetch images. Uploaded image IDs are scoped to
the URL product to prevent deleting another product's asset. Product deletion may
be blocked by protected order history; return a controlled conflict rather than
destroying historical integrity.

## User and review management

`AdminUserListView` returns/searches users and aggregate activity without exposing
password hashes, OTP hashes, or private authentication state. Be deliberate when
adding personal information.

`AdminReviewListView` joins review/user/product for dashboard display.
`AdminReviewDetailView.delete()` remembers the product, deletes the review, and
calls `recompute_rating()`. That helper recalculates both denormalized rating fields;
never delete a review without keeping product aggregates synchronized.

## Response and query conventions

All responses use `common.responses.ok()`/`fail()` and therefore the
`{ok, data}`/`{ok, error}` envelope. API field names are camelCase. Validate and
bound page sizes. Use `select_related` for single-valued relationships and
`prefetch_related` for collections in list endpoints.

## Safe change checklist

1. Put `StaffRequiredMixin` on every new view.
2. Never broaden staff access to SEO-only users.
3. Keep cancellation and stock restoration atomic and exactly-once.
4. Reuse canonical DTO/mapping helpers rather than creating response drift.
5. Scope nested image/review/object lookups to their parent where applicable.
6. Avoid exposing credentials, OTP state, or password hashes in user responses.
7. Run `./.venv/bin/python manage.py test adminapi orders catalog --verbosity 2`.
