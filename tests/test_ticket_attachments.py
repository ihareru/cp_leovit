from tempfile import TemporaryDirectory

import pytest

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.urls import reverse

from apps.organization.models import Department
from apps.tickets.models import Ticket, TicketAttachment
from apps.tickets.attachment_services import add_ticket_attachment


@pytest.fixture
def attachment_data(db):
    User = get_user_model()

    author = User.objects.create_user(
        username="attachment_author",
        password="TestPassword123!",
    )

    outsider = User.objects.create_user(
        username="attachment_outsider",
        password="TestPassword123!",
    )

    department = Department.objects.create(
        name="Отдел вложений",
        code="ATTACHMENTS",
    )

    ticket = Ticket.objects.create(
        author=author,
        department=department,
        title="Проверка вложений",
        description="Тестовая заявка",
    )

    return {
        "author": author,
        "outsider": outsider,
        "ticket": ticket,
    }


@pytest.fixture
def private_storage(settings):
    with TemporaryDirectory() as directory:
        settings.PRIVATE_UPLOAD_ROOT = directory
        yield directory


def make_file(name="test.txt", content=b"Test content"):
    return SimpleUploadedFile(
        name,
        content,
        content_type="text/plain",
    )


@pytest.mark.django_db
def test_author_can_upload_attachment(
    attachment_data,
    private_storage,
):
    attachment = add_ticket_attachment(
        ticket_id=attachment_data["ticket"].pk,
        actor=attachment_data["author"],
        uploaded_file=make_file(),
    )

    assert attachment.pk is not None
    assert attachment.original_name == "test.txt"
    assert attachment.size == len(b"Test content")
    assert attachment.file.storage.exists(
        attachment.file.name
    )


@pytest.mark.django_db
def test_invalid_extension_rejected(
    attachment_data,
    private_storage,
):
    with pytest.raises(ValidationError):
        add_ticket_attachment(
            ticket_id=attachment_data["ticket"].pk,
            actor=attachment_data["author"],
            uploaded_file=make_file("script.exe"),
        )


@pytest.mark.django_db
def test_oversized_file_rejected(
    attachment_data,
    private_storage,
    settings,
):
    settings.TICKET_ATTACHMENT_MAX_SIZE = 10

    with pytest.raises(ValidationError):
        add_ticket_attachment(
            ticket_id=attachment_data["ticket"].pk,
            actor=attachment_data["author"],
            uploaded_file=make_file(
                content=b"X" * 11,
            ),
        )


@pytest.mark.django_db
def test_outsider_cannot_download(
    client,
    attachment_data,
    private_storage,
):
    ticket = attachment_data["ticket"]

    attachment = add_ticket_attachment(
        ticket_id=ticket.pk,
        actor=attachment_data["author"],
        uploaded_file=make_file(),
    )

    client.force_login(attachment_data["outsider"])

    response = client.get(
        reverse(
            "tickets:download_attachment",
            args=[ticket.number, attachment.pk],
        )
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_author_can_download(
    client,
    attachment_data,
    private_storage,
):
    ticket = attachment_data["ticket"]

    attachment = add_ticket_attachment(
        ticket_id=ticket.pk,
        actor=attachment_data["author"],
        uploaded_file=make_file(),
    )

    client.force_login(attachment_data["author"])

    response = client.get(
        reverse(
            "tickets:download_attachment",
            args=[ticket.number, attachment.pk],
        )
    )

    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"Test content"


@pytest.mark.django_db
def test_attachment_limit(
    attachment_data,
    private_storage,
    settings,
):
    settings.TICKET_ATTACHMENT_MAX_COUNT = 1

    ticket = attachment_data["ticket"]
    author = attachment_data["author"]

    add_ticket_attachment(
        ticket_id=ticket.pk,
        actor=author,
        uploaded_file=make_file("first.txt"),
    )

    with pytest.raises(ValidationError):
        add_ticket_attachment(
            ticket_id=ticket.pk,
            actor=author,
            uploaded_file=make_file("second.txt"),
        )

    assert TicketAttachment.objects.filter(
        ticket=ticket
    ).count() == 1


@pytest.mark.django_db
def test_custom_404_page_for_outsider(
    client,
    attachment_data,
    private_storage,
    settings,
):
    settings.DEBUG = False

    ticket = attachment_data["ticket"]

    attachment = add_ticket_attachment(
        ticket_id=ticket.pk,
        actor=attachment_data["author"],
        uploaded_file=make_file(),
    )

    client.force_login(attachment_data["outsider"])

    response = client.get(
        reverse(
            "tickets:download_attachment",
            args=[ticket.number, attachment.pk],
        )
    )

    assert response.status_code == 404
    assert "Страница не найдена" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_create_ticket_with_attachment(
    client,
    attachment_data,
    private_storage,
):
    author = attachment_data["author"]
    department = attachment_data["ticket"].department

    client.force_login(author)

    response = client.post(
        reverse("tickets:create"),
        {
            "department": department.pk,
            "title": "Заявка с файлом",
            "description": "Проверка загрузки при создании",
            "requested_due_date": "2026-11-20",
            "file": make_file("document.txt", b"Hello"),
        },
    )

    assert response.status_code == 302

    ticket = Ticket.objects.get(
        title="Заявка с файлом"
    )

    attachment = TicketAttachment.objects.get(
        ticket=ticket
    )

    assert attachment.original_name == "document.txt"
    assert attachment.size == 5


@pytest.mark.django_db
def test_create_ticket_without_attachment(
    client,
    attachment_data,
    private_storage,
):
    author = attachment_data["author"]
    department = attachment_data["ticket"].department

    client.force_login(author)

    response = client.post(
        reverse("tickets:create"),
        {
            "department": department.pk,
            "title": "Заявка без файла",
            "description": "Обычная заявка",
            "requested_due_date": "2026-11-20",
        },
    )

    assert response.status_code == 302

    ticket = Ticket.objects.get(
        title="Заявка без файла"
    )

    assert ticket.attachments.count() == 0


@pytest.mark.django_db
def test_invalid_attachment_prevents_ticket_creation(
    client,
    attachment_data,
    private_storage,
):
    author = attachment_data["author"]
    department = attachment_data["ticket"].department

    client.force_login(author)

    response = client.post(
        reverse("tickets:create"),
        {
            "department": department.pk,
            "title": "Заявка с запрещённым файлом",
            "description": "Проверка валидации",
            "file": make_file("virus.exe", b"invalid"),
        },
    )

    assert response.status_code == 200

    assert not Ticket.objects.filter(
        title="Заявка с запрещённым файлом"
    ).exists()
