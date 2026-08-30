from django.urls import path

from . import views_admin, views_public

public_urlpatterns = [
    path("", views_public.PublicFooterView.as_view()),
]

admin_urlpatterns = [
    path("settings", views_admin.AdminFooterSettingsView.as_view()),
    path("settings/logo", views_admin.AdminFooterLogoView.as_view()),
    path("geocode/search", views_admin.AdminFooterGeocodeSearchView.as_view()),
    path("geocode/reverse", views_admin.AdminFooterGeocodeReverseView.as_view()),
    path("icons", views_admin.AdminFooterIconListView.as_view()),
    path("icons/<int:pk>", views_admin.AdminFooterIconDetailView.as_view()),
    path("icons/<int:pk>/image", views_admin.AdminFooterIconImageView.as_view()),
    path("sections", views_admin.AdminFooterSectionListView.as_view()),
    path("sections/<int:pk>", views_admin.AdminFooterSectionDetailView.as_view()),
    path("sections/<int:pk>/move", views_admin.AdminFooterSectionMoveView.as_view()),
    path("sections/<int:pk>/items", views_admin.AdminFooterItemListView.as_view()),
    path("items/<int:pk>", views_admin.AdminFooterItemDetailView.as_view()),
    path("items/<int:pk>/move", views_admin.AdminFooterItemMoveView.as_view()),
    path("items/<int:pk>/image", views_admin.AdminFooterItemImageView.as_view()),
]
