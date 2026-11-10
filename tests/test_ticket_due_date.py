from datetime import date

import pytest

from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from apps.organization.models import Department, DepartmentMembership
from apps.tickets.models import Ticket, TicketDueDateHistory
from apps.tickets.services import change_ticket_due_date, take_ticket


@pytest.fixture
def data(db, django_user_model):

    department = Department.objects.create(
        name="Отдел проверки сроков",
        code="due-date-test",
    )

    author = django_user_model.objects.create_user(
        username="due_author",
        password="TestPassword123!",
    )

    executor = django_user_model.objects.create_user(
        username="due_executor",
        password="TestPassword123!",
    )

    manager = django_user_model.objects.create_user(
        username="due_manager",
        password="TestPassword123!",
    )

    DepartmentMembership.objects.create(
        user=executor,
        department=department,
        role=DepartmentMembership.Role.EXECUTOR,
    )

    DepartmentMembership.objects.create(
        user=manager,
        department=department,
        role=DepartmentMembership.Role.MANAGER,
    )

    ticket = Ticket.objects.create(
        author=author,
        department=department,
        title="Проверка сроков",
        description="Тестовая заявка",
        requested_due_date=date(2026, 11, 20),
    )

    return {
        "author": author,
        "executor": executor,
        "manager": manager,
        "ticket": ticket,
    }


@pytest.mark.django_db
def test_manager_can_change_due_date(data):

    ticket = change_ticket_due_date(
        ticket=data["ticket"],
        new_due_date=date(2026, 11, 25),
        changed_by=data["manager"],
        reason="Необходимо дополнительное время",
    )

    assert ticket.due_date == date(2026, 11, 25)


@pytest.mark.django_db
def test_due_date_change_creates_history(data):

    change_ticket_due_date(
        ticket=data["ticket"],
        new_due_date=date(2026, 11, 25),
        changed_by=data["manager"],
        reason="Ожидание оборудования",
    )

    history = TicketDueDateHistory.objects.get(
        ticket=data["ticket"]
    )

    assert history.old_due_date == date(2026, 11, 20)
    assert history.new_due_date == date(2026, 11, 25)
    assert history.changed_by == data["manager"]
    assert history.reason == "Ожидание оборудования"


@pytest.mark.django_db
def test_executor_cannot_change_due_date(data):

    with pytest.raises(PermissionDenied):
        change_ticket_due_date(
            ticket=data["ticket"],
            new_due_date=date(2026, 11, 25),
            changed_by=data["executor"],
            reason="Попытка изменения",
        )


@pytest.mark.django_db
def test_author_cannot_change_due_date(data):

    with pytest.raises(PermissionDenied):
        change_ticket_due_date(
            ticket=data["ticket"],
            new_due_date=date(2026, 11, 25),
            changed_by=data["author"],
            reason="Попытка автора",
        )


@pytest.mark.django_db
def test_due_date_change_requires_reason(data):

    with pytest.raises(ValidationError):
        change_ticket_due_date(
            ticket=data["ticket"],
            new_due_date=date(2026, 11, 25),
            changed_by=data["manager"],
            reason="   ",
        )

    data["ticket"].refresh_from_db()

    assert data["ticket"].due_date == date(2026, 11, 20)

    assert not TicketDueDateHistory.objects.filter(
        ticket=data["ticket"]
    ).exists()


@pytest.mark.django_db
def test_same_due_date_does_not_create_history(data):

    change_ticket_due_date(
        ticket=data["ticket"],
        new_due_date=date(2026, 11, 20),
        changed_by=data["manager"],
    )

    assert not TicketDueDateHistory.objects.filter(
        ticket=data["ticket"]
    ).exists()


@pytest.mark.django_db
def test_cannot_change_completed_ticket(data):

    ticket = data["ticket"]
    ticket.status = Ticket.Status.COMPLETED
    ticket.save(update_fields=["status"])

    with pytest.raises(ValidationError):
        change_ticket_due_date(
            ticket=ticket,
            new_due_date=date(2026, 11, 25),
            changed_by=data["manager"],
            reason="Изменение закрытой заявки",
        )


@pytest.mark.django_db
def test_cannot_change_rejected_ticket(data):

    ticket = data["ticket"]
    ticket.status = Ticket.Status.REJECTED
    ticket.save(update_fields=["status"])

    with pytest.raises(ValidationError):
        change_ticket_due_date(
            ticket=ticket,
            new_due_date=date(2026, 11, 25),
            changed_by=data["manager"],
            reason="Изменение отклонённой заявки",
        )


@pytest.mark.django_db
def test_manager_can_clear_due_date(data):

    ticket = change_ticket_due_date(
        ticket=data["ticket"],
        new_due_date=None,
        changed_by=data["manager"],
        reason="Срок будет определён позднее",
    )

    assert ticket.due_date is None


@pytest.mark.django_db
def test_due_date_view_requires_post(client, data):

    client.force_login(data["manager"])

    response = client.get(
        reverse(
            "tickets:change_due_date",
            args=[data["ticket"].number],
        )
    )

    assert response.status_code == 405


@pytest.mark.django_db
def test_due_date_view_manager_success(client, data):

    client.force_login(data["manager"])

    response = client.post(
        reverse(
            "tickets:change_due_date",
            args=[data["ticket"].number],
        ),
        {
            "new_due_date": "2026-11-25",
            "reason": "Ожидание оборудования",
        },
    )

    assert response.status_code == 302

    data["ticket"].refresh_from_db()

    assert data["ticket"].due_date == date(2026, 11, 25)


@pytest.mark.django_db
def test_due_date_view_executor_denied(client, data):

    client.force_login(data["executor"])

    response = client.post(
        reverse(
            "tickets:change_due_date",
            args=[data["ticket"].number],
        ),
        {
            "new_due_date": "2026-11-25",
            "reason": "Попытка изменения",
        },
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_due_date_view_without_reason(client, data):

    client.force_login(data["manager"])

    response = client.post(
        reverse(
            "tickets:change_due_date",
            args=[data["ticket"].number],
        ),
        {
            "new_due_date": "2026-11-25",
            "reason": "",
        },
    )

    assert response.status_code == 302

    data["ticket"].refresh_from_db()

    assert data["ticket"].due_date == date(2026, 11, 20)


@pytest.mark.django_db
def test_due_date_history_visible_in_detail(client, data):

    change_ticket_due_date(
        ticket=data["ticket"],
        new_due_date=date(2026, 11, 25),
        changed_by=data["manager"],
        reason="Ожидание оборудования",
    )

    client.force_login(data["author"])

    response = client.get(
        reverse(
            "tickets:detail",
            args=[data["ticket"].number],
        )
    )

    assert response.status_code == 200
    assert "Ожидание оборудования" in (
        response.content.decode("utf-8")
    )


@pytest.mark.django_db
def test_assigned_executor_can_change_due_date(data):
    ticket = data["ticket"]

    take_ticket(
        ticket_id=ticket.pk,
        actor=data["executor"],
    )

    updated = change_ticket_due_date(
        ticket=ticket,
        new_due_date=date(2026, 11, 28),
        changed_by=data["executor"],
        reason="Необходимо дополнительное время",
    )

    assert updated.due_date == date(2026, 11, 28)

    assert TicketDueDateHistory.objects.filter(
        ticket=ticket,
        changed_by=data["executor"],
    ).count() == 1


@pytest.mark.django_db
def test_unassigned_executor_cannot_change_due_date(data):
    with pytest.raises(PermissionDenied):
        change_ticket_due_date(
            ticket=data["ticket"],
            new_due_date=date(2026, 11, 28),
            changed_by=data["executor"],
            reason="Попытка изменения",
        )


@pytest.mark.django_db
def test_assigned_executor_sees_due_date_form(client, data):
    ticket = data["ticket"]

    take_ticket(
        ticket_id=ticket.pk,
        actor=data["executor"],
    )

    client.force_login(data["executor"])

    response = client.get(
        reverse("tickets:detail", args=[ticket.number])
    )

    assert response.status_code == 200
    assert response.context["can_change_due_date"] is True


@pytest.mark.django_db
def test_assigned_executor_can_change_due_date_via_post(client, data):
    ticket = data["ticket"]

    take_ticket(
        ticket_id=ticket.pk,
        actor=data["executor"],
    )

    client.force_login(data["executor"])

    response = client.post(
        reverse(
            "tickets:change_due_date",
            args=[ticket.number],
        ),
        {
            "new_due_date": "2026-11-28",
            "reason": "Дополнительные работы",
        },
    )

    assert response.status_code == 302

    ticket.refresh_from_db()

    assert ticket.due_date == date(2026, 11, 28)
