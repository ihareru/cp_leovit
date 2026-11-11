import pytest

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from apps.organization.models import (
    Department,
    DepartmentMembership,
)
from apps.tickets.models import Ticket, TicketComment
from apps.tickets.comment_services import add_ticket_comment


@pytest.fixture
def comment_data(db):
    User = get_user_model()

    author = User.objects.create_user(
        username="comment_author",
        password="TestPassword123!",
    )

    executor = User.objects.create_user(
        username="comment_executor",
        password="TestPassword123!",
    )

    outsider = User.objects.create_user(
        username="comment_outsider",
        password="TestPassword123!",
    )

    department = Department.objects.create(
        name="Отдел комментариев",
        code="COMMENTS",
    )

    DepartmentMembership.objects.create(
        user=executor,
        department=department,
        role=DepartmentMembership.Role.EXECUTOR,
    )

    ticket = Ticket.objects.create(
        author=author,
        department=department,
        title="Тест комментариев",
        description="Проверка обсуждения заявки",
    )

    return {
        "author": author,
        "executor": executor,
        "outsider": outsider,
        "ticket": ticket,
    }


@pytest.mark.django_db
def test_author_can_add_comment(comment_data):
    comment = add_ticket_comment(
        ticket_id=comment_data["ticket"].pk,
        actor=comment_data["author"],
        text="Проверьте оборудование",
    )

    assert comment.text == "Проверьте оборудование"
    assert comment.author == comment_data["author"]


@pytest.mark.django_db
def test_executor_can_add_comment(comment_data):
    comment = add_ticket_comment(
        ticket_id=comment_data["ticket"].pk,
        actor=comment_data["executor"],
        text="Приступаю к проверке",
    )

    assert comment.pk is not None


@pytest.mark.django_db
def test_empty_comment_rejected(comment_data):
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        add_ticket_comment(
            ticket_id=comment_data["ticket"].pk,
            actor=comment_data["author"],
            text="   ",
        )


@pytest.mark.django_db
def test_outsider_cannot_add_comment(client, comment_data):
    ticket = comment_data["ticket"]

    client.force_login(comment_data["outsider"])

    response = client.post(
        reverse("tickets:add_comment", args=[ticket.number]),
        {"text": "Чужой комментарий"},
    )

    assert response.status_code == 404
    assert TicketComment.objects.count() == 0


@pytest.mark.django_db
def test_comment_visible_in_ticket_detail(client, comment_data):
    ticket = comment_data["ticket"]

    add_ticket_comment(
        ticket_id=ticket.pk,
        actor=comment_data["author"],
        text="Ожидаем дополнительную информацию",
    )

    client.force_login(comment_data["author"])

    response = client.get(
        reverse("tickets:detail", args=[ticket.number])
    )

    assert response.status_code == 200
    assert "Ожидаем дополнительную информацию" in (
        response.content.decode("utf-8")
    )


@pytest.mark.django_db
def test_add_comment_via_post(client, comment_data):
    ticket = comment_data["ticket"]

    client.force_login(comment_data["author"])

    response = client.post(
        reverse("tickets:add_comment", args=[ticket.number]),
        {"text": "Проверка отправки"},
    )

    assert response.status_code == 302
    assert TicketComment.objects.filter(
        ticket=ticket,
        text="Проверка отправки",
    ).exists()


@pytest.mark.django_db
def test_get_comment_endpoint_not_allowed(client, comment_data):
    ticket = comment_data["ticket"]

    client.force_login(comment_data["author"])

    response = client.get(
        reverse("tickets:add_comment", args=[ticket.number])
    )

    assert response.status_code == 405
