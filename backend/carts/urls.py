from django.urls import path

from . import views

urlpatterns = [
    path("cart", views.CartView.as_view()),
    path("cart/items", views.CartItemsView.as_view()),
    path("cart/items/<int:pk>", views.CartItemDetailView.as_view()),
]
