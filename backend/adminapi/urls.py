from django.urls import path

from . import views, views_managers, views_seo_admins, views_users

urlpatterns = [
    path("stats", views.StatsView.as_view()),
    path("orders", views.AdminOrderListView.as_view()),
    path("orders/<int:pk>", views.AdminOrderDetailView.as_view()),
    path("categories", views.AdminCategoryListView.as_view()),
    path("categories/<int:pk>", views.AdminCategoryDetailView.as_view()),
    path("categories/<int:pk>/icon", views.AdminCategoryIconView.as_view()),
    path("brands", views.AdminBrandListView.as_view()),
    path("brands/<int:pk>", views.AdminBrandDetailView.as_view()),
    path("brands/<int:pk>/logo", views.AdminBrandLogoView.as_view()),
    path(
        "brands/<int:pk>/price-adjustment",
        views.AdminBrandPriceAdjustmentView.as_view(),
    ),
    path("specifications", views.AdminSpecificationKeyListView.as_view()),
    path(
        "specifications/<int:pk>", views.AdminSpecificationKeyDetailView.as_view()
    ),
    path("products", views.AdminProductListView.as_view()),
    path("products/<int:pk>", views.AdminProductDetailView.as_view()),
    path(
        "products/<int:pk>/visibility",
        views.AdminProductVisibilityView.as_view(),
    ),
    path(
        "products/<int:pk>/best-seller",
        views.AdminProductBestSellerView.as_view(),
    ),
    path(
        "products/<int:pk>/incredible",
        views.AdminProductIncredibleView.as_view(),
    ),
    path("products/<int:pk>/image", views.AdminProductImageView.as_view()),
    path(
        "products/<int:pk>/images/<int:image_id>",
        views.AdminProductImageDetailView.as_view(),
    ),
    # مدیریت کاربران — دامنه‌ی دید هر نقش را accounts.selectors تعیین می‌کند
    path("users", views_users.AdminUserListView.as_view()),
    path("users/<int:pk>", views_users.AdminUserDetailView.as_view()),
    # مدیریت «مدیر اجرایی» و دسترسی سئوی او — فقط سوپریوزر
    path("managers", views_managers.ManagerListView.as_view()),
    path("managers/<int:pk>", views_managers.ManagerDetailView.as_view()),
    # مدیریت «مدیر سئو» — سوپریوزر یا مدیر اجرایی دارای دسترسی سئو
    path("seo-admins", views_seo_admins.SeoAdminListView.as_view()),
    path(
        "seo-admins/<int:pk>", views_seo_admins.SeoAdminDetailView.as_view()
    ),
    path("comments", views.AdminCommentListView.as_view()),
    path("comments/<int:pk>", views.AdminCommentDetailView.as_view()),
    path(
        "comments/<int:pk>/responses",
        views.AdminCommentResponseView.as_view(),
    ),
]
