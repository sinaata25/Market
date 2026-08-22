from django.urls import path

from .views import ProvinceCityListView, ProvinceListView


urlpatterns = [
    path("provinces", ProvinceListView.as_view()),
    path("provinces/<str:province_id>/cities", ProvinceCityListView.as_view()),
]
