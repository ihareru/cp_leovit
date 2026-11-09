from django.db.models import Q
from django.shortcuts import get_object_or_404
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


def get_visible_ticket_or_404(user, number):
    """
    Возвращает заявку по номеру,
    если пользователь имеет право её просматривать.

    Если заявка отсутствует или недоступна,
    возвращает HTTP 404.
    """

    return get_object_or_404(
        get_visible_tickets(user),
        number=number,
    )

def filter_tickets(queryset, cleaned_data):
    """
    Применяет фильтры к уже доступным заявкам.

    Важно:
    queryset должен быть получен через
    get_visible_tickets(user).
    """

    query = cleaned_data.get("q", "").strip()

    if query:
        search_condition = Q(title__icontains=query)

        if query.isascii() and query.isdecimal():
            search_condition |= Q(number=int(query))

        queryset = queryset.filter(search_condition)

    status = cleaned_data.get("status")

    if status:
        queryset = queryset.filter(status=status)

    department = cleaned_data.get("department")

    if department:
        queryset = queryset.filter(department=department)

    assignee = cleaned_data.get("assignee")

    if assignee:
        queryset = queryset.filter(assignee=assignee)

    return queryset
