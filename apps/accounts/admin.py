from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class PortalUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "Корпоративная информация",
            {
                "fields": (
                    "middle_name",
                    "position",
                    "phone",
                ),
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets

    list_display = (
        "username",
        "last_name",
        "first_name",
        "email",
        "position",
        "is_active",
        "is_staff",
    )

    search_fields = (
        "username",
        "last_name",
        "first_name",
        "email",
    )
