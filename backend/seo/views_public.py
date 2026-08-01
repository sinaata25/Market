"""ویوهای عمومی سئو: robots.txt، sitemap.xml، متای صفحات، ریدایرکت، ثبت ۴۰۴"""

import json

from django.db.models import F
from django.http import HttpResponse
from rest_framework.views import APIView

from common.responses import fail, ok

from .models import NotFoundLog, PageMeta, Redirect, SeoSettings
from .services import auto_schema, meta_dto


def robots_txt(request):
    s = SeoSettings.load()
    return HttpResponse(s.robots_txt, content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    from .services import build_sitemap

    s = SeoSettings.load()
    if not s.sitemap_enabled:
        return HttpResponse(status=404)
    return HttpResponse(
        build_sitemap(), content_type="application/xml; charset=utf-8"
    )


class PageMetaPublicView(APIView):
    """متای مؤثر یک صفحه برای رندر متاتگ‌ها در فرانت.

    مثال: /api/seo/meta?type=product&key=1
    """

    authentication_classes: list = []

    def get(self, request):
        page_type = request.query_params.get("type", "")
        key = request.query_params.get("key", "")
        if page_type not in ("product", "category", "static") or not key:
            return fail("پارامتر نامعتبر", 422)

        s = SeoSettings.load()
        meta = PageMeta.objects.filter(
            page_type=page_type, object_key=key
        ).first()
        data = meta_dto(meta, page_type, key)

        # اسکیما: سفارشی یا خودکار
        schema = None
        if meta and meta.schema_custom.strip():
            try:
                schema = json.loads(meta.schema_custom)
            except json.JSONDecodeError:
                schema = None
        if schema is None:
            schema = auto_schema(page_type, key, s)

        return ok(
            {
                "meta": data,
                "schema": schema,
                "site": {
                    "name": s.site_name,
                    "url": s.site_url,
                    "breadcrumbsEnabled": s.breadcrumbs_enabled,
                    "lazyloadEnabled": s.lazyload_enabled,
                    "orgSchemaEnabled": s.org_schema_enabled,
                    "hreflang": s.hreflang or [],
                },
            }
        )


class ResolveRedirectView(APIView):
    """بررسی ریدایرکت برای middleware فرانت — /api/seo/resolve?path=/old"""

    authentication_classes: list = []

    def get(self, request):
        path = request.query_params.get("path", "")
        if not path:
            return ok({"redirect": None})
        redirect = Redirect.objects.filter(
            from_path=path.rstrip("/") or "/", is_active=True
        ).first()
        if redirect is None:
            return ok({"redirect": None})
        Redirect.objects.filter(pk=redirect.pk).update(hits=F("hits") + 1)
        return ok(
            {
                "redirect": {
                    "to": redirect.to_path,
                    "status": redirect.status_code,
                }
            }
        )


class Track404View(APIView):
    """ثبت خطای ۴۰۴ از فرانت (بدون نیاز به ورود)"""

    authentication_classes: list = []

    def post(self, request):
        path = str(request.data.get("path", ""))[:300]
        referer = str(request.data.get("referer", ""))[:300]
        if not path or path.startswith("/api/"):
            return ok({"logged": False})
        log, created = NotFoundLog.objects.get_or_create(
            path=path, defaults={"referer": referer}
        )
        if not created:
            log.hits += 1
            if referer:
                log.referer = referer
            log.save(update_fields=["hits", "referer", "last_seen"])
        return ok({"logged": True})
