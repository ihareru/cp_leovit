import pytest

from django.contrib.auth.models import Group, Permission
from django.urls import reverse

from apps.organization.models import (
    Department,
    DepartmentMembership,
)
from apps.tickets.models import Ticket
from apps.tickets.selectors import get_visible_tickets


@pytest.fixture
def users(django_user_model):
    author = django_user_model.objects.create_user(
        username="author",
        password="TestPassword123!",
    )

    executor = django_user_model.objects.create_user(
        username="executor",
        password="TestPassword123!",
    )

    outsider = django_user_model.objects.create_user(
        username="outsider",
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
        description="Не печатает принтер",
    )

    ticket_1c = Ticket.objects.create(
        author=outsider,
        department=one_c,
        title="Ошибка в 1С",
        description="Ошибка при проведении документа",
    )

    return ticket_it, ticket_1c


@pytest.mark.django_db
def test_author_sees_own_ticket(users, tickets):
    author, _, _ = users
    ticket_it, ticket_1c = tickets

    visible = get_visible_tickets(author)

    assert ticket_it in visible
    assert ticket_1c not in visible


@pytest.mark.django_db
def test_executor_sees_department_tickets(
    users,
    departments,
    tickets,
):
    _, executor, _ = users
    it, _ = departments

    DepartmentMembership.objects.create(
        user=executor,
        department=it,
        role=DepartmentMembership.Role.EXECUTOR,
    )

    visible = get_visible_tickets(executor)

    assert tickets[0] in visible
    assert tickets[1] not in visible


@pytest.mark.django_db
def test_manager_sees_department_tickets(
    users,
    departments,
    tickets,
):
    _, executor, _ = users
    it, _ = departments

    DepartmentMembership.objects.create(
        user=executor,
        department=it,
        role=DepartmentMembership.Role.MANAGER,
    )

    visible = get_visible_tickets(executor)

    assert tickets[0] in visible
    assert tickets[1] not in visible


@pytest.mark.django_db
def test_observer_sees_all_tickets(users, tickets):
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

    visible = get_visible_tickets(executor)

    assert visible.count() == 2


@pytest.mark.django_db
def test_outsider_cannot_see_foreign_ticket(
    users,
    tickets,
):
    _, _, outsider = users

    visible = get_visible_tickets(outsider)

    assert tickets[0] not in visible
    assert tickets[1] in visible


@pytest.mark.django_db
def test_ticket_list_requires_login(client):
    response = client.get(reverse("tickets:list"))

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_ticket_list_renders_for_author(
    client,
    users,
    tickets,
):
    author, _, _ = users

    client.force_login(author)

    response = client.get(reverse("tickets:list"))

    assert response.status_code == 200
    assert b"ticket_list.html" not in response.content

    content = response.content.decode("utf-8")

    assert "Проблема с принтером" in content
    assert "Ошибка в 1С" not in content


@pytest.mark.django_db
def test_ticket_list_empty_for_new_user(
    client,
    users,
    tickets,
):
    _, executor, _ = users

    client.force_login(executor)

    response = client.get(reverse("tickets:list"))

    assert response.status_code == 200
    assert "Заявок пока нет" in response.content.decode("utf-8")
