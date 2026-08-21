from django.urls import path

from . import views

urlpatterns = [
    path("categories", views.CategoryListView.as_view()),
    path("brands", views.BrandListView.as_view()),
    path("products", views.ProductListView.as_view()),
    path("products/compare", views.ProductCompareView.as_view()),
    path("products/by-ids", views.ProductBulkView.as_view()),
    path("products/<int:pk>", views.ProductDetailView.as_view()),
    path("products/slug/<slug:slug>", views.ProductBySlugView.as_view()),
    path("products/<int:pk>/rating", views.ProductRatingView.as_view()),
    path("products/<int:pk>/comments", views.ProductCommentListCreateView.as_view()),
]
