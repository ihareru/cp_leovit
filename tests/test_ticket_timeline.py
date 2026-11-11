from datetime import date, timedelta

import pytest

from django.urls import reverse
from django.utils import timezone

from django.contrib.auth import get_user_model

from apps.organization.models import Department
from apps.tickets.models import Ticket

from apps.tickets.models import (
    TicketActionHistory,
    TicketDueDateHistory,
)

from apps.tickets.timeline import get_ticket_timeline


@pytest.fixture
def employee(db):
    User = get_user_model()

    return User.objects.create_user(
        username="timeline_employee",
        password="TestPassword123!",
        first_name="Иван",
        last_name="Иванов",
    )


@pytest.fixture
def department(db):
    return Department.objects.create(
        name="Технический отдел",
        code="TIMELINE",
    )


@pytest.fixture
def ticket(db, employee, department):
    return Ticket.objects.create(
        author=employee,
        department=department,
        title="Не работает принтер",
        description="Принтер не печатает документы",
        requested_due_date=date(2026, 11, 20),
    )


@pytest.mark.django_db
def test_timeline_contains_creation(ticket):
    events = get_ticket_timeline(ticket)

    assert len(events) == 1
    assert events[0].kind == "created"
    assert events[0].title == "Заявка создана"
    assert events[0].actor == ticket.author


@pytest.mark.django_db
def test_timeline_contains_action(ticket, employee):
    TicketActionHistory.objects.create(
        ticket=ticket,
        action=TicketActionHistory.Action.TAKEN,
        actor=employee,
    )

    events = get_ticket_timeline(ticket)

    assert len(events) == 2
    assert any(
        event.kind == "action"
        for event in events
    )


@pytest.mark.django_db
def test_timeline_contains_due_date_change(ticket, employee):
    TicketDueDateHistory.objects.create(
        ticket=ticket,
        old_due_date=date(2026, 11, 20),
        new_due_date=date(2026, 11, 25),
        changed_by=employee,
        reason="Ожидание оборудования",
    )

    events = get_ticket_timeline(ticket)

    due_date_events = [
        event
        for event in events
        if event.kind == "due_date"
    ]

    assert len(due_date_events) == 1

    event = due_date_events[0]

    assert event.old_due_date == date(2026, 11, 20)
    assert event.new_due_date == date(2026, 11, 25)
    assert event.comment == "Ожидание оборудования"


@pytest.mark.django_db
def test_timeline_sorted_newest_first(ticket, employee):
    TicketActionHistory.objects.create(
        ticket=ticket,
        action=TicketActionHistory.Action.TAKEN,
        actor=employee,
    )

    TicketDueDateHistory.objects.create(
        ticket=ticket,
        old_due_date=date(2026, 11, 20),
        new_due_date=date(2026, 11, 25),
        changed_by=employee,
        reason="Изменение срока",
    )

    events = get_ticket_timeline(ticket)

    timestamps = [
        event.occurred_at
        for event in events
    ]

    assert timestamps == sorted(
        timestamps,
        reverse=True,
    )


@pytest.mark.django_db
def test_timeline_contains_all_event_types(ticket, employee):
    TicketActionHistory.objects.create(
        ticket=ticket,
        action=TicketActionHistory.Action.TAKEN,
        actor=employee,
    )

    TicketDueDateHistory.objects.create(
        ticket=ticket,
        old_due_date=ticket.due_date,
        new_due_date=date(2026, 11, 28),
        changed_by=employee,
        reason="Дополнительные работы",
    )

    events = get_ticket_timeline(ticket)

    kinds = {event.kind for event in events}

    assert kinds == {
        "created",
        "action",
        "due_date",
    }


@pytest.mark.django_db
def test_timeline_visible_in_ticket_detail(
    client,
    ticket,
):
    client.force_login(ticket.author)

    response = client.get(
        reverse(
            "tickets:detail",
            args=[ticket.number],
        )
    )

    assert response.status_code == 200
    assert "timeline" in response.context
    assert "История заявки" in response.content.decode("utf-8")
