
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .admin_forms import (
    PortalUserChangeForm,
    PortalUserCreationForm,
)
from .models import User


@admin.register(User)
class PortalUserAdmin(UserAdmin):
    form = PortalUserChangeForm
    add_form = PortalUserCreationForm

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

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Электронная почта",
            {
                "fields": ("email",),
            },
        ),
    )

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
