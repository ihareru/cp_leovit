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
