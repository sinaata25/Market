"""ویوهای پنل مدیریت سئو — دسترسی: staff یا مدیر سئو"""

import time

import requests as http
from rest_framework import serializers
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView

from catalog.models import ProductImage
from common.responses import fail, ok

from .models import (
    MetaRevision,
    NotFoundLog,
    PageMeta,
    Redirect,
    ScanResult,
    SeoSettings,
)
from .services import (
    all_pages,
    meta_dto,
    meta_to_snapshot,
    parse_schema_custom,
    settings_dto,
)


class IsSeoOrAdmin(BasePermission):
    """staff یا مدیر سئو"""

    message = "دسترسی سئو ندارید"

    def has_permission(self, request, view):
        u = request.user
        return bool(
            u and u.is_authenticated and (u.is_staff or u.is_seo_manager)
        )


class SeoMixin:
    permission_classes = [IsSeoOrAdmin]


# ─── نمای کلی ────────────────────────────────────────────────


class SeoOverviewView(SeoMixin, APIView):
    def get(self, request):
        pages = all_pages()
        metas = {
            (m.page_type, m.object_key): m for m in PageMeta.objects.all()
        }
        missing_meta = sum(
            1
            for p in pages
            if (p["pageType"], p["objectKey"]) not in metas
            or not metas[(p["pageType"], p["objectKey"])].meta_title
        )
        noindex = sum(1 for m in metas.values() if not m.robots_index)
        missing_alt = ProductImage.objects.filter(alt="").count()
        broken = ScanResult.objects.filter(ok=False).count()

        return ok(
            {
                "pagesTotal": len(pages),
                "missingMeta": missing_meta,
                "noindexPages": noindex,
                "redirects": Redirect.objects.filter(is_active=True).count(),
                "notFoundTotal": NotFoundLog.objects.count(),
                "notFoundTop": [
                    {"path": n.path, "hits": n.hits}
                    for n in NotFoundLog.objects.order_by("-hits")[:5]
                ],
                "missingAlt": missing_alt,
                "brokenLinks": broken,
                "lastScan": (
                    ScanResult.objects.order_by("-checked_at")
                    .values_list("checked_at", flat=True)
                    .first()
                ),
            }
        )


# ─── فهرست صفحات و متا ──────────────────────────────────────


class SeoPagesView(SeoMixin, APIView):
    def get(self, request):
        metas = {
            (m.page_type, m.object_key): m for m in PageMeta.objects.all()
        }
        rows = []
        for p in all_pages():
            meta = metas.get((p["pageType"], p["objectKey"]))
            rows.append(
                {
                    **p,
                    "hasMeta": bool(meta and meta.meta_title),
                    "titleLength": len(meta.meta_title) if meta else 0,
                    "descriptionLength": len(meta.meta_description)
                    if meta
                    else 0,
                    "focusKeyword": meta.focus_keyword if meta else "",
                    "robotsIndex": meta.robots_index if meta else True,
                    "slug": meta.slug if meta else "",
                }
            )
        return ok({"pages": rows})


class MetaSerializer(serializers.Serializer):
    metaTitle = serializers.CharField(
        max_length=200, allow_blank=True, default=""
    )
    metaDescription = serializers.CharField(allow_blank=True, default="")
    slug = serializers.CharField(max_length=200, allow_blank=True, default="")
    canonical = serializers.CharField(
        max_length=300, allow_blank=True, default=""
    )
    robotsIndex = serializers.BooleanField(default=True)
    robotsFollow = serializers.BooleanField(default=True)
    focusKeyword = serializers.CharField(
        max_length=100, allow_blank=True, default=""
    )
    ogTitle = serializers.CharField(max_length=200, allow_blank=True, default="")
    ogDescription = serializers.CharField(allow_blank=True, default="")
    ogImage = serializers.CharField(max_length=300, allow_blank=True, default="")
    twitterCard = serializers.ChoiceField(
        choices=["summary", "summary_large_image"],
        default="summary_large_image",
    )
    schemaType = serializers.ChoiceField(
        choices=["", "Product", "Article", "FAQPage", "WebPage", "CollectionPage"],
        allow_blank=True,
        default="",
    )
    schemaCustom = serializers.CharField(allow_blank=True, default="")


class SeoMetaView(SeoMixin, APIView):
    """خواندن/ذخیره متای یک صفحه — ?type=product&key=1"""

    def _params(self, request):
        page_type = request.query_params.get("type", "")
        key = request.query_params.get("key", "")
        if page_type not in ("product", "category", "static") or not key:
            return None, None
        return page_type, key

    def get(self, request):
        page_type, key = self._params(request)
        if page_type is None:
            return fail("پارامتر نامعتبر", 422)
        meta = PageMeta.objects.filter(
            page_type=page_type, object_key=key
        ).first()
        return ok({"meta": meta_dto(meta, page_type, key)})

    def put(self, request):
        page_type, key = self._params(request)
        if page_type is None:
            return fail("پارامتر نامعتبر", 422)

        ser = MetaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        valid, err = parse_schema_custom(d["schemaCustom"])
        if not valid:
            return fail(err, 422)

        meta, _created = PageMeta.objects.get_or_create(
            page_type=page_type, object_key=key
        )
        old_slug = meta.slug

        # اسنپ‌شات نسخه قبلی
        MetaRevision.objects.create(
            meta=meta, data=meta_to_snapshot(meta), user=request.user
        )

        meta.meta_title = d["metaTitle"]
        meta.meta_description = d["metaDescription"]
        meta.slug = d["slug"]
        meta.canonical = d["canonical"]
        meta.robots_index = d["robotsIndex"]
        meta.robots_follow = d["robotsFollow"]
        meta.focus_keyword = d["focusKeyword"]
        meta.og_title = d["ogTitle"]
        meta.og_description = d["ogDescription"]
        meta.og_image = d["ogImage"]
        meta.twitter_card = d["twitterCard"]
        meta.schema_type = d["schemaType"]
        meta.schema_custom = d["schemaCustom"]
        meta.save()

        # تغییر نامک محصول → ریدایرکت خودکار ۳۰۱
        auto_redirect = None
        if (
            page_type == "product"
            and old_slug
            and d["slug"]
            and old_slug != d["slug"]
        ):
            redirect, _ = Redirect.objects.update_or_create(
                from_path=f"/product/{old_slug}",
                defaults={
                    "to_path": f"/product/{d['slug']}",
                    "status_code": 301,
                    "is_active": True,
                    "note": "خودکار — تغییر نامک محصول",
                },
            )
            auto_redirect = {
                "from": redirect.from_path,
                "to": redirect.to_path,
            }

        return ok(
            {
                "meta": meta_dto(meta, page_type, key),
                "autoRedirect": auto_redirect,
            }
        )


class MetaRevisionsView(SeoMixin, APIView):
    """تاریخچه نسخه‌ها + بازگردانی — ?type=&key="""

    def get(self, request):
        page_type = request.query_params.get("type", "")
        key = request.query_params.get("key", "")
        meta = PageMeta.objects.filter(
            page_type=page_type, object_key=key
        ).first()
        if meta is None:
            return ok({"revisions": []})
        return ok(
            {
                "revisions": [
                    {
                        "id": r.id,
                        "createdAt": r.created_at.isoformat(),
                        "user": (r.user.name or r.user.phone) if r.user else "—",
                        "data": r.data,
                    }
                    for r in meta.revisions.all()[:20]
                ]
            }
        )

    def post(self, request):
        revision_id = request.data.get("revisionId")
        revision = MetaRevision.objects.filter(pk=revision_id).first()
        if revision is None:
            return fail("نسخه یافت نشد", 404)
        meta = revision.meta
        # قبل از بازگردانی، وضعیت فعلی هم ثبت شود
        MetaRevision.objects.create(
            meta=meta, data=meta_to_snapshot(meta), user=request.user
        )
        for field, value in revision.data.items():
            setattr(meta, field, value)
        meta.save()
        return ok(
            {"meta": meta_dto(meta, meta.page_type, meta.object_key)}
        )


# ─── ریدایرکت‌ها ─────────────────────────────────────────────


class RedirectSerializer(serializers.Serializer):
    fromPath = serializers.CharField(max_length=300)
    toPath = serializers.CharField(max_length=300)
    statusCode = serializers.ChoiceField(choices=[301, 302], default=301)
    isActive = serializers.BooleanField(default=True)
    note = serializers.CharField(max_length=200, allow_blank=True, default="")

    def validate_fromPath(self, v):
        v = v.strip()
        if not v.startswith("/"):
            raise serializers.ValidationError("مسیر باید با / شروع شود")
        return v.rstrip("/") or "/"

    def validate(self, data):
        if data["fromPath"] == data["toPath"].rstrip("/"):
            raise serializers.ValidationError("مبدأ و مقصد یکسان است")
        return data


def redirect_dto(r: Redirect) -> dict:
    return {
        "id": r.id,
        "fromPath": r.from_path,
        "toPath": r.to_path,
        "statusCode": r.status_code,
        "isActive": r.is_active,
        "note": r.note,
        "hits": r.hits,
        "createdAt": r.created_at.isoformat(),
    }


class RedirectListView(SeoMixin, APIView):
    def get(self, request):
        return ok(
            {"redirects": [redirect_dto(r) for r in Redirect.objects.all()]}
        )

    def post(self, request):
        ser = RedirectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        if Redirect.objects.filter(from_path=d["fromPath"]).exists():
            return fail("برای این مسیر قبلاً ریدایرکت ثبت شده است", 409)
        r = Redirect.objects.create(
            from_path=d["fromPath"],
            to_path=d["toPath"],
            status_code=d["statusCode"],
            is_active=d["isActive"],
            note=d["note"],
        )
        return ok({"redirect": redirect_dto(r)}, status=201)


class RedirectDetailView(SeoMixin, APIView):
    def patch(self, request, pk: int):
        r = Redirect.objects.filter(pk=pk).first()
        if r is None:
            return fail("ریدایرکت یافت نشد", 404)
        ser = RedirectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        r.from_path = d["fromPath"]
        r.to_path = d["toPath"]
        r.status_code = d["statusCode"]
        r.is_active = d["isActive"]
        r.note = d["note"]
        r.save()
        return ok({"redirect": redirect_dto(r)})

    def delete(self, request, pk: int):
        deleted, _ = Redirect.objects.filter(pk=pk).delete()
        if not deleted:
            return fail("ریدایرکت یافت نشد", 404)
        return ok({"deleted": True})


# ─── گزارش ۴۰۴ ───────────────────────────────────────────────


class NotFoundListView(SeoMixin, APIView):
    def get(self, request):
        return ok(
            {
                "logs": [
                    {
                        "id": n.id,
                        "path": n.path,
                        "hits": n.hits,
                        "referer": n.referer,
                        "lastSeen": n.last_seen.isoformat(),
                    }
                    for n in NotFoundLog.objects.all()[:100]
                ]
            }
        )

    def delete(self, request):
        NotFoundLog.objects.all().delete()
        return ok({"cleared": True})


# ─── Alt تصاویر ─────────────────────────────────────────────


class ImageAltView(SeoMixin, APIView):
    def get(self, request):
        images = ProductImage.objects.select_related("product").order_by(
            "product_id", "order"
        )
        return ok(
            {
                "images": [
                    {
                        "id": img.id,
                        "url": img.image.url,
                        "alt": img.alt,
                        "productId": img.product_id,
                        "productTitle": img.product.title,
                    }
                    for img in images
                ]
            }
        )

    def patch(self, request):
        """ویرایش گروهی: [{id, alt}, ...]"""
        items = request.data.get("items", [])
        if not isinstance(items, list) or not items:
            return fail("لیست تغییرات خالی است", 422)
        updated = 0
        for item in items:
            img = ProductImage.objects.filter(pk=item.get("id")).first()
            if img is not None:
                img.alt = str(item.get("alt", ""))[:255]
                img.save(update_fields=["alt"])
                updated += 1
        return ok({"updated": updated})


# ─── اسکن سرعت و لینک شکسته ─────────────────────────────────


class ScanView(SeoMixin, APIView):
    def get(self, request):
        return ok(
            {
                "results": [
                    {
                        "url": r.url,
                        "kind": r.kind,
                        "statusCode": r.status_code,
                        "responseMs": r.response_ms,
                        "ok": r.ok,
                        "checkedAt": r.checked_at.isoformat(),
                    }
                    for r in ScanResult.objects.all()
                ]
            }
        )

    def post(self, request):
        """اسکن همه صفحات سایت + تصاویر محصولات (همزمان — برای سایت کوچک)"""
        s = SeoSettings.load()
        ScanResult.objects.all().delete()

        checked = 0
        for page in all_pages():
            url = f"{s.site_url}{page['path']}"
            code, ms = self._check(url)
            ScanResult.objects.create(
                url=url,
                kind="page",
                status_code=code,
                response_ms=ms,
                ok=code is not None and code < 400,
            )
            checked += 1

        for img in ProductImage.objects.all()[:50]:
            url = f"{s.site_url}{img.image.url}"
            code, ms = self._check(url)
            ScanResult.objects.create(
                url=url,
                kind="link",
                status_code=code,
                response_ms=ms,
                ok=code is not None and code < 400,
            )
            checked += 1

        return ok({"checked": checked})

    @staticmethod
    def _check(url: str):
        try:
            start = time.monotonic()
            r = http.get(url, timeout=15)
            ms = int((time.monotonic() - start) * 1000)
            return r.status_code, ms
        except http.RequestException:
            return None, None


# ─── تنظیمات ─────────────────────────────────────────────────


class SeoSettingsView(SeoMixin, APIView):
    def get(self, request):
        return ok({"settings": settings_dto(SeoSettings.load())})

    def put(self, request):
        s = SeoSettings.load()
        d = request.data
        s.site_name = str(d.get("siteName", s.site_name))[:100]
        s.site_url = str(d.get("siteUrl", s.site_url)).rstrip("/")[:200]
        s.default_meta_description = str(
            d.get("defaultMetaDescription", s.default_meta_description)
        )
        s.robots_txt = str(d.get("robotsTxt", s.robots_txt))
        s.sitemap_enabled = bool(d.get("sitemapEnabled", s.sitemap_enabled))
        s.sitemap_include_products = bool(
            d.get("sitemapIncludeProducts", s.sitemap_include_products)
        )
        s.sitemap_include_categories = bool(
            d.get("sitemapIncludeCategories", s.sitemap_include_categories)
        )
        s.sitemap_include_static = bool(
            d.get("sitemapIncludeStatic", s.sitemap_include_static)
        )
        s.sitemap_excluded_paths = str(
            d.get("sitemapExcludedPaths", s.sitemap_excluded_paths)
        )
        s.breadcrumbs_enabled = bool(
            d.get("breadcrumbsEnabled", s.breadcrumbs_enabled)
        )
        s.lazyload_enabled = bool(d.get("lazyloadEnabled", s.lazyload_enabled))
        s.image_compression_enabled = bool(
            d.get("imageCompressionEnabled", s.image_compression_enabled)
        )
        s.org_schema_enabled = bool(
            d.get("orgSchemaEnabled", s.org_schema_enabled)
        )
        hreflang = d.get("hreflang", s.hreflang)
        if isinstance(hreflang, list):
            s.hreflang = [
                {
                    "lang": str(h.get("lang", ""))[:20],
                    "url": str(h.get("url", ""))[:200],
                }
                for h in hreflang
                if isinstance(h, dict) and h.get("lang") and h.get("url")
            ]
        s.save()
        return ok({"settings": settings_dto(s)})
