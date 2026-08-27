from django.contrib import admin

from common.admin import NormalizedSearchAdminMixin

from .models import Order, OrderItem
from .services import schedule_order_status_changed_sms


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

    def save_model(self, request, obj, form, change):
        previous_status = None
        if change and obj.pk:
            previous_status = (
                Order.objects.select_for_update()
                .filter(pk=obj.pk)
                .values_list("status", flat=True)
                .first()
            )
        super().save_model(request, obj, form, change)
        if previous_status is not None:
            schedule_order_status_changed_sms(obj, previous_status)
