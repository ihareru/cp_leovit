from django.contrib import admin

from .models import Department, DepartmentMembership


class DepartmentMembershipInline(admin.TabularInline):
    model = DepartmentMembership
    extra = 0
    autocomplete_fields = ["user"]
    fields = ["user", "role", "is_active"]


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "notification_email",
        "is_active",
        "members_count",
    ]

    list_filter = ["is_active"]
    search_fields = ["name", "code", "notification_email"]
    ordering = ["name"]

    prepopulated_fields = {
        "code": ("name",),
    }

    inlines = [DepartmentMembershipInline]

    @admin.display(description="Участников")
    def members_count(self, obj):
        return obj.memberships.filter(
            is_active=True,
        ).count()


@admin.register(DepartmentMembership)
class DepartmentMembershipAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "department",
        "role",
        "is_active",
        "created_at",
    ]

    list_filter = [
        "department",
        "role",
        "is_active",
    ]

    search_fields = [
        "user__username",
        "user__first_name",
        "user__last_name",
        "department__name",
    ]

    autocomplete_fields = [
        "user",
        "department",
    ]

    list_select_related = [
        "user",
        "department",
    ]
