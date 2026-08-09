from django.urls import path

from . import views

urlpatterns = [
    path("stats", views.StatsView.as_view()),
    path("orders", views.AdminOrderListView.as_view()),
    path("orders/<int:pk>", views.AdminOrderDetailView.as_view()),
    path("categories", views.AdminCategoryListView.as_view()),
    path("categories/<int:pk>", views.AdminCategoryDetailView.as_view()),
    path("categories/<int:pk>/icon", views.AdminCategoryIconView.as_view()),
    path("products", views.AdminProductListView.as_view()),
    path("products/<int:pk>", views.AdminProductDetailView.as_view()),
    path(
        "products/<int:pk>/visibility",
        views.AdminProductVisibilityView.as_view(),
    ),
    path("products/<int:pk>/image", views.AdminProductImageView.as_view()),
    path(
        "products/<int:pk>/images/<int:image_id>",
        views.AdminProductImageDetailView.as_view(),
    ),
    path("users", views.AdminUserListView.as_view()),
    path("reviews", views.AdminReviewListView.as_view()),
    path("reviews/<int:pk>", views.AdminReviewDetailView.as_view()),
]
