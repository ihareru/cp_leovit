from django.contrib import admin

from .models import (
    Ticket,
    TicketCounter,
    TicketDueDateHistory,
)


class TicketDueDateHistoryInline(admin.TabularInline):
    model = TicketDueDateHistory
    extra = 0
    can_delete = False

    readonly_fields = [
        "old_due_date",
        "new_due_date",
        "changed_by",
        "reason",
        "changed_at",
    ]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):

    list_display = [
        "number",
        "title",
        "department",
        "author",
        "assignee",
        "status",
        "due_date",
        "created_at",
    ]

    list_filter = [
        "status",
        "department",
        "created_at",
    ]

    search_fields = [
        "title",
        "description",
        "author__username",
        "assignee__username",
    ]

    autocomplete_fields = [
        "author",
        "department",
        "assignee",
    ]

    readonly_fields = [
        "number",
        "created_at",
        "updated_at",
        "assigned_at",
        "completed_at",
    ]

    inlines = [TicketDueDateHistoryInline]

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))

        if obj is not None:
            fields.extend([
                "requested_due_date",
                "due_date",
            ])

        return fields


@admin.register(TicketCounter)
class TicketCounterAdmin(admin.ModelAdmin):
    list_display = ["name", "last_number"]
    readonly_fields = ["name", "last_number"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TicketDueDateHistory)
class TicketDueDateHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "ticket",
        "old_due_date",
        "new_due_date",
        "changed_by",
        "changed_at",
    ]

    readonly_fields = [
        "ticket",
        "old_due_date",
        "new_due_date",
        "changed_by",
        "reason",
        "changed_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False