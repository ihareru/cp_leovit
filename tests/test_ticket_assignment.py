import pytest

from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from apps.organization.models import Department, DepartmentMembership
from apps.tickets.models import Ticket
from apps.tickets.services import take_ticket, assign_ticket


@pytest.fixture
def setup_data(db, django_user_model):
    department = Department.objects.create(
        name="Отдел тестирования назначений",
        code="assignment-test",
    )

    other_department = Department.objects.create(
        name="Другой отдел",
        code="assignment-other",
    )

    author = django_user_model.objects.create_user(
        username="assign_author",
        password="TestPassword123!",
    )

    executor = django_user_model.objects.create_user(
        username="assign_executor",
        password="TestPassword123!",
    )

    second_executor = django_user_model.objects.create_user(
        username="assign_executor2",
        password="TestPassword123!",
    )

    manager = django_user_model.objects.create_user(
        username="assign_manager",
        password="TestPassword123!",
    )

    outsider = django_user_model.objects.create_user(
        username="assign_outsider",
        password="TestPassword123!",
    )

    for user, role in (
        (executor, DepartmentMembership.Role.EXECUTOR),
        (second_executor, DepartmentMembership.Role.EXECUTOR),
        (manager, DepartmentMembership.Role.MANAGER),
    ):
        DepartmentMembership.objects.create(
            user=user,
            department=department,
            role=role,
        )

    DepartmentMembership.objects.create(
        user=outsider,
        department=other_department,
        role=DepartmentMembership.Role.EXECUTOR,
    )

    ticket = Ticket.objects.create(
        author=author,
        department=department,
        title="Проверка назначения",
        description="Тестовая заявка",
    )

    return {
        "department": department,
        "author": author,
        "executor": executor,
        "second_executor": second_executor,
        "manager": manager,
        "outsider": outsider,
        "ticket": ticket,
    }


@pytest.mark.django_db
def test_executor_can_take_ticket(setup_data):
    data = setup_data

    ticket = take_ticket(
        ticket_id=data["ticket"].pk,
        actor=data["executor"],
    )

    assert ticket.assignee == data["executor"]
    assert ticket.status == Ticket.Status.IN_PROGRESS
    assert ticket.assigned_at is not None


@pytest.mark.django_db
def test_manager_can_take_ticket(setup_data):
    data = setup_data

    ticket = take_ticket(
        ticket_id=data["ticket"].pk,
        actor=data["manager"],
    )

    assert ticket.assignee == data["manager"]


@pytest.mark.django_db
def test_manager_can_assign_executor(setup_data):
    data = setup_data

    ticket = assign_ticket(
        ticket_id=data["ticket"].pk,
        assignee=data["executor"],
        actor=data["manager"],
    )

    assert ticket.assignee == data["executor"]
    assert ticket.status == Ticket.Status.IN_PROGRESS


@pytest.mark.django_db
def test_manager_can_assign_self(setup_data):
    data = setup_data

    ticket = assign_ticket(
        ticket_id=data["ticket"].pk,
        assignee=data["manager"],
        actor=data["manager"],
    )

    assert ticket.assignee == data["manager"]


@pytest.mark.django_db
def test_executor_cannot_assign_another_user(setup_data):
    data = setup_data

    with pytest.raises(PermissionDenied):
        assign_ticket(
            ticket_id=data["ticket"].pk,
            assignee=data["second_executor"],
            actor=data["executor"],
        )


@pytest.mark.django_db
def test_other_department_executor_cannot_take(setup_data):
    data = setup_data

    with pytest.raises(PermissionDenied):
        take_ticket(
            ticket_id=data["ticket"].pk,
            actor=data["outsider"],
        )


@pytest.mark.django_db
def test_cannot_take_already_assigned_ticket(setup_data):
    data = setup_data

    take_ticket(
        ticket_id=data["ticket"].pk,
        actor=data["executor"],
    )

    with pytest.raises(ValidationError):
        take_ticket(
            ticket_id=data["ticket"].pk,
            actor=data["second_executor"],
        )


@pytest.mark.django_db
def test_manager_can_reassign_ticket(setup_data):
    data = setup_data

    take_ticket(
        ticket_id=data["ticket"].pk,
        actor=data["executor"],
    )

    ticket = assign_ticket(
        ticket_id=data["ticket"].pk,
        assignee=data["second_executor"],
        actor=data["manager"],
    )

    assert ticket.assignee == data["second_executor"]


@pytest.mark.django_db
def test_manager_cannot_assign_outsider(setup_data):
    data = setup_data

    with pytest.raises(ValidationError):
        assign_ticket(
            ticket_id=data["ticket"].pk,
            assignee=data["outsider"],
            actor=data["manager"],
        )


@pytest.mark.django_db
def test_take_ticket_view_requires_post(client, setup_data):
    data = setup_data
    client.force_login(data["executor"])

    response = client.get(
        reverse(
            "tickets:take",
            args=[data["ticket"].number],
        )
    )

    assert response.status_code == 405


@pytest.mark.django_db
def test_take_ticket_view_success(client, setup_data):
    data = setup_data
    client.force_login(data["executor"])

    response = client.post(
        reverse(
            "tickets:take",
            args=[data["ticket"].number],
        )
    )

    assert response.status_code == 302

    data["ticket"].refresh_from_db()

    assert data["ticket"].assignee == data["executor"]
    assert data["ticket"].status == Ticket.Status.IN_PROGRESS


@pytest.mark.django_db
def test_assign_view_denies_executor(client, setup_data):
    data = setup_data
    client.force_login(data["executor"])

    response = client.post(
        reverse(
            "tickets:assign",
            args=[data["ticket"].number],
        ),
        {"assignee": data["second_executor"].pk},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_assign_view_manager_success(client, setup_data):
    data = setup_data
    client.force_login(data["manager"])

    response = client.post(
        reverse(
            "tickets:assign",
            args=[data["ticket"].number],
        ),
        {"assignee": data["executor"].pk},
    )

    assert response.status_code == 302

    data["ticket"].refresh_from_db()
    assert data["ticket"].assignee == data["executor"]
