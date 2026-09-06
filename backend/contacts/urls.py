from django.urls import path
from . import views_admin, views_public

public_urlpatterns = [path("floating-contact-buttons", views_public.PublicFloatingContactButtonsView.as_view())]
admin_urlpatterns = [
    path("floating-contact-buttons", views_admin.AdminButtonListView.as_view()),
    path("floating-contact-buttons/<int:pk>", views_admin.AdminButtonDetailView.as_view()),
    path("floating-contact-buttons/<int:pk>/move", views_admin.AdminButtonMoveView.as_view()),
    path("floating-contact-buttons/<int:pk>/icon", views_admin.AdminButtonIconView.as_view()),
]
