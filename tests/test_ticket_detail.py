import pytest

from datetime import date

from django.contrib.auth.models import Group, Permission
from django.urls import reverse

from apps.organization.models import (
    Department,
    DepartmentMembership,
)
from apps.tickets.models import Ticket
from apps.tickets.services import change_ticket_due_date


@pytest.fixture
def users(django_user_model):
    author = django_user_model.objects.create_user(
        username="detail_author",
        password="TestPassword123!",
    )

    executor = django_user_model.objects.create_user(
        username="detail_executor",
        password="TestPassword123!",
    )

    outsider = django_user_model.objects.create_user(
        username="detail_outsider",
        password="TestPassword123!",
    )

    return author, executor, outsider


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
def tickets(users, departments):
    author, executor, outsider = users
    it, one_c = departments

    ticket_it = Ticket.objects.create(
        author=author,
        department=it,
        title="Проблема с принтером",
        description="Принтер не печатает",
        requested_due_date=date(2026, 11, 20),
    )

    ticket_1c = Ticket.objects.create(
        author=outsider,
        department=one_c,
        title="Ошибка в 1С",
        description="Ошибка проведения документа",
    )

    return ticket_it, ticket_1c


@pytest.mark.django_db
def test_detail_requires_login(client, tickets):
    ticket = tickets[0]

    response = client.get(
        reverse("tickets:detail", args=[ticket.number])
    )

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_author_can_open_own_ticket(client, users, tickets):
    author, _, _ = users
    ticket = tickets[0]

    client.force_login(author)

    response = client.get(
        reverse("tickets:detail", args=[ticket.number])
    )

    assert response.status_code == 200
    assert "Проблема с принтером" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_outsider_cannot_open_foreign_ticket(
    client, users, tickets
):
    _, _, outsider = users
    ticket = tickets[0]

    client.force_login(outsider)

    response = client.get(
        reverse("tickets:detail", args=[ticket.number])
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_executor_can_open_department_ticket(
    client, users, departments, tickets
):
    _, executor, _ = users
    it, _ = departments
    ticket = tickets[0]

    DepartmentMembership.objects.create(
        user=executor,
        department=it,
        role=DepartmentMembership.Role.EXECUTOR,
    )

    client.force_login(executor)

    response = client.get(
        reverse("tickets:detail", args=[ticket.number])
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_executor_cannot_open_other_department_ticket(
    client, users, departments, tickets
):
    _, executor, _ = users
    it, _ = departments
    ticket = tickets[1]

    DepartmentMembership.objects.create(
        user=executor,
        department=it,
        role=DepartmentMembership.Role.EXECUTOR,
    )

    client.force_login(executor)

    response = client.get(
        reverse("tickets:detail", args=[ticket.number])
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_observer_can_open_any_ticket(client, users, tickets):
    _, executor, _ = users

    group, _ = Group.objects.get_or_create(
        name="ticket_observers",
    )

    permission = Permission.objects.get(
        content_type__app_label="tickets",
        codename="view_all_tickets",
    )

    group.permissions.add(permission)
    executor.groups.add(group)

    client.force_login(executor)

    response = client.get(
        reverse("tickets:detail", args=[tickets[1].number])
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_nonexistent_ticket_returns_404(client, users):
    author, _, _ = users

    client.force_login(author)

    response = client.get(
        reverse("tickets:detail", args=[999999999])
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_ticket_detail_displays_due_date_history(
    client, users, tickets
):
    author, _, _ = users
    ticket = tickets[0]

    manager = type(author).objects.create_user(
        username="detail_history_manager",
        password="TestPassword123!",
    )

    DepartmentMembership.objects.create(
        user=manager,
        department=ticket.department,
        role=DepartmentMembership.Role.MANAGER,
    )

    change_ticket_due_date(
        ticket=ticket,
        new_due_date=date(2026, 11, 25),
        changed_by=manager,
        reason="Ожидание запасной части",
    )

    client.force_login(author)

    response = client.get(
        reverse("tickets:detail", args=[ticket.number])
    )

    assert response.status_code == 200

    content = response.content.decode("utf-8")

    assert "25.11.2026" in content
    assert "Ожидание запасной части" in content


@pytest.mark.django_db
def test_ticket_list_contains_detail_link(
    client, users, tickets
):
    author, _, _ = users
    ticket = tickets[0]

    client.force_login(author)

    response = client.get(reverse("tickets:list"))

    detail_url = reverse(
        "tickets:detail",
        args=[ticket.number],
    )

    assert detail_url in response.content.decode("utf-8")
