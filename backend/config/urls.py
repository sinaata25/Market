"""مسیرهای اصلی بک‌اند فروشگاه"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from seo import views_public as seo_public
from seo.urls import admin_urlpatterns as seo_admin_urls
from seo.urls import public_urlpatterns as seo_public_urls
from blog.urls import admin_urlpatterns as blog_admin_urls
from blog.urls import public_urlpatterns as blog_public_urls
from staticpages.urls import admin_urlpatterns as staticpages_admin_urls
from staticpages.urls import public_urlpatterns as staticpages_public_urls
from homepage.urls import admin_urlpatterns as homepage_admin_urls
from homepage.urls import public_urlpatterns as homepage_public_urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
    path(
        "api/redoc/", SpectacularRedocView.as_view(url_name="api-schema"), name="redoc"
    ),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("catalog.urls")),
    path("api/", include("carts.urls")),
    path("api/", include("orders.urls")),
    path("api/admin/", include("adminapi.urls")),
    path("api/admin/blog/", include((blog_admin_urls, "blog-admin"))),
    path("api/admin/seo/", include((seo_admin_urls, "seo-admin"))),
    path(
        "api/admin/content/",
        include((staticpages_admin_urls, "staticpages-admin")),
    ),
    path("api/admin/home/", include((homepage_admin_urls, "homepage-admin"))),
    path("api/blog/", include((blog_public_urls, "blog-public"))),
    path("api/seo/", include((seo_public_urls, "seo-public"))),
    path(
        "api/content/",
        include((staticpages_public_urls, "staticpages-public")),
    ),
    path("api/home/", include((homepage_public_urls, "homepage-public"))),
    # فایل‌های سئو در ریشه (از طریق rewrite فرانت هم در دسترس‌اند)
    path("robots.txt", seo_public.robots_txt),
    path("sitemap.xml", seo_public.sitemap_xml),
]

# سروکردن تصاویر آپلودی در حالت توسعه
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
