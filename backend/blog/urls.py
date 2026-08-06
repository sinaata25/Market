from django.urls import path

from . import views, views_admin

public_urlpatterns = [
    path("posts", views.BlogPostListView.as_view(), name="post-list"),
    path("posts/<str:slug>", views.BlogPostDetailView.as_view(), name="post-detail"),
    path("categories", views.BlogCategoryListView.as_view(), name="category-list"),
    path("tags", views.BlogTagListView.as_view(), name="tag-list"),
]

admin_urlpatterns = [
    path("posts", views_admin.AdminBlogPostListView.as_view(), name="post-list"),
    path("posts/<int:pk>", views_admin.AdminBlogPostDetailView.as_view(), name="post-detail"),
    path("posts/<int:pk>/publish", views_admin.AdminBlogPublishView.as_view(), name="post-publish"),
    path("posts/<int:pk>/unpublish", views_admin.AdminBlogUnpublishView.as_view(), name="post-unpublish"),
    path("posts/<int:pk>/featured-image", views_admin.AdminBlogFeaturedImageView.as_view(), name="post-featured-image"),
    path("categories", views_admin.AdminBlogCategoryListView.as_view(), name="category-list"),
    path("categories/<int:pk>", views_admin.AdminBlogCategoryDetailView.as_view(), name="category-detail"),
    path("tags", views_admin.AdminBlogTagListView.as_view(), name="tag-list"),
    path("tags/<int:pk>", views_admin.AdminBlogTagDetailView.as_view(), name="tag-detail"),
]
