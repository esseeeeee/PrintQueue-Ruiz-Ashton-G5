from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class PrintQueueUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("PrintQueue", {"fields": ("role", "phone_number", "profile_photo")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("PrintQueue", {"fields": ("email", "role")}),
    )
    list_display = ("username", "email", "role", "is_active")
    list_filter = ("role", "is_active")
