from django.urls import path

from . import views_admin, views_public

# مسیرهای عمومی زیر /api/seo/
public_urlpatterns = [
    path("meta", views_public.PageMetaPublicView.as_view()),
    path("resolve", views_public.ResolveRedirectView.as_view()),
    path("404", views_public.Track404View.as_view()),
]

# مسیرهای پنل زیر /api/admin/seo/
admin_urlpatterns = [
    path("overview", views_admin.SeoOverviewView.as_view()),
    path("pages", views_admin.SeoPagesView.as_view()),
    path("meta", views_admin.SeoMetaView.as_view()),
    path("revisions", views_admin.MetaRevisionsView.as_view()),
    path("redirects", views_admin.RedirectListView.as_view()),
    path("redirects/<int:pk>", views_admin.RedirectDetailView.as_view()),
    path("404s", views_admin.NotFoundListView.as_view()),
    path("images", views_admin.ImageAltView.as_view()),
    path("scan", views_admin.ScanView.as_view()),
    path("settings", views_admin.SeoSettingsView.as_view()),
]
