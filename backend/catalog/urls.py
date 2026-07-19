from django.urls import path

from . import views

urlpatterns = [
    path("categories", views.CategoryListView.as_view()),
    path("products", views.ProductListView.as_view()),
    path("products/<int:pk>", views.ProductDetailView.as_view()),
    path("products/<int:pk>/reviews", views.ReviewListCreateView.as_view()),
]
