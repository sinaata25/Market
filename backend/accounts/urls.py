from django.urls import path

from . import views

urlpatterns = [
    path("otp/send", views.SendOtpView.as_view()),
    path("otp/verify", views.VerifyOtpView.as_view()),
    path("me", views.MeView.as_view()),
    path("logout", views.LogoutView.as_view()),
]
