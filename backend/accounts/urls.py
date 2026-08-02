from django.urls import path

from . import views, views_profile

urlpatterns = [
    path("csrf", views.CsrfCookieView.as_view()),
    path("otp/send", views.SendOtpView.as_view()),
    path("otp/verify", views.VerifyOtpView.as_view()),
    path("me", views.MeView.as_view()),
    path("logout", views.LogoutView.as_view()),
    # پروفایل کاربر
    path("profile", views_profile.ProfileView.as_view()),
    path("addresses", views_profile.AddressListView.as_view()),
    path("addresses/<int:pk>", views_profile.AddressDetailView.as_view()),
    path("favorites", views_profile.FavoriteListView.as_view()),
    path("favorites/<int:pk>", views_profile.FavoriteCheckView.as_view()),
    path("my-reviews", views_profile.MyReviewsView.as_view()),
]
