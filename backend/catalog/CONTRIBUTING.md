# Catalog app contributor guide

## Responsibility

`catalog` owns independent brands, categories, products, product images, public
discovery APIs, ratings, comments, and questions. It also defines the canonical
brand/category/product response DTOs reused by the cart, profile, and admin APIs.

## Module map

- `models.py`: catalog entities, including reusable `SpecificationKey` definitions
  and ordered `ProductSpecification` values.
- `dto.py`: stable camelCase public representations for brands/categories/products.
- `brand_pricing.py`: transactional brand-wide percentage price adjustments.
- `brand_files.py`: transaction-aware cleanup of replaced/deleted brand logos.
- `feedback.py`: purchase verification, rating aggregation, comment DTOs, and
  visible conversation selection.
- `specifications.py`: Persian key normalization, specification prefetching, and
  atomic product/specification writes.
- `views.py`: category, product, rating, and comment endpoints.
- `validators.py`: strict PNG and SVG category-icon validation.
- `icon_files.py`: transaction-aware cleanup of replaced/deleted icon files.
- `admin.py`: Django admin, product image inline, and safe icon lifecycle hooks.
- `management/commands/seed_catalog.py`: base catalog seed data.
- `management/commands/seed_demo.py`: richer development/demo data.
- `tests.py`: product and review API contracts.
- `test_brands.py`: brand model, API, permissions, filtering, and pricing tests.
- `test_category_icons.py`: validation, replacement, deletion, and storage tests.

## Data model

`Brand` is separate from the category graph. Its `name` and `slug` are unique;
`description`, validated PNG/SVG `logo`, and `website` are optional. `is_active`
controls public brand navigation and brand-specific filtering, while staff APIs
continue to return inactive brands.

`Category.slug` is the public category identifier. `parents` is a directed
self-referential many-to-many relation, so a category can be a child of multiple
parents. Categories without parents are roots; child-only categories are rendered
only below their parents. `is_active` controls explicit visibility. Effective
public visibility requires an all-active path from a root, so hiding a parent also
hides its exclusive descendants while shared descendants remain reachable through
another active parent. Staff APIs continue to return every category. `icon` accepts
only validated `.png` or `.svg` uploads and may be empty.

`Product.category` is its primary category, retained for stable breadcrumbs, SEO,
and backward-compatible response fields. `Product.categories` contains every
assigned category (including the primary one); write APIs keep both relations in
sync and require at least one category. `Product.brand` is a nullable protected
foreign key, so a product has zero or one brand independently of all category
assignments. Monetary values are integer toman amounts.
`old_price` is nullable and represents the pre-discount display price. `colors` and
`features` are JSON UI content. Rating and rating count are denormalized
onto the product for fast listing/sorting and must be recomputed after rating
creation/update/deletion. `is_active` controls storefront visibility without deleting the
product or its history. Stock is mutated transactionally by the orders app.

`SpecificationKey` is a globally reusable definition. Its `normalized_name` uses
Unicode/Persian canonicalization and is unique, so visually equivalent key names
cannot be duplicated. `ProductSpecification` holds one product-specific text value
and position; `(product, key)` is unique and key deletion is protected while used.

`ProductImage` provides an ordered one-to-many image gallery. Code returning a
product should select `brand` and prefetch `categories` and `images`; otherwise
`product_dto()` creates N+1 queries.

`ProductRating` contains only a 1–5 star value. Its unique database constraint
enforces one rating per user/product; updates replace that value. The API accepts a
rating only when a paid, shipped, or delivered `OrderItem` proves the user purchased
the product. Product aggregates come only from these rows.

`ProductComment` is independent of ratings and supports comments, questions, and
self-referential replies. Every customer-created row starts `pending`; staff-created
official responses start `approved`. Public selectors expose approved rows plus the
authenticated author's own moderated rows. Admin and verified-purchase indicators
are derived from the author role and qualifying order data, never request booleans.

## DTO contract

`brand_dto()`, `category_dto()`, and `product_dto()` deliberately separate the
database schema from the frontend contract. They convert snake_case fields to camelCase, return
relative media URLs (proxied by Next.js), include the full image gallery, and
provide presentation defaults for missing features/description/warranty. Product
detail responses additionally contain ordered `specifications`; summary/list/card
representations deliberately omit them. The product contract includes a brand
object or `null`.

Because `product_dto()` is shared across apps, changing it affects product lists,
details, related products, carts, favorites, and admin responses. Update contract
tests and the frontend together. It expects `category` and `brand` to be selected
and both `categories` and `images` to be prefetched by callers.

## Category icon security and lifecycle

Uploaded SVG is active document content, not merely an image. `validators.py`
therefore reads a size-limited payload and rejects malformed XML, DTD/entity
constructs, scripts, event-handler attributes, external URLs, unsafe namespaces,
and other active content. PNG validation checks signature/chunk structure,
dimensions, decoding, and trailing payloads. Extension and actual content must
agree. Keep these checks fail-closed.

Validation rewinds the uploaded file so storage can read it afterward. Limits
protect memory and decompression workloads; do not replace them with extension or
MIME checks alone because both are attacker-controlled.

Database rollback cannot restore an already deleted storage object. For that
reason, `icon_files.py` schedules old-file deletion with `transaction.on_commit()`.
It also checks whether another category references the same storage name before
deleting. `CategoryAdmin.save_model()` remembers the old name and schedules cleanup
only after a successful replacement. Clear/delete paths follow the same ordering;
protected database deletes must leave the icon intact. Storage deletion failures
are non-fatal after a committed database change and should be logged/handled as
cleanup problems, not turn a completed update into a false API failure.

## Public APIs

- `GET /api/brands`: active brands for storefront navigation and brand pages.
- `GET /api/categories`: effectively visible roots and descendants through
  `category_dto()`; relationships contain real category slugs and titles.
- `GET /api/products`: optional independent category/brand/search/discount
  filters, allow-listed sort keys, and bounded pagination (`perPage` cannot exceed 50).
- `GET /api/products/<id>`: product plus up to four related products, preferring
  the same category and filling with popular products elsewhere.
- `GET /api/products/slug/<slug>`: resolve a product SEO slug through `PageMeta`,
  then delegate to the normal detail representation.
- `GET /api/products/<id>/rating`: aggregate, current user's rating, and eligibility.
- `PUT /api/products/<id>/rating`: create/update one purchaser-only rating.
- `GET /api/products/<id>/comments`: approved threads plus the author's own rows.
- `POST /api/products/<id>/comments`: create a top-level comment/question or reply.

Ratings and comments use separate serializers and payloads. Do not add a rating to
comment writes or comment text to rating writes. Every customer reply independently
passes moderation even when its parent was approved.

## Admin behavior

`BrandAdmin` and `CategoryAdmin` preview validated image assets and manage file
cleanup as described above. `ProductAdmin` embeds image and specification rows as
tabular inlines, and reusable keys have their own protected management screen.
Search/list/filter configuration is operational convenience only; custom
storefront management endpoints live in `adminapi`.

## Seeding

Seed commands are for predictable development content. Keep them idempotent where
possible (use stable slugs/keys and update-or-create semantics) and do not make
production startup depend on demo assets.

## Safe change checklist

1. Treat `product_dto()` as a cross-app public contract.
2. Add `select_related("category", "brand")` and `prefetch_related("categories", "images")`
   to bulk DTO calls.
3. Prefetch ordered specifications with their key only for detail DTO calls.
4. Keep rating and product-specification uniqueness enforced at the database level.
5. Recompute denormalized ratings after every rating mutation.
6. Keep customer moderation, official-author identity, and purchase verification.
7. Never weaken SVG/PNG content validation to MIME/extension checks.
8. Delete replaced files only after transaction commit and only if unreferenced.
9. Run `./.venv/bin/python manage.py test catalog --verbosity 2`.
10. Keep the category graph acyclic in every write surface, including Django admin.
