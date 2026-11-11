from apps.organization.models import DepartmentMembership


def is_active_user(user):
    return (
        user.is_authenticated
        and user.is_active
    )


def is_portal_admin(user):
    return (
        is_active_user(user)
        and user.is_superuser
    )


def has_department_role(user, department, roles):
    """
    Проверяет активное членство пользователя
    в активном отделе с одной из указанных ролей.
    """

    if not is_active_user(user):
        return False

    if not department.is_active:
        return False

    return DepartmentMembership.objects.filter(
        user=user,
        department=department,
        role__in=roles,
        is_active=True,
    ).exists()


def can_execute_department_tickets(user, department):
    """
    Исполнитель и руководитель могут
    обрабатывать заявки своего отдела.
    """

    if is_portal_admin(user):
        return True

    return has_department_role(
        user,
        department,
        [
            DepartmentMembership.Role.EXECUTOR,
            DepartmentMembership.Role.MANAGER,
        ],
    )


def can_manage_department_tickets(user, department):
    """
    Руководитель может назначать исполнителей
    и управлять заявками своего отдела.
    """

    if is_portal_admin(user):
        return True

    return has_department_role(
        user,
        department,
        [
            DepartmentMembership.Role.MANAGER,
        ],
    )


def can_view_all_tickets(user):
    """
    Глобальный наблюдатель или администратор
    может просматривать все заявки.
    """

    if not is_active_user(user):
        return False

    return (
        is_portal_admin(user)
        or user.has_perm("tickets.view_all_tickets")
    )


def can_view_department_tickets(user, department):
    """
    Доступ к заявкам отдела:
    исполнитель, руководитель, наблюдатель,
    администратор.
    """

    if can_view_all_tickets(user):
        return True

    return has_department_role(
        user,
        department,
        [
            DepartmentMembership.Role.EXECUTOR,
            DepartmentMembership.Role.MANAGER,
        ],
    )

def can_change_ticket_due_date(user, ticket):
    """
    Изменять срок могут:
    - администратор портала;
    - руководитель отдела;
    - назначенный исполнитель заявки.

    Только для незакрытых заявок.
    """

    if not is_active_user(user):
        return False

    if ticket.status not in (
        "created",
        "in_progress",
    ):
        return False

    if can_manage_department_tickets(
        user,
        ticket.department,
    ):
        return True

    return (
        ticket.assignee_id == user.pk
        and can_execute_department_tickets(
            user,
            ticket.department,
        )
    )


def can_comment_ticket(user, ticket):
    """
    Право добавления комментария.

    Разрешено:
    - автору заявки;
    - действующему исполнителю/руководителю отдела;
    - администратору портала.

    Глобальное право просмотра само по себе
    не даёт права комментирования.
    """

    if not is_active_user(user):
        return False

    if is_portal_admin(user):
        return True

    if ticket.author_id == user.pk:
        return True

    return can_execute_department_tickets(
        user,
        ticket.department,
    )

def can_upload_ticket_attachment(user, ticket):
    """
    Загрузка вложений разрешена тем же пользователям,
    которым разрешено комментировать заявку.
    """
    return can_comment_ticket(user, ticket)
