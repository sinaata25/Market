from django.urls import path

from . import views_admin, views_public

public_urlpatterns = [
    path("sections", views_public.PublicHomepageSectionListView.as_view()),
]

admin_urlpatterns = [
    path("sections", views_admin.AdminHomepageSectionListView.as_view()),
    path("sections/<int:pk>", views_admin.AdminHomepageSectionDetailView.as_view()),
    path(
        "sections/<int:pk>/move",
        views_admin.AdminHomepageSectionMoveView.as_view(),
    ),
    path("banners", views_admin.AdminBannerListView.as_view()),
    path("banners/<int:pk>", views_admin.AdminBannerDetailView.as_view()),
    path(
        "banners/<int:pk>/image/<str:variant>",
        views_admin.AdminBannerImageView.as_view(),
    ),
]
