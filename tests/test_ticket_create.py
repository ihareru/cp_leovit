import pytest

from django.urls import reverse

from apps.organization.models import Department
from apps.tickets.models import Ticket


@pytest.fixture
def employee(django_user_model):
    return django_user_model.objects.create_user(
        username="create_author",
        password="TestPassword123!",
    )


@pytest.fixture
def departments(db):
    active = Department.objects.create(
        name="ИТ",
        code="it",
    )

    inactive = Department.objects.create(
        name="Неактивный отдел",
        code="inactive",
        is_active=False,
    )

    return active, inactive


@pytest.mark.django_db
def test_create_page_requires_login(client):
    response = client.get(reverse("tickets:create"))

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_create_page_available_to_employee(
    client, employee, departments
):
    client.force_login(employee)

    response = client.get(reverse("tickets:create"))

    assert response.status_code == 200
    assert "Создать заявку" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_create_ticket_successfully(
    client, employee, departments
):
    active, _ = departments
    client.force_login(employee)

    response = client.post(
        reverse("tickets:create"),
        {
            "department": active.pk,
            "title": "Не работает компьютер",
            "description": "Компьютер не включается",
            "requested_due_date": "2026-11-20",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("tickets:list")

    ticket = Ticket.objects.get(
        title="Не работает компьютер"
    )

    assert ticket.author == employee
    assert ticket.department == active
    assert ticket.number >= 1
    assert ticket.status == Ticket.Status.CREATED
    assert ticket.assignee is None
    assert str(ticket.due_date) == "2026-11-20"


@pytest.mark.django_db
def test_create_ticket_without_due_date(
    client, employee, departments
):
    active, _ = departments
    client.force_login(employee)

    response = client.post(
        reverse("tickets:create"),
        {
            "department": active.pk,
            "title": "Настройка программы",
            "description": "Требуется настройка",
            "requested_due_date": "",
        },
    )

    assert response.status_code == 302

    ticket = Ticket.objects.get(
        title="Настройка программы"
    )

    assert ticket.due_date is None


@pytest.mark.django_db
def test_cannot_create_ticket_in_inactive_department(
    client, employee, departments
):
    _, inactive = departments
    client.force_login(employee)

    response = client.post(
        reverse("tickets:create"),
        {
            "department": inactive.pk,
            "title": "Тестовая заявка",
            "description": "Описание",
        },
    )

    assert response.status_code == 200
    assert Ticket.objects.count() == 0


@pytest.mark.django_db
def test_ticket_author_cannot_be_overridden(
    client, employee, departments, django_user_model
):
    active, _ = departments

    another_user = django_user_model.objects.create_user(
        username="another_author",
        password="TestPassword123!",
    )

    client.force_login(employee)

    response = client.post(
        reverse("tickets:create"),
        {
            "department": active.pk,
            "title": "Проверка автора",
            "description": "Описание",
            "author": another_user.pk,
            "status": Ticket.Status.COMPLETED,
        },
    )

    assert response.status_code == 302

    ticket = Ticket.objects.get(title="Проверка автора")

    assert ticket.author == employee
    assert ticket.status == Ticket.Status.CREATED


@pytest.mark.django_db
def test_create_ticket_requires_title(
    client, employee, departments
):
    active, _ = departments
    client.force_login(employee)

    response = client.post(
        reverse("tickets:create"),
        {
            "department": active.pk,
            "title": "",
            "description": "Описание",
        },
    )

    assert response.status_code == 200
    assert Ticket.objects.count() == 0


@pytest.mark.django_db
def test_create_ticket_requires_description(
    client, employee, departments
):
    active, _ = departments
    client.force_login(employee)

    response = client.post(
        reverse("tickets:create"),
        {
            "department": active.pk,
            "title": "Название",
            "description": "",
        },
    )

    assert response.status_code == 200
    assert Ticket.objects.count() == 0
