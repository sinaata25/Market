from django.contrib import admin

from common.admin import NormalizedSearchAdminMixin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["title", "price", "old_price", "qty", "product"]


@admin.register(Order)
class OrderAdmin(NormalizedSearchAdminMixin, admin.ModelAdmin):
    list_display = ["code", "user", "status", "total_price", "city", "created_at"]
    list_filter = ["status"]
    list_editable = ["status"]
    search_fields = ["code", "full_name", "phone", "postal_code"]
    inlines = [OrderItemInline]
    readonly_fields = [
        "code",
        "user",
        "items_price",
        "discount",
        "shipping_price",
        "total_price",
    ]
