import pytest

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.organization.models import (
    Department,
    DepartmentMembership,
)


@pytest.fixture
def employee(django_user_model):
    return django_user_model.objects.create_user(
        username="employee",
        password="TestPassword123!",
    )


@pytest.fixture
def department(db):
    return Department.objects.create(
        name="ИТ",
        code="it",
    )


@pytest.mark.django_db
def test_create_department():
    department = Department.objects.create(
        name="Эксплуатация",
        code="maintenance",
    )

    assert department.name == "Эксплуатация"
    assert department.code == "maintenance"
    assert department.is_active is True


@pytest.mark.django_db
def test_department_unique_code(department):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Department.objects.create(
                name="Другой отдел",
                code="it",
            )


@pytest.mark.django_db
def test_add_employee_to_department(employee, department):
    membership = DepartmentMembership.objects.create(
        user=employee,
        department=department,
    )

    assert membership.role == DepartmentMembership.Role.MEMBER
    assert membership.is_active is True


@pytest.mark.django_db
def test_employee_can_join_multiple_departments(
    employee,
    department,
):
    second_department = Department.objects.create(
        name="1С",
        code="1c",
    )

    DepartmentMembership.objects.create(
        user=employee,
        department=department,
    )

    DepartmentMembership.objects.create(
        user=employee,
        department=second_department,
        role=DepartmentMembership.Role.MANAGER,
    )

    assert employee.department_memberships.count() == 2


@pytest.mark.django_db
def test_duplicate_membership_forbidden(employee, department):
    DepartmentMembership.objects.create(
        user=employee,
        department=department,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            DepartmentMembership.objects.create(
                user=employee,
                department=department,
            )


@pytest.mark.django_db
def test_manager_role(employee, department):
    membership = DepartmentMembership.objects.create(
        user=employee,
        department=department,
        role=DepartmentMembership.Role.MANAGER,
    )

    assert membership.role == "manager"
    assert membership.get_role_display() == "Руководитель"


@pytest.mark.django_db
def test_inactive_department_rejects_active_membership(
    employee,
    department,
):
    department.is_active = False
    department.save()

    membership = DepartmentMembership(
        user=employee,
        department=department,
        is_active=True,
    )

    with pytest.raises(ValidationError):
        membership.full_clean()


@pytest.mark.django_db
def test_inactive_membership_allowed_in_inactive_department(
    employee,
    department,
):
    department.is_active = False
    department.save()

    membership = DepartmentMembership(
        user=employee,
        department=department,
        is_active=False,
    )

    membership.full_clean()
    membership.save()

    assert membership.pk is not None
