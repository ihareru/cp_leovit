import pytest

from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from apps.organization.models import Department, DepartmentMembership
from apps.tickets.models import Ticket, TicketActionHistory
from apps.tickets.services import (
    take_ticket,
    assign_ticket,
    complete_ticket,
    reject_ticket,
)


@pytest.fixture
def data(db, django_user_model):
    department = Department.objects.create(
        name="Тестовый отдел статусов",
        code="status-test",
    )

    users = {}

    for name, role in (
        ("author", None),
        ("executor", DepartmentMembership.Role.EXECUTOR),
        ("manager", DepartmentMembership.Role.MANAGER),
        ("outsider", None),
    ):
        user = django_user_model.objects.create_user(
            username=f"status_{name}",
            password="TestPassword123!",
        )
        users[name] = user

        if role:
            DepartmentMembership.objects.create(
                user=user,
                department=department,
                role=role,
            )

    ticket = Ticket.objects.create(
        author=users["author"],
        department=department,
        title="Тест изменения статуса",
        description="Проверка рабочего процесса",
    )

    users["ticket"] = ticket
    return users


@pytest.mark.django_db
def test_executor_completes_own_ticket(data):
    take_ticket(
        ticket_id=data["ticket"].pk,
        actor=data["executor"],
    )

    ticket = complete_ticket(
        ticket_id=data["ticket"].pk,
        actor=data["executor"],
        comment="Работа выполнена",
    )

    assert ticket.status == Ticket.Status.COMPLETED
    assert ticket.completed_at is not None
    assert ticket.action_history.filter(
        action=TicketActionHistory.Action.COMPLETED
    ).exists()


@pytest.mark.django_db
def test_manager_can_complete_ticket(data):
    assign_ticket(
        ticket_id=data["ticket"].pk,
        assignee=data["executor"],
        actor=data["manager"],
    )

    ticket = complete_ticket(
        ticket_id=data["ticket"].pk,
        actor=data["manager"],
    )

    assert ticket.status == Ticket.Status.COMPLETED


@pytest.mark.django_db
def test_other_user_cannot_complete(data):
    take_ticket(
        ticket_id=data["ticket"].pk,
        actor=data["executor"],
    )

    with pytest.raises(PermissionDenied):
        complete_ticket(
            ticket_id=data["ticket"].pk,
            actor=data["outsider"],
        )


@pytest.mark.django_db
def test_cannot_complete_new_ticket(data):
    with pytest.raises(ValidationError):
        complete_ticket(
            ticket_id=data["ticket"].pk,
            actor=data["manager"],
        )


@pytest.mark.django_db
def test_manager_rejects_ticket(data):
    ticket = reject_ticket(
        ticket_id=data["ticket"].pk,
        actor=data["manager"],
        reason="Не относится к компетенции отдела",
    )

    assert ticket.status == Ticket.Status.REJECTED
    assert ticket.action_history.filter(
        action=TicketActionHistory.Action.REJECTED,
        comment="Не относится к компетенции отдела",
    ).exists()


@pytest.mark.django_db
def test_reject_requires_reason(data):
    with pytest.raises(ValidationError):
        reject_ticket(
            ticket_id=data["ticket"].pk,
            actor=data["manager"],
            reason="   ",
        )


@pytest.mark.django_db
def test_executor_cannot_reject(data):
    with pytest.raises(PermissionDenied):
        reject_ticket(
            ticket_id=data["ticket"].pk,
            actor=data["executor"],
            reason="Причина",
        )


@pytest.mark.django_db
def test_cannot_reject_completed_ticket(data):
    take_ticket(
        ticket_id=data["ticket"].pk,
        actor=data["executor"],
    )
    complete_ticket(
        ticket_id=data["ticket"].pk,
        actor=data["executor"],
    )

    with pytest.raises(ValidationError):
        reject_ticket(
            ticket_id=data["ticket"].pk,
            actor=data["manager"],
            reason="Позднее отклонение",
        )


@pytest.mark.django_db
def test_complete_view_requires_post(client, data):
    client.force_login(data["executor"])

    response = client.get(
        reverse("tickets:complete", args=[data["ticket"].number])
    )

    assert response.status_code == 405


@pytest.mark.django_db
def test_reject_view_requires_post(client, data):
    client.force_login(data["manager"])

    response = client.get(
        reverse("tickets:reject", args=[data["ticket"].number])
    )

    assert response.status_code == 405


@pytest.mark.django_db
def test_complete_view_success(client, data):
    take_ticket(
        ticket_id=data["ticket"].pk,
        actor=data["executor"],
    )

    client.force_login(data["executor"])

    response = client.post(
        reverse("tickets:complete", args=[data["ticket"].number]),
        {"comment": "Готово"},
    )

    assert response.status_code == 302
    data["ticket"].refresh_from_db()
    assert data["ticket"].status == Ticket.Status.COMPLETED


@pytest.mark.django_db
def test_reject_view_success(client, data):
    client.force_login(data["manager"])

    response = client.post(
        reverse("tickets:reject", args=[data["ticket"].number]),
        {"reason": "Неверный отдел"},
    )

    assert response.status_code == 302
    data["ticket"].refresh_from_db()
    assert data["ticket"].status == Ticket.Status.REJECTED


@pytest.mark.django_db
def test_executor_sees_complete_button(client, data):
    take_ticket(
        ticket_id=data["ticket"].pk,
        actor=data["executor"],
    )

    client.force_login(data["executor"])

    response = client.get(
        reverse(
            "tickets:detail",
            args=[data["ticket"].number],
        )
    )

    assert response.status_code == 200
    assert response.context["can_complete"] is True

    assert reverse(
        "tickets:complete",
        args=[data["ticket"].number],
    ) in response.content.decode("utf-8")
