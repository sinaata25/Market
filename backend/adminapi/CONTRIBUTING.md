# Admin API contributor guide

## Responsibility

`adminapi` is the JSON management surface used by the custom frontend dashboard.
It is distinct from Django admin and owns no database models. It orchestrates
models from accounts, catalog, and orders.

## Module map

- `views.py`: DTOs, statistics, and the operational management endpoints.
- `views_users.py`: user management — list, create, edit, role change, delete.
- `views_managers.py`: manager admin accounts and the SEO-access grant (superuser).
- `views_seo_admins.py`: SEO admin accounts.
- `urls.py`: routes under `/api/admin/`.
- `tests.py`: product/low-stock/pagination contract coverage.
- `tests_user_management.py`: the capability matrix, per role, plus crafted-payload
  privilege-escalation attempts.
- `tests_managers.py` / `tests_seo_admins.py`: privileged-account lifecycles.
- `apps.py`: normal Django app registration. The empty migrations package exists
  even though this app currently owns no models.

## Authorization boundary

Every authorization decision comes from `accounts/roles.py`; this app only wires
DRF mixins from `accounts/permissions.py` onto views. Never re-derive a role from
raw flags (`user.is_staff and not user.is_superuser`) inside a view.

- `ShopAdminRequiredMixin` — the operational dashboard: superuser, manager admin,
  regular admin. SEO admins and customers are rejected.
- `UserManagementRequiredMixin` — user management. Passing this mixin only gets a
  caller *into* the section; how much they see is decided by
  `accounts.selectors.visible_users_for()`.
- `SeoAdminManagementRequiredMixin` — managing SEO admin accounts: superuser, or a
  manager admin the superuser granted SEO access.
- `DeveloperOnlyMixin` — system-level areas (manager accounts, granting SEO
  access). Superuser only.

When adding an endpoint, inherit the right mixin before `APIView`. Global DRF
permissions allow anonymous access by default, so omitting the mixin is a security
bug.

### Roles

Roles are *derived* from existing flags, never stored in a parallel column
(`accounts.roles.Role` / `role_of()`):

| Role          | Condition                                            |
| ------------- | ---------------------------------------------------- |
| Superuser     | `is_superuser` — Django's own mechanism, untouched   |
| Manager admin | `is_manager_admin and is_staff`, not superuser        |
| Regular admin | `is_staff` with no other role                         |
| SEO admin     | `is_seo_manager` (separate branch, never `is_staff`)  |
| Customer      | none of the above                                     |

`can_access_seo` is an added capability on a manager admin, granted and revoked
only by a superuser through `views_managers.py`.

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

## Brand, category, and product management

Brand management exposes staff-only list/create/update/delete endpoints plus a
separate multipart logo endpoint. A brand referenced by products cannot be
deleted. `brandSlug` on product writes assigns one brand or `null` without changing
category assignments. Inactive brands remain manageable but disappear from public
brand navigation.

`POST brands/<id>/price-adjustment` accepts an `increase` or `decrease` operation
and a positive decimal percentage. Decreases must be below 100%. The catalog
service locks and adjusts only products with that exact brand inside one database
transaction, using `Decimal` and half-up rounding to the project's whole-toman
precision. Both current and non-null old prices move by the same factor; other
brands and unbranded products remain untouched. Keep this business logic in
`catalog.brand_pricing`, not in the API view.

Category management exposes staff-only list/create/update/delete endpoints plus a
separate multipart icon endpoint. Category deletion returns a controlled conflict
while products reference it. Icon replacement/removal uses catalog's deferred,
unreferenced-file cleanup helper; do not delete storage objects before the database
change commits. Staff can toggle `isActive`; inactive categories stay available in
the management API but are omitted from the public category feed. `parentIds`
assigns zero or more real parent categories. Updates reject self-links and cycles;
categories with children cannot be deleted until those relationships are moved.
Responses expose both explicit `isActive` and derived `effectiveIsActive` so the
dashboard can distinguish a manually hidden category from one hidden by an ancestor.

`ProductWriteSerializer` defines the dashboard write contract, including camelCase
names and JSON content. `categorySlugs` accepts one or more unique category slugs;
the first becomes the backward-compatible primary category and all values populate
the many-to-many relation. The legacy singular `categorySlug` input remains
accepted. Optional `brandSlug` maps separately to `Product.brand`. Cross-field
validation enforces price-related rules. `apply_product_data()`
has been replaced by catalog's transactional `save_product_with_specifications()`
service so core fields, categories, and optional ordered specification replacement
commit or roll back together. Omitting `specifications` preserves current rows;
sending an empty list removes them.

- `GET/POST products`: filtered/paginated list and creation.
- `GET/PATCH/DELETE products/<id>`: detail mutation.
- `PATCH products/<id>/visibility`: hide or show a product without deleting it.
- `POST products/<id>/image`: multipart gallery upload.
- `DELETE products/<id>/images/<image-id>`: deletion scoped to its product.
- `GET/POST brands`: list and create brands.
- `PATCH/DELETE brands/<id>`: update or safely delete an unused brand.
- `POST/DELETE brands/<id>/logo`: replace or remove a validated logo.
- `POST brands/<id>/price-adjustment`: atomic staff-only bulk price adjustment.
- `GET/POST specifications`: searchable reusable-key list and creation.
- `PATCH/DELETE specifications/<id>`: rename or safely delete an unused key.

List responses use `product_dto()` and omit specifications; detail responses use
`admin_product_dto()` and include ordered specifications. Bulk queries select
category and brand and prefetch images. Detail queries additionally prefetch
specification values with their keys. Uploaded image IDs are
scoped to the URL product to prevent deleting another product's asset. Product deletion may
be blocked by protected order history; return a controlled conflict rather than
destroying historical integrity.

## User and comment management

User management lives in `views_users.py`, not `views.py`. It returns/searches
users and aggregate activity without exposing password hashes, OTP hashes, or
private authentication state. Be deliberate when adding personal information.

Three rules keep it safe, and all three must hold for any new user endpoint:

1. **Restrict before serializing.** Read through `visible_users_for(request.user)`
   so an invisible record never leaves the database. Filtering a full queryset in
   the response — or in React — is a security bug.
2. **Invisible record → 404, not 403.** A manager admin requesting a superuser's
   id must not learn that the account exists. 403 is for a record the caller *can*
   see but an operation they may not perform.
3. **Never let a role field reach the model directly.** `UserCreateSerializer` and
   `UserUpdateSerializer` contain no `is_superuser`, `is_staff`, `groups`, or
   `user_permissions` at all, so sending them is inert. `role`, `isActive` and
   `canAccessSeo` each pass a separate capability check before being applied, and
   role writes go through `apply_role()` so flag combinations stay consistent.

`GET` responses carry a `permissions` object so the dashboard can render controls
without duplicating the rules. It is a UI hint — the same checks run again on
write.

`AdminCommentListView` joins comment/user/product and can filter by moderation
status. `AdminCommentDetailView` approves, rejects/unpublishes, or deletes a
message. `AdminCommentResponseView` always authors replies from the authenticated
staff account and publishes them immediately. It never accepts an admin-indicator
flag from the client. Ratings are independent and are not changed by comment
moderation.

## Response and query conventions

All responses use `common.responses.ok()`/`fail()` and therefore the
`{ok, data}`/`{ok, error}` envelope. API field names are camelCase. Validate and
bound page sizes. Use `select_related` for single-valued relationships and
`prefetch_related` for collections in list endpoints.

## Safe change checklist

1. Put the correct `*RequiredMixin` from `accounts/permissions.py` on every new view.
2. Never broaden dashboard access to SEO-only users, and never widen a role check
   by hand — change `accounts/roles.py` so every caller moves together.
3. Keep cancellation and stock restoration atomic and exactly-once.
4. Reuse canonical DTO/mapping helpers rather than creating response drift.
5. Scope nested image/review/object lookups to their parent where applicable.
6. Avoid exposing credentials, OTP state, or password hashes in user responses.
7. Add permission coverage to `tests_user_management.py` for anything touching
   roles, visibility, or account state — including the crafted-payload case.
8. Run `./.venv/bin/python manage.py test adminapi orders catalog accounts seo --verbosity 2`.
