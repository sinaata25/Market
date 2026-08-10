from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import format_html

from .feedback import recompute_product_rating
from .brand_files import schedule_brand_logo_delete
from .icon_files import schedule_category_icon_delete
from .models import (
    Brand,
    Category,
    Product,
    ProductComment,
    ProductImage,
    ProductRating,
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class CategoryAdminForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = "__all__"

    def clean_parents(self):
        parents = self.cleaned_data.get("parents")
        category = self.instance
        if not category.pk or parents is None:
            return parents

        parent_ids = set(parents.values_list("id", flat=True))
        if category.pk in parent_ids:
            raise ValidationError("یک دسته‌بندی نمی‌تواند والد خودش باشد")

        descendants = {category.pk}
        frontier = {category.pk}
        while frontier:
            child_ids = set(
                Category.objects.filter(parents__id__in=frontier)
                .exclude(id__in=descendants)
                .distinct()
                .values_list("id", flat=True)
            )
            descendants.update(child_ids)
            frontier = child_ids
        if parent_ids & descendants:
            raise ValidationError("این رابطه باعث ایجاد چرخه در دسته‌بندی‌ها می‌شود")
        return parents


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryAdminForm
    list_display = ["icon_preview", "title", "slug", "is_active"]
    list_editable = ["is_active"]
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ["icon_preview"]
    search_fields = ["title"]
    filter_horizontal = ["parents"]
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

    def has_delete_permission(self, request, obj=None):
        allowed = super().has_delete_permission(request, obj)
        if not allowed or obj is None:
            return allowed
        return not (
            obj.products.exists()
            or obj.categorized_products.exists()
            or obj.children.exists()
        )

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["logo_preview", "name", "slug", "is_active", "product_count"]
    list_editable = ["is_active"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["logo_preview"]
    search_fields = ["name", "slug"]
    formfield_overrides = {
        models.FileField: {
            "widget": forms.ClearableFileInput(
                attrs={"accept": ".png,.svg,image/png,image/svg+xml"}
            )
        }
    }

    @admin.display(description="پیش‌نمایش نشان")
    def logo_preview(self, obj):
        if not obj or not obj.logo:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="width: 48px; height: 48px; '
            'object-fit: contain;" />',
            obj.logo.url,
        )

    @admin.display(description="تعداد محصولات")
    def product_count(self, obj):
        return obj.products.count()

    def save_model(self, request, obj, form, change):
        old_name = ""
        old_storage = None
        if change:
            previous = Brand.objects.filter(pk=obj.pk).first()
            if previous and previous.logo:
                old_name = previous.logo.name
                old_storage = previous.logo.storage

        super().save_model(request, obj, form, change)
        new_name = obj.logo.name if obj.logo else ""
        if old_name and old_name != new_name:
            schedule_brand_logo_delete(
                old_name,
                old_storage,
                using=obj._state.db or "default",
            )

    def delete_model(self, request, obj):
        name = obj.logo.name if obj.logo else ""
        storage = obj.logo.storage if obj.logo else None
        using = obj._state.db or "default"
        super().delete_model(request, obj)
        if name:
            schedule_brand_logo_delete(name, storage, using=using)

    def has_delete_permission(self, request, obj=None):
        allowed = super().has_delete_permission(request, obj)
        if not allowed or obj is None:
            return allowed
        return not obj.products.exists()

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "brand",
        "category",
        "price",
        "old_price",
        "stock",
        "rating",
        "is_active",
    ]
    list_filter = ["brand", "categories"]
    search_fields = ["title", "title_en"]
    list_editable = ["price", "old_price", "stock", "is_active"]
    filter_horizontal = ["categories"]
    inlines = [ProductImageInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.categories.add(form.instance.category)


@admin.register(ProductRating)
class ProductRatingAdmin(admin.ModelAdmin):
    list_display = ["product", "user", "rating", "updated_at"]
    list_filter = ["rating"]
    search_fields = ["product__title", "user__phone", "user__name"]
    readonly_fields = ["product", "user", "rating", "created_at", "updated_at"]

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        recompute_product_rating(obj.product_id)

    def delete_model(self, request, obj):
        product_id = obj.product_id
        super().delete_model(request, obj)
        recompute_product_rating(product_id)

    def delete_queryset(self, request, queryset):
        product_ids = set(queryset.values_list("product_id", flat=True))
        super().delete_queryset(request, queryset)
        for product_id in product_ids:
            recompute_product_rating(product_id)


@admin.register(ProductComment)
class ProductCommentAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "user",
        "comment_type",
        "moderation_status",
        "official_response",
        "created_at",
    ]
    list_editable = ["moderation_status"]
    list_filter = ["moderation_status", "comment_type"]
    search_fields = ["content", "product__title", "user__phone", "user__name"]
    readonly_fields = [
        "product",
        "user",
        "parent",
        "comment_type",
        "content",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request):
        return False

    @admin.display(boolean=True, description="پاسخ رسمی")
    def official_response(self, obj):
        return obj.user.is_staff
