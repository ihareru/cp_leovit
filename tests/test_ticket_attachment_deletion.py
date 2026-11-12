import pytest

from django.core.exceptions import PermissionDenied
from django.urls import reverse

from apps.tickets.attachment_services import (
    add_ticket_attachment,
    delete_ticket_attachment,
)
from apps.tickets.models import TicketAttachment, Ticket
from apps.tickets.timeline import get_ticket_timeline

from test_ticket_attachments import (
    attachment_data,
    private_storage,
    make_file,
)


@pytest.mark.django_db
def test_author_can_delete_own_attachment(
    attachment_data,
    private_storage,
):
    ticket = attachment_data["ticket"]
    author = attachment_data["author"]

    attachment = add_ticket_attachment(
        ticket_id=ticket.pk,
        actor=author,
        uploaded_file=make_file("delete.txt"),
    )

    result = delete_ticket_attachment(
        ticket_id=ticket.pk,
        attachment_id=attachment.pk,
        actor=author,
    )

    attachment.refresh_from_db()

    assert result.pk == attachment.pk
    assert attachment.deleted_at is not None
    assert attachment.deleted_by == author
    assert attachment.is_deleted
    assert attachment.file.storage.exists(
        attachment.file.name
    )


@pytest.mark.django_db
def test_deleted_attachment_cannot_be_downloaded(
    client,
    attachment_data,
    private_storage,
):
    ticket = attachment_data["ticket"]
    author = attachment_data["author"]

    attachment = add_ticket_attachment(
        ticket_id=ticket.pk,
        actor=author,
        uploaded_file=make_file("secret.txt"),
    )

    delete_ticket_attachment(
        ticket_id=ticket.pk,
        attachment_id=attachment.pk,
        actor=author,
    )

    client.force_login(author)

    response = client.get(
        reverse(
            "tickets:download_attachment",
            args=[ticket.number, attachment.pk],
        )
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_outsider_cannot_delete_attachment(
    attachment_data,
    private_storage,
):
    ticket = attachment_data["ticket"]
    author = attachment_data["author"]
    outsider = attachment_data["outsider"]

    attachment = add_ticket_attachment(
        ticket_id=ticket.pk,
        actor=author,
        uploaded_file=make_file("protected.txt"),
    )

    with pytest.raises(Ticket.DoesNotExist):
        delete_ticket_attachment(
            ticket_id=ticket.pk,
            attachment_id=attachment.pk,
            actor=outsider,
        )

    attachment.refresh_from_db()

    assert attachment.deleted_at is None


@pytest.mark.django_db
def test_deleted_attachment_appears_in_timeline(
    attachment_data,
    private_storage,
):
    ticket = attachment_data["ticket"]
    author = attachment_data["author"]

    attachment = add_ticket_attachment(
        ticket_id=ticket.pk,
        actor=author,
        uploaded_file=make_file("history.txt"),
    )

    delete_ticket_attachment(
        ticket_id=ticket.pk,
        attachment_id=attachment.pk,
        actor=author,
    )

    events = get_ticket_timeline(ticket)

    deletion_events = [
        event
        for event in events
        if event.kind == "attachment_deleted"
    ]

    assert len(deletion_events) == 1
    assert deletion_events[0].actor == author
    assert deletion_events[0].comment == "history.txt"


@pytest.mark.django_db
def test_deleted_attachment_not_counted_in_limit(
    attachment_data,
    private_storage,
    settings,
):
    settings.TICKET_ATTACHMENT_MAX_COUNT = 1

    ticket = attachment_data["ticket"]
    author = attachment_data["author"]

    first = add_ticket_attachment(
        ticket_id=ticket.pk,
        actor=author,
        uploaded_file=make_file("first.txt"),
    )

    delete_ticket_attachment(
        ticket_id=ticket.pk,
        attachment_id=first.pk,
        actor=author,
    )

    second = add_ticket_attachment(
        ticket_id=ticket.pk,
        actor=author,
        uploaded_file=make_file("second.txt"),
    )

    assert second.pk != first.pk

    assert TicketAttachment.objects.filter(
        ticket=ticket,
        deleted_at__isnull=True,
    ).count() == 1


@pytest.mark.django_db
def test_attachment_cannot_be_deleted_twice(
    attachment_data,
    private_storage,
):
    ticket = attachment_data["ticket"]
    author = attachment_data["author"]

    attachment = add_ticket_attachment(
        ticket_id=ticket.pk,
        actor=author,
        uploaded_file=make_file("once.txt"),
    )

    delete_ticket_attachment(
        ticket_id=ticket.pk,
        attachment_id=attachment.pk,
        actor=author,
    )

    attachment.refresh_from_db()
    first_deleted_at = attachment.deleted_at

    with pytest.raises(PermissionDenied):
        delete_ticket_attachment(
            ticket_id=ticket.pk,
            attachment_id=attachment.pk,
            actor=author,
        )

    attachment.refresh_from_db()

    assert attachment.deleted_at == first_deleted_at
    assert attachment.deleted_by == author
