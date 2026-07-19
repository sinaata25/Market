from django.contrib import admin

from .models import Category, Product, Review


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "emoji"]
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ["title"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "price", "old_price", "stock", "rating"]
    list_filter = ["category"]
    search_fields = ["title", "title_en"]
    list_editable = ["price", "old_price", "stock"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["product", "user", "rating", "created_at"]
    list_filter = ["rating"]
    search_fields = ["text"]
