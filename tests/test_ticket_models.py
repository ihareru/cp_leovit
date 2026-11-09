from datetime import date

import pytest

from django.db import IntegrityError, transaction

from apps.organization.models import Department
from apps.tickets.models import Ticket, TicketDueDateHistory
from apps.tickets.services import change_ticket_due_date


@pytest.fixture
def department(db):
    return Department.objects.create(
        name="ИТ",
        code="it",
    )


@pytest.fixture
def employee(django_user_model):
    return django_user_model.objects.create_user(
        username="ticket_author",
        password="TestPassword123!",
    )


@pytest.fixture
def ticket(employee, department):
    return Ticket.objects.create(
        author=employee,
        department=department,
        title="Не работает принтер",
        description="Принтер не печатает документы.",
        requested_due_date=date(2026, 11, 20),
    )


@pytest.mark.django_db
def test_create_ticket(ticket):
    assert ticket.pk is not None
    assert ticket.number >= 1
    assert ticket.status == Ticket.Status.CREATED


@pytest.mark.django_db
def test_ticket_number_is_unique(employee, department):
    first = Ticket.objects.create(
        author=employee,
        department=department,
        title="Первая заявка",
        description="Описание",
    )

    second = Ticket.objects.create(
        author=employee,
        department=department,
        title="Вторая заявка",
        description="Описание",
    )

    assert second.number == first.number + 1


@pytest.mark.django_db
def test_requested_due_date_copied_to_due_date(ticket):
    assert ticket.due_date == date(2026, 11, 20)


@pytest.mark.django_db
def test_ticket_default_status(ticket):
    assert ticket.status == Ticket.Status.CREATED


@pytest.mark.django_db
def test_change_due_date_creates_history(ticket, employee):
    updated = change_ticket_due_date(
        ticket=ticket,
        new_due_date=date(2026, 11, 25),
        changed_by=employee,
        reason="Требуется дополнительное оборудование",
    )

    assert updated.due_date == date(2026, 11, 25)

    history = TicketDueDateHistory.objects.get(ticket=ticket)

    assert history.old_due_date == date(2026, 11, 20)
    assert history.new_due_date == date(2026, 11, 25)
    assert history.changed_by == employee


@pytest.mark.django_db
def test_same_due_date_does_not_create_history(ticket, employee):
    change_ticket_due_date(
        ticket=ticket,
        new_due_date=ticket.due_date,
        changed_by=employee,
    )

    assert TicketDueDateHistory.objects.filter(
        ticket=ticket,
    ).count() == 0


@pytest.mark.django_db
def test_ticket_protects_author(employee, ticket):
    with pytest.raises(Exception):
        employee.delete()

    assert Ticket.objects.filter(pk=ticket.pk).exists()


@pytest.mark.django_db
def test_ticket_string_representation(ticket):
    assert str(ticket).startswith(f"№{ticket.number}")
