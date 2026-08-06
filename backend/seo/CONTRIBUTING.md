# SEO app contributor guide

## Responsibility

`seo` stores site-wide SEO settings, per-page overrides and revision history,
redirects, frontend-reported 404s, image-alt management, and scan results. It
provides both public data consumed by Next.js and a restricted management API.

## Module map

- `models.py`: singleton settings, page metadata, revisions, redirects, 404 logs,
  and scan results.
- `services.py`: page discovery, defaults/effective metadata, sitemap, DTOs, and
  structured-data generation.
- `views_public.py`: robots, sitemap, metadata, redirect resolution, and 404 intake.
- `views_admin.py`: dashboard overview and all SEO mutations.
- `urls.py`: separate public/admin pattern lists mounted by `config.urls`.

## Models

`SeoSettings` is a singleton-style row loaded through `SeoSettings.load()`. It
contains canonical site identity, robots text, sitemap switches/exclusions,
frontend feature flags, organization/schema settings, and hreflang JSON. Use the
loader instead of assuming a row already exists.

`PageMeta` is uniquely identified by `(page_type, object_key)`. Page types cover
static, category, and product pages. Blank override fields intentionally mean
“fall back to generated defaults.” Robots flags, social fields, schema type, and
custom JSON-LD live here. `slug` can provide an SEO-facing product route.

`MetaRevision` stores a JSON snapshot and optional editor. It cascades with its
metadata row and is ordered newest first. Revisions should be created before
overwriting meaningful state so rollback remains possible.

`Redirect` has a unique source path, destination, 301/302 status, active flag,
note, and hit counter. Next.js applies these redirects after calling the resolve
endpoint. `NotFoundLog` aggregates path hits and referer/seen timestamps.
`ScanResult` records page/link health, response status, latency, and check time.

## Page identity and effective metadata

`STATIC_PAGES` is the explicit inventory of non-model pages. `all_pages()` appends
current categories and products. `page_path()` translates `(page_type, object_key)`
to a frontend route. Product object keys are database IDs even when an optional
SEO slug exists; changing this identity scheme requires a migration and coordinated
frontend/API changes.

`default_meta_for()` derives useful metadata from site settings and catalog data.
`meta_dto()` returns both stored overrides, generated defaults, and resolved
effective values. The frontend should render effective values. Blank overrides
must continue falling back rather than becoming blank tags.

`meta_to_snapshot()` lists every revisioned field. Whenever a mutable `PageMeta`
field is added, update this function and restore logic together or history will be
partial.

## Sitemap, robots, and structured data

`build_sitemap()` starts from all known pages, applies type inclusion settings,
explicit path exclusions, and per-page `noindex`, then emits XML locations using
`site_url`. Keep output escaped if paths ever become less constrained. The public
view returns 404 when sitemap generation is disabled.

`robots_txt()` serves configured text from the site root. `auto_schema()` builds
JSON-LD for products/categories from current catalog state, including availability,
price, images, and aggregate rating. A valid `schema_custom` override wins;
`parse_schema_custom()` validates JSON before storage. Treat structured data as
data—never inject it into HTML without safe JSON serialization on the frontend.

## Public endpoints

- `GET /robots.txt`: configured plain text.
- `GET /sitemap.xml`: generated XML or 404 when disabled.
- `GET /api/seo/meta?type=…&key=…`: effective metadata, schema, and site flags.
- `GET /api/seo/resolve?path=…`: active redirect and atomic hit increment.
- `POST /api/seo/404`: aggregate non-API frontend 404 reports.

Public API views disable session authentication where CSRF/session identity is not
needed. Inputs are length-bounded and API-path 404 noise is ignored. Redirect
sources are normalized around trailing slashes; preserve one canonical rule to
avoid duplicate/missed redirects.

## Admin authorization and endpoints

`IsSeoOrAdmin` permits authenticated `is_staff` or `is_seo_manager` users.
`SeoMixin` applies that policy. SEO managers must remain unable to reach the main
admin API.

Under `/api/admin/seo/`:

- `overview`: aggregate SEO health/counts.
- `pages`: searchable inventory with override/effective state.
- `meta`: get or update a page's metadata and create revisions.
- `revisions`: list or restore snapshots.
- `redirects`, `redirects/<id>`: create/list/update/delete validated redirects.
- `404s`: list or clear reported missing paths.
- `images`: list/update catalog image alt text.
- `scan`: list/run site/link checks and persist results.
- `settings`: read/update singleton settings.

`MetaSerializer` is the write contract. Validate custom JSON and page identity
before saving. `RedirectSerializer` requires an absolute internal source path,
prevents self-redirects, and restricts status codes. Consider redirect loops/chains
when extending validation.

The scan endpoint performs outbound requests and can become an SSRF or resource
exhaustion surface. Keep targets derived from controlled site pages/settings,
enforce timeouts and result limits, and do not allow arbitrary user-provided URLs
without explicit host/IP validation.

## Safe change checklist

1. Use `SeoSettings.load()` for singleton access.
2. Update DTO, snapshot, serializer, and restore logic together for new meta fields.
3. Keep blank override semantics and effective fallback behavior intact.
4. Exclude `noindex` and configured paths from sitemap output.
5. Validate custom schema as JSON and serialize it safely in Next.js.
6. Keep SEO-manager permissions isolated from financial/admin APIs.
7. Bound redirect/404/scan input and guard outbound scanning against SSRF.
8. Add SEO tests when changing this currently under-tested app, then run
   `./.venv/bin/python manage.py test seo --verbosity 2` plus the full suite.

