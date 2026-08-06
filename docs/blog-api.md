# Blog API

The blog uses the store's existing session authentication, CSRF protection, and
`{ok: true, data}` / `{ok: false, error}` response envelope. Public endpoints
only query posts whose status is `PUBLISHED` and whose publication time has
arrived. All write endpoints require an authenticated user with `is_staff=true`.

## Public endpoints

- `GET /api/blog/posts` — published posts. Query parameters: `category`, `tag`,
  `search`, `page`, and `perPage` (maximum 50).
- `GET /api/blog/posts/{slug}` — one published post by stable slug. Draft,
  scheduled, missing, and unpublished posts return 404.
- `GET /api/blog/categories` — categories used by currently visible posts.
- `GET /api/blog/tags` — tags used by currently visible posts.

The list response contains `items`, `total`, `page`, `perPage`, and `pages`.
Post objects use camelCase fields and include author display name, category,
tags, publication time, SEO fields, and a relative `featuredImage` media URL.
Only the detail endpoint includes `content`.

## Staff endpoints

- `GET|POST /api/admin/blog/posts`
- `GET|PATCH|DELETE /api/admin/blog/posts/{id}`
- `POST /api/admin/blog/posts/{id}/publish`
- `POST /api/admin/blog/posts/{id}/unpublish`
- `POST|DELETE /api/admin/blog/posts/{id}/featured-image`
- `GET|POST /api/admin/blog/categories`
- `PATCH|DELETE /api/admin/blog/categories/{id}`
- `GET|POST /api/admin/blog/tags`
- `PATCH|DELETE /api/admin/blog/tags/{id}`

Post create/update fields are `title`, `slug`, `excerpt`, `content`,
`categorySlug`, `tagSlugs`, `status`, `publishedAt`, `seoTitle`, and
`seoDescription`. A published post requires an ISO-8601 `publishedAt`; a draft
must use `null`. The publish action accepts an optional `publishedAt` and uses
the current time when omitted. Featured-image upload uses multipart form data
with a `file` field and accepts validated JPEG, PNG, or WebP images up to 5 MB.

Validation errors use the standard error envelope and HTTP 400 or 422. Missing
objects return 404, and users without store-admin access receive 403. The live
OpenAPI schema and Swagger UI remain available at `/api/schema/` and
`/api/docs/`.
