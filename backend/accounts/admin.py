from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Otp, User


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
    list_display = ["phone", "code", "used", "attempts", "expires_at", "created_at"]
    list_filter = ["used"]
    search_fields = ["phone"]
