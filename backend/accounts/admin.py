from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Address, Favorite, Otp, User


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "full_name", "city", "is_default"]
    list_filter = ["is_default", "province"]
    search_fields = ["full_name", "phone", "city"]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ["user", "product", "created_at"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["phone", "name", "is_active", "is_staff", "date_joined"]
    list_filter = ["is_active", "is_staff"]
    search_fields = ["phone", "name"]
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("اطلاعات شخصی", {"fields": ("name",)}),
        ("دسترسی‌ها", {"fields": ("is_active", "is_staff", "is_superuser", "groups")}),
        ("تاریخ‌ها", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("phone", "password1", "password2")}),
    )


@admin.register(Otp)
class OtpAdmin(admin.ModelAdmin):
    list_display = [
        "phone",
        "used",
        "attempts",
        "expires_at",
        "sent_at",
        "resend_blocked_until",
        "delivery_status",
        "provider_message_id",
    ]
    list_filter = ["used"]
    search_fields = ["phone"]
    exclude = ["code_hash", "pending_code_hash"]
    readonly_fields = [
        "provider_message_id",
        "delivery_status",
        "sent_at",
        "resend_blocked_until",
        "send_started_at",
        "pending_expires_at",
        "pending_attempts",
        "send_token",
    ]
