"""منطق مشترک سئو: فهرست صفحات سایت، متای مؤثر هر صفحه، سایت‌مپ"""

import json

from catalog.models import Category, Product
from catalog.category_tree import visible_category_ids
from common.search import filter_by_search, normalize_search_text

from .models import PageMeta, SeoSettings

# صفحات ثابت سایت
STATIC_PAGES = [
    {"key": "/", "title": "صفحه اصلی"},
    {"key": "/products", "title": "همه محصولات"},
    {"key": "/blog", "title": "وبلاگ کشاورزی"},
    {"key": "/incredible", "title": "شگفت‌انگیزها"},
    {"key": "/best-sellers", "title": "پرفروش‌ترین‌ها"},
    {"key": "/support", "title": "سوالی دارید؟"},
    {"key": "/login", "title": "ورود | ثبت‌نام"},
    {"key": "/cart", "title": "سبد خرید"},
]


def page_inventory(
    *, search: str = "", page_type: str = "", page: int = 1, per_page: int = 20
) -> tuple[list[dict], int]:
    """Return one database-backed slice of the SEO-manageable page inventory."""

    normalized_search = normalize_search_text(search)
    tokens = normalized_search.split(" ") if normalized_search else []
    sources: list[tuple[int, object]] = []

    if page_type in ("", "static"):
        static_rows = [
            {
                "pageType": "static",
                "objectKey": item["key"],
                "title": item["title"],
                "path": item["key"],
            }
            for item in STATIC_PAGES
            if not tokens
            or all(
                token
                in normalize_search_text(f'{item["title"]} {item["key"]}')
                for token in tokens
            )
        ]
        sources.append((len(static_rows), static_rows))

    if page_type in ("", "category"):
        categories = Category.objects.only("id", "slug", "title").order_by("id")
        if normalized_search:
            categories = filter_by_search(
                categories, normalized_search, fields=("title", "slug")
            )
        sources.append((categories.count(), categories))

    if page_type in ("", "product"):
        products = Product.objects.only("id", "title", "created_at").order_by(
            "-created_at", "-id"
        )
        if normalized_search:
            products = filter_by_search(
                products,
                normalized_search,
                fields=("title", "title_en"),
                include_pk=True,
            )
        sources.append((products.count(), products))

    total = sum(count for count, _source in sources)
    start = (page - 1) * per_page
    remaining = per_page
    rows: list[dict] = []

    for count, source in sources:
        if remaining <= 0:
            break
        if start >= count:
            start -= count
            continue
        take = min(remaining, count - start)
        selected = source[start : start + take]
        if isinstance(source, list):
            rows.extend(selected)
        elif source.model is Category:
            rows.extend(
                {
                    "pageType": "category",
                    "objectKey": category.slug,
                    "title": category.title,
                    "path": f"/category/{category.slug}",
                }
                for category in selected
            )
        else:
            rows.extend(
                {
                    "pageType": "product",
                    "objectKey": str(product.id),
                    "title": product.title,
                    "path": f"/product/{product.id}",
                }
                for product in selected
            )
        remaining -= take
        start = 0

    return rows, total


def all_pages() -> list[dict]:
    """فهرست همه‌ی صفحات قابل مدیریت سئو"""
    pages = [
        {
            "pageType": "static",
            "objectKey": p["key"],
            "title": p["title"],
            "path": p["key"],
        }
        for p in STATIC_PAGES
    ]
    for c in Category.objects.all():
        pages.append(
            {
                "pageType": "category",
                "objectKey": c.slug,
                "title": c.title,
                "path": f"/category/{c.slug}",
            }
        )
    for p in Product.objects.select_related("category"):
        pages.append(
            {
                "pageType": "product",
                "objectKey": str(p.id),
                "title": p.title,
                "path": f"/product/{p.id}",
            }
        )
    return pages


def page_path(page_type: str, object_key: str) -> str | None:
    """مسیر واقعی صفحه از نوع/کلید"""
    if page_type == "static":
        return object_key
    if page_type == "category":
        c = Category.objects.filter(slug=object_key).first()
        return f"/category/{c.slug}" if c else None
    if page_type == "product":
        return f"/product/{object_key}"
    return None


def default_meta_for(page_type: str, object_key: str) -> dict:
    """متای پیش‌فرض (وقتی مدیر سئو چیزی تنظیم نکرده)"""
    s = SeoSettings.load()
    if page_type == "product":
        p = (
            Product.objects.select_related("category", "brand")
            .prefetch_related("images")
            .filter(pk=object_key)
            .first()
        )
        if p:
            first_image = next(iter(p.images.all()), None)
            return {
                "title": f"خرید {p.title} | {s.site_name}",
                "description": (p.description or "")[:160]
                or f"خرید اینترنتی {p.title} با بهترین قیمت و ضمانت اصالت کالا از {s.site_name}.",
                "image": first_image.image.url if first_image else "",
            }
    if page_type == "category":
        c = Category.objects.filter(slug=object_key).first()
        if c:
            return {
                "title": f"خرید {c.title} | قیمت انواع {c.title} | {s.site_name}",
                "description": f"خرید اینترنتی انواع {c.title} با بهترین قیمت، ضمانت اصالت کالا و ارسال سریع از فروشگاه {s.site_name}.",
                "image": "",
            }
    static_titles = {p["key"]: p["title"] for p in STATIC_PAGES}
    return {
        "title": f"{static_titles.get(object_key, 'صفحه')} | {s.site_name}",
        "description": s.default_meta_description
        or f"فروشگاه اینترنتی {s.site_name}؛ ابزارآلات و ادوات کشاورزی با ضمانت اصالت کالا.",
        "image": "",
    }


def meta_dto(meta: PageMeta | None, page_type: str, object_key: str) -> dict:
    """متای مؤثر صفحه: تنظیم‌شده یا پیش‌فرض — خروجی برای پنل و فرانت"""
    defaults = default_meta_for(page_type, object_key)
    return {
        "pageType": page_type,
        "objectKey": object_key,
        "path": page_path(page_type, object_key),
        "metaTitle": meta.meta_title if meta else "",
        "metaDescription": meta.meta_description if meta else "",
        "slug": meta.slug if meta else "",
        "canonical": meta.canonical if meta else "",
        "robotsIndex": meta.robots_index if meta else True,
        "robotsFollow": meta.robots_follow if meta else True,
        "focusKeyword": meta.focus_keyword if meta else "",
        "ogTitle": meta.og_title if meta else "",
        "ogDescription": meta.og_description if meta else "",
        "ogImage": meta.og_image if meta else "",
        "twitterCard": meta.twitter_card if meta else "summary_large_image",
        "schemaType": meta.schema_type if meta else "",
        "schemaCustom": meta.schema_custom if meta else "",
        "defaults": defaults,
        "effectiveTitle": (meta.meta_title if meta else "") or defaults["title"],
        "effectiveDescription": (meta.meta_description if meta else "")
        or defaults["description"],
        "effectiveImage": (meta.og_image if meta else "") or defaults["image"],
    }


def meta_to_snapshot(meta: PageMeta) -> dict:
    """اسنپ‌شات برای تاریخچه نسخه‌ها"""
    return {
        "meta_title": meta.meta_title,
        "meta_description": meta.meta_description,
        "slug": meta.slug,
        "canonical": meta.canonical,
        "robots_index": meta.robots_index,
        "robots_follow": meta.robots_follow,
        "focus_keyword": meta.focus_keyword,
        "og_title": meta.og_title,
        "og_description": meta.og_description,
        "og_image": meta.og_image,
        "twitter_card": meta.twitter_card,
        "schema_type": meta.schema_type,
        "schema_custom": meta.schema_custom,
    }


def build_sitemap() -> str:
    """ساخت XML سایت‌مپ بر اساس تنظیمات و صفحات noindex"""
    s = SeoSettings.load()
    excluded = {
        line.strip()
        for line in (s.sitemap_excluded_paths or "").splitlines()
        if line.strip()
    }
    noindex = {
        (m.page_type, m.object_key)
        for m in PageMeta.objects.filter(robots_index=False)
    }
    active_product_keys = {
        str(pk) for pk in Product.objects.filter(is_active=True).values_list("pk", flat=True)
    }
    active_category_keys = set(
        Category.objects.filter(id__in=visible_category_ids()).values_list(
            "slug", flat=True
        )
    )

    urls: list[str] = []
    for page in all_pages():
        if (
            page["pageType"] == "product"
            and page["objectKey"] not in active_product_keys
        ):
            continue
        if (
            page["pageType"] == "category"
            and page["objectKey"] not in active_category_keys
        ):
            continue
        if page["pageType"] == "static" and not s.sitemap_include_static:
            continue
        if page["pageType"] == "category" and not s.sitemap_include_categories:
            continue
        if page["pageType"] == "product" and not s.sitemap_include_products:
            continue
        if page["path"] in excluded:
            continue
        if (page["pageType"], page["objectKey"]) in noindex:
            continue
        urls.append(f"  <url><loc>{s.site_url}{page['path']}</loc></url>")

    # نوشته‌های وبلاگ منبع متای مستقل دارند و فقط پس از انتشار وارد سایت‌مپ می‌شوند.
    from blog.models import BlogPost

    for post in BlogPost.objects.published().only("slug", "updated_at"):
        path = f"/blog/{post.slug}"
        if path in excluded:
            continue
        urls.append(
            f"  <url><loc>{s.site_url}{path}</loc>"
            f"<lastmod>{post.updated_at.date().isoformat()}</lastmod></url>"
        )

    body = "\n".join(urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>"
    )


def settings_dto(s: SeoSettings) -> dict:
    return {
        "siteName": s.site_name,
        "siteUrl": s.site_url,
        "defaultMetaDescription": s.default_meta_description,
        "robotsTxt": s.robots_txt,
        "sitemapEnabled": s.sitemap_enabled,
        "sitemapIncludeProducts": s.sitemap_include_products,
        "sitemapIncludeCategories": s.sitemap_include_categories,
        "sitemapIncludeStatic": s.sitemap_include_static,
        "sitemapExcludedPaths": s.sitemap_excluded_paths,
        "breadcrumbsEnabled": s.breadcrumbs_enabled,
        "lazyloadEnabled": s.lazyload_enabled,
        "imageCompressionEnabled": s.image_compression_enabled,
        "orgSchemaEnabled": s.org_schema_enabled,
        "hreflang": s.hreflang or [],
    }


def auto_schema(page_type: str, object_key: str, s: SeoSettings) -> dict | None:
    """اسکیمای خودکار JSON-LD بر اساس نوع صفحه"""
    if page_type == "product":
        p = (
            Product.objects.select_related("category", "brand")
            .prefetch_related("images")
            .filter(pk=object_key)
            .first()
        )
        if not p:
            return None
        first_image = next(iter(p.images.all()), None)
        return {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": p.title,
            "image": (
                [f"{s.site_url}{first_image.image.url}"] if first_image else []
            ),
            "description": (p.description or "")[:300],
            "category": p.category.title,
            "brand": (
                {"@type": "Brand", "name": p.brand.name}
                if p.brand_id
                else None
            ),
            "aggregateRating": (
                {
                    "@type": "AggregateRating",
                    "ratingValue": p.rating,
                    "reviewCount": p.rating_count,
                }
                if p.rating_count
                else None
            ),
            "offers": {
                "@type": "Offer",
                "priceCurrency": "IRT",
                "price": p.price,
                "availability": (
                    "https://schema.org/InStock"
                    if p.stock > 0
                    else "https://schema.org/OutOfStock"
                ),
                "url": f"{s.site_url}/product/{p.id}",
            },
        }
    if page_type == "category":
        c = Category.objects.filter(slug=object_key).first()
        if not c:
            return None
        return {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": c.title,
            "url": f"{s.site_url}/category/{c.slug}",
        }
    return None


def parse_schema_custom(value: str) -> tuple[bool, str]:
    """اعتبارسنجی JSON سفارشی"""
    if not value.strip():
        return True, ""
    try:
        json.loads(value)
        return True, ""
    except json.JSONDecodeError as e:
        return False, f"JSON نامعتبر است: {e.msg}"
