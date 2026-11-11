import pytest

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.tickets.models import Ticket, TicketAttachment

from test_ticket_attachments import (
    attachment_data,
    private_storage,
)


def make_file(name, content=b"file content"):
    return SimpleUploadedFile(
        name,
        content,
        content_type="application/octet-stream",
    )


@pytest.mark.django_db
def test_create_ticket_with_multiple_files(
    client, attachment_data, private_storage,
):
    author = attachment_data["author"]
    department = attachment_data["ticket"].department

    client.force_login(author)

    response = client.post(
        reverse("tickets:create"),
        {
            "department": department.pk,
            "title": "Заявка с несколькими файлами",
            "description": "Проверка",
            "files": [
                make_file("one.txt"),
                make_file("two.pdf"),
            ],
        },
    )

    assert response.status_code == 302

    ticket = Ticket.objects.get(
        title="Заявка с несколькими файлами"
    )

    assert ticket.attachments.count() == 2


@pytest.mark.django_db
def test_upload_multiple_files_to_existing_ticket(
    client, attachment_data, private_storage,
):
    ticket = attachment_data["ticket"]

    client.force_login(attachment_data["author"])

    response = client.post(
        reverse(
            "tickets:upload_attachment",
            args=[ticket.number],
        ),
        {
            "files": [
                make_file("first.txt"),
                make_file("second.txt"),
            ],
        },
    )

    assert response.status_code == 302
    assert ticket.attachments.count() == 2


@pytest.mark.django_db
def test_empty_upload_is_rejected(
    client, attachment_data, private_storage,
):
    ticket = attachment_data["ticket"]

    client.force_login(attachment_data["author"])

    response = client.post(
        reverse(
            "tickets:upload_attachment",
            args=[ticket.number],
        ),
        {},
    )

    assert response.status_code == 302
    assert ticket.attachments.count() == 0


@pytest.mark.django_db
def test_comment_with_attachments(
    client, attachment_data, private_storage,
):
    ticket = attachment_data["ticket"]

    client.force_login(attachment_data["author"])

    response = client.post(
        reverse(
            "tickets:add_comment",
            args=[ticket.number],
        ),
        {
            "text": "Комментарий с файлами",
            "files": [
                make_file("photo.jpg"),
                make_file("document.pdf"),
            ],
        },
    )

    assert response.status_code == 302

    comment = ticket.comments.get(
        text="Комментарий с файлами"
    )

    assert comment.attachments.count() == 2

    assert TicketAttachment.objects.filter(
        ticket=ticket,
        comment=comment,
    ).count() == 2


@pytest.mark.django_db
def test_comment_attachments_limit(
    client, attachment_data, private_storage, settings,
):
    settings.TICKET_ATTACHMENT_MAX_COUNT = 1

    ticket = attachment_data["ticket"]

    client.force_login(attachment_data["author"])

    response = client.post(
        reverse(
            "tickets:add_comment",
            args=[ticket.number],
        ),
        {
            "text": "Комментарий сверх лимита",
            "files": [
                make_file("one.txt"),
                make_file("two.txt"),
            ],
        },
    )

    assert response.status_code == 302

    assert not ticket.comments.filter(
        text="Комментарий сверх лимита"
    ).exists()

    assert ticket.attachments.count() == 0
