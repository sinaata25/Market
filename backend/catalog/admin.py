from django import forms
from django.contrib import admin
from django.db import models
from django.utils.html import format_html

from .icon_files import schedule_category_icon_delete
from .models import Category, Product, ProductImage, Review


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["icon_preview", "title", "slug"]
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ["icon_preview"]
    search_fields = ["title"]
    formfield_overrides = {
        models.FileField: {
            "widget": forms.ClearableFileInput(
                attrs={"accept": ".png,.svg,image/png,image/svg+xml"}
            )
        }
    }

    @admin.display(description="پیش‌نمایش آیکن")
    def icon_preview(self, obj):
        if not obj or not obj.icon:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="width: 40px; height: 40px; '
            'object-fit: contain;" />',
            obj.icon.url,
        )

    def save_model(self, request, obj, form, change):
        old_name = ""
        old_storage = None
        if change:
            previous = Category.objects.filter(pk=obj.pk).first()
            if previous and previous.icon:
                old_name = previous.icon.name
                old_storage = previous.icon.storage

        super().save_model(request, obj, form, change)
        new_name = obj.icon.name if obj.icon else ""
        if old_name and old_name != new_name:
            schedule_category_icon_delete(
                old_name,
                old_storage,
                using=obj._state.db or "default",
            )

    def delete_model(self, request, obj):
        name = obj.icon.name if obj.icon else ""
        storage = obj.icon.storage if obj.icon else None
        using = obj._state.db or "default"
        super().delete_model(request, obj)
        if name:
            schedule_category_icon_delete(name, storage, using=using)

    def delete_queryset(self, request, queryset):
        icons = [
            (category.icon.name, category.icon.storage, category._state.db or "default")
            for category in queryset
            if category.icon
        ]
        super().delete_queryset(request, queryset)
        for name, storage, using in icons:
            schedule_category_icon_delete(name, storage, using=using)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "price", "old_price", "stock", "rating"]
    list_filter = ["category"]
    search_fields = ["title", "title_en"]
    list_editable = ["price", "old_price", "stock"]
    inlines = [ProductImageInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["product", "user", "rating", "created_at"]
    list_filter = ["rating"]
    search_fields = ["text"]
