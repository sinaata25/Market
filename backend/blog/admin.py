from django.contrib import admin

from .models import BlogCategory, BlogPost, BlogTag


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(BlogTag)
class BlogTagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "category", "status", "published_at", "updated_at"]
    list_filter = ["status", "category", "tags", "published_at", "created_at"]
    search_fields = ["title", "excerpt", "content", "seo_title"]
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["author"]
    filter_horizontal = ["tags"]
    date_hierarchy = "published_at"
    list_select_related = ["author", "category"]
