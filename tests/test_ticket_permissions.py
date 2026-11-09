import pytest

from django.contrib.auth.models import Group, Permission
from django.contrib.auth.models import AnonymousUser

from apps.organization.models import (
    Department,
    DepartmentMembership,
)
from apps.tickets.permissions import (
    can_execute_department_tickets,
    can_manage_department_tickets,
    can_view_all_tickets,
    can_view_department_tickets,
)


@pytest.fixture
def departments(db):
    it = Department.objects.create(
        name="ИТ",
        code="it",
    )

    one_c = Department.objects.create(
        name="1С",
        code="1c",
    )

    return it, one_c


@pytest.fixture
def employee(django_user_model):
    return django_user_model.objects.create_user(
        username="ticket_employee",
        password="TestPassword123!",
    )


@pytest.fixture
def observer_group(db):
    group, _ = Group.objects.get_or_create(
        name="ticket_observers",
    )

    permission = Permission.objects.get(
        content_type__app_label="tickets",
        codename="view_all_tickets",
    )

    group.permissions.add(permission)

    return group


@pytest.mark.django_db
def test_member_cannot_execute(employee, departments):
    it, _ = departments

    DepartmentMembership.objects.create(
        user=employee,
        department=it,
        role=DepartmentMembership.Role.MEMBER,
    )

    assert not can_execute_department_tickets(employee, it)


@pytest.mark.django_db
def test_executor_can_execute_own_department(
    employee,
    departments,
):
    it, one_c = departments

    DepartmentMembership.objects.create(
        user=employee,
        department=it,
        role=DepartmentMembership.Role.EXECUTOR,
    )

    assert can_execute_department_tickets(employee, it)
    assert not can_execute_department_tickets(employee, one_c)


@pytest.mark.django_db
def test_executor_cannot_manage(employee, departments):
    it, _ = departments

    DepartmentMembership.objects.create(
        user=employee,
        department=it,
        role=DepartmentMembership.Role.EXECUTOR,
    )

    assert not can_manage_department_tickets(employee, it)


@pytest.mark.django_db
def test_manager_can_execute_and_manage(
    employee,
    departments,
):
    it, _ = departments

    DepartmentMembership.objects.create(
        user=employee,
        department=it,
        role=DepartmentMembership.Role.MANAGER,
    )

    assert can_execute_department_tickets(employee, it)
    assert can_manage_department_tickets(employee, it)


@pytest.mark.django_db
def test_roles_are_department_specific(
    employee,
    departments,
):
    it, one_c = departments

    DepartmentMembership.objects.create(
        user=employee,
        department=it,
        role=DepartmentMembership.Role.EXECUTOR,
    )

    DepartmentMembership.objects.create(
        user=employee,
        department=one_c,
        role=DepartmentMembership.Role.MANAGER,
    )

    assert can_execute_department_tickets(employee, it)
    assert not can_manage_department_tickets(employee, it)

    assert can_execute_department_tickets(employee, one_c)
    assert can_manage_department_tickets(employee, one_c)


@pytest.mark.django_db
def test_observer_can_view_all(
    employee,
    departments,
    observer_group,
):
    it, one_c = departments

    employee.groups.add(observer_group)

    assert can_view_all_tickets(employee)
    assert can_view_department_tickets(employee, it)
    assert can_view_department_tickets(employee, one_c)

    assert not can_execute_department_tickets(employee, it)
    assert not can_manage_department_tickets(employee, it)


@pytest.mark.django_db
def test_inactive_membership_denies_access(
    employee,
    departments,
):
    it, _ = departments

    DepartmentMembership.objects.create(
        user=employee,
        department=it,
        role=DepartmentMembership.Role.MANAGER,
        is_active=False,
    )

    assert not can_execute_department_tickets(employee, it)
    assert not can_manage_department_tickets(employee, it)


@pytest.mark.django_db
def test_inactive_department_denies_access(
    employee,
    departments,
):
    it, _ = departments

    DepartmentMembership.objects.create(
        user=employee,
        department=it,
        role=DepartmentMembership.Role.MANAGER,
    )

    it.is_active = False
    it.save()

    assert not can_execute_department_tickets(employee, it)
    assert not can_manage_department_tickets(employee, it)


@pytest.mark.django_db
def test_anonymous_user_has_no_access(departments):
    it, _ = departments

    anonymous = AnonymousUser()

    assert not can_execute_department_tickets(anonymous, it)
    assert not can_manage_department_tickets(anonymous, it)
    assert not can_view_all_tickets(anonymous)


@pytest.mark.django_db
def test_superuser_has_full_access(
    django_user_model,
    departments,
):
    it, one_c = departments

    admin = django_user_model.objects.create_superuser(
        username="ticket_admin",
        password="TestPassword123!",
        email="admin@example.com",
    )

    assert can_view_all_tickets(admin)
    assert can_execute_department_tickets(admin, it)
    assert can_manage_department_tickets(admin, one_c)
