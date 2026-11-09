from django.db.models import Q

from apps.organization.models import DepartmentMembership
from .models import Ticket


def get_visible_tickets(user):
    """
    Возвращает QuerySet заявок, доступных пользователю.

    Обычный сотрудник:
        только собственные заявки.

    Исполнитель / руководитель:
        собственные заявки и заявки своих отделов.

    Наблюдатель / администратор:
        все заявки.
    """

    queryset = Ticket.objects.select_related(
        "author",
        "department",
        "assignee",
    )

    if not user.is_authenticated or not user.is_active:
        return queryset.none()

    if (
        user.is_superuser
        or user.has_perm("tickets.view_all_tickets")
    ):
        return queryset

    department_ids = DepartmentMembership.objects.filter(
        user=user,
        is_active=True,
        department__is_active=True,
        role__in=[
            DepartmentMembership.Role.EXECUTOR,
            DepartmentMembership.Role.MANAGER,
        ],
    ).values_list("department_id", flat=True)

    return queryset.filter(
        Q(author=user)
        | Q(department_id__in=department_ids)
    ).distinct()
