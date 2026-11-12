import pytest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from apps.organization.models import DepartmentMembership
from apps.tickets.attachment_services import add_ticket_attachment

from test_ticket_attachments import (
    attachment_data,
    private_storage,
    make_file,
)


@pytest.fixture
def deletion_http_data(attachment_data, private_storage):
    ticket = attachment_data["ticket"]
    author = attachment_data["author"]

    User = get_user_model()

    manager = User.objects.create_user(username="delete_manager")
    observer = User.objects.create_user(username="delete_observer")

    DepartmentMembership.objects.create(
        user=manager,
        department=ticket.department,
        role=DepartmentMembership.Role.MANAGER,
    )

    permission = Permission.objects.get(
        content_type__app_label="tickets",
        codename="view_all_tickets",
    )
    observer.user_permissions.add(permission)

    attachment = add_ticket_attachment(
        ticket_id=ticket.pk,
        actor=author,
        uploaded_file=make_file("delete_http.txt"),
    )

    url = reverse(
        "tickets:delete_attachment",
        args=[ticket.number, attachment.pk],
    )

    return {
        "ticket": ticket,
        "author": author,
        "manager": manager,
        "observer": observer,
        "attachment": attachment,
        "url": url,
    }


@pytest.mark.django_db
def test_get_cannot_delete_attachment(client, deletion_http_data):
    data = deletion_http_data
    client.force_login(data["author"])

    response = client.get(data["url"])

    assert response.status_code == 405

    data["attachment"].refresh_from_db()
    assert data["attachment"].deleted_at is None


@pytest.mark.django_db
def test_delete_requires_authentication(client, deletion_http_data):
    response = client.post(deletion_http_data["url"])

    assert response.status_code == 302
    assert "/login/" in response["Location"]

    deletion_http_data["attachment"].refresh_from_db()
    assert deletion_http_data["attachment"].deleted_at is None


@pytest.mark.django_db
def test_delete_requires_csrf(deletion_http_data):
    data = deletion_http_data
    client = Client(enforce_csrf_checks=True)
    client.force_login(data["author"])

    response = client.post(data["url"])

    assert response.status_code == 403

    data["attachment"].refresh_from_db()
    assert data["attachment"].deleted_at is None


@pytest.mark.django_db
def test_manager_can_delete_attachment(client, deletion_http_data):
    data = deletion_http_data
    client.force_login(data["manager"])

    response = client.post(data["url"])

    assert response.status_code == 302

    data["attachment"].refresh_from_db()
    assert data["attachment"].deleted_by == data["manager"]
    assert data["attachment"].deleted_at is not None


@pytest.mark.django_db
def test_observer_cannot_delete_attachment(client, deletion_http_data):
    data = deletion_http_data
    client.force_login(data["observer"])

    response = client.post(data["url"])

    assert response.status_code == 403

    data["attachment"].refresh_from_db()
    assert data["attachment"].deleted_at is None


@pytest.mark.django_db
def test_outsider_cannot_delete_attachment(client, deletion_http_data):
    data = deletion_http_data
    client.force_login(attachment_data_outsider(data))

    response = client.post(data["url"])

    assert response.status_code == 404

    data["attachment"].refresh_from_db()
    assert data["attachment"].deleted_at is None


def attachment_data_outsider(data):
    return get_user_model().objects.create_user(
        username="delete_http_outsider",
    )


@pytest.mark.django_db
def test_deleted_attachment_hidden_from_detail(client, deletion_http_data):
    data = deletion_http_data
    client.force_login(data["author"])

    response = client.post(data["url"])
    assert response.status_code == 302

    response = client.get(
        reverse("tickets:detail", args=[data["ticket"].number])
    )

    assert response.status_code == 200
    assert response.context["attachments"].count() == 0

    assert any(
        event.kind == "attachment_deleted"
        for event in response.context["timeline"]
    )


@pytest.mark.django_db
def test_second_delete_does_not_change_record(client, deletion_http_data):
    data = deletion_http_data
    client.force_login(data["author"])

    first_response = client.post(data["url"])
    assert first_response.status_code == 302

    data["attachment"].refresh_from_db()
    first_deleted_at = data["attachment"].deleted_at

    second_response = client.post(data["url"])

    assert second_response.status_code == 403

    data["attachment"].refresh_from_db()
    assert data["attachment"].deleted_at == first_deleted_at
