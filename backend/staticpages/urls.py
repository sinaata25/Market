from django.urls import path

from . import views_admin, views_public


public_urlpatterns = [
    path("pages", views_public.PublicStaticPageListView.as_view()),
    path(
        "pages/visibility",
        views_public.PublicStaticPageVisibilityView.as_view(),
    ),
    path("pages/<str:key>", views_public.PublicStaticPageDetailView.as_view()),
]

admin_urlpatterns = [
    path("pages", views_admin.AdminStaticPageListView.as_view()),
    path("pages/<str:key>", views_admin.AdminStaticPageDetailView.as_view()),
]
