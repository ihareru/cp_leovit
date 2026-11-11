from pathlib import Path

from django.conf import settings
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction

from .attachment_validation import (
    validate_ticket_attachment,
)
from .models import Ticket, TicketAttachment
from .permissions import can_upload_ticket_attachment
from .selectors import get_visible_tickets


@transaction.atomic
def add_ticket_attachment(*, ticket_id, actor, uploaded_file):
    validate_ticket_attachment(uploaded_file)

    # Проверяем видимость заявки без блокировки.
    if not get_visible_tickets(actor).filter(
        pk=ticket_id
    ).exists():
        raise Ticket.DoesNotExist(
            "Заявка недоступна."
        )

    # Блокируем только строку самой заявки.
    # Не используем DISTINCT вместе с FOR UPDATE.
    ticket = (
        Ticket.objects
        .select_for_update()
        .get(pk=ticket_id)
    )

    if not can_upload_ticket_attachment(actor, ticket):
        raise PermissionDenied(
            "Нет прав на загрузку вложений."
        )

    count = TicketAttachment.objects.filter(
        ticket=ticket
    ).count()

    if count >= settings.TICKET_ATTACHMENT_MAX_COUNT:
        raise ValidationError(
            "К заявке можно прикрепить не более 10 файлов."
        )

    original_name = Path(
        uploaded_file.name.replace("\\", "/")
    ).name

    attachment = TicketAttachment(
        ticket=ticket,
        uploaded_by=actor,
        original_name=original_name,
        size=uploaded_file.size,
    )

    attachment.file = uploaded_file
    attachment.save()

    return attachment


@transaction.atomic
def add_ticket_attachments(
    *,
    ticket_id,
    actor,
    uploaded_files,
    comment=None,
):
    files = list(uploaded_files)

    if not files:
        return []

    for uploaded_file in files:
        validate_ticket_attachment(uploaded_file)

    if not get_visible_tickets(actor).filter(
        pk=ticket_id
    ).exists():
        raise Ticket.DoesNotExist(
            "Заявка недоступна."
        )

    ticket = (
        Ticket.objects
        .select_for_update()
        .get(pk=ticket_id)
    )

    if not can_upload_ticket_attachment(actor, ticket):
        raise PermissionDenied(
            "Нет прав на загрузку вложений."
        )

    if comment is not None:
        if (
            comment.pk is None
            or comment.ticket_id != ticket.pk
            or not comment.__class__.objects.filter(
                pk=comment.pk,
                ticket_id=ticket.pk,
            ).exists()
        ):
            raise ValidationError(
                "Комментарий не принадлежит заявке."
            )

    current_count = TicketAttachment.objects.filter(
        ticket=ticket
    ).count()

    max_count = settings.TICKET_ATTACHMENT_MAX_COUNT

    if current_count + len(files) > max_count:
        raise ValidationError(
            f"К заявке можно прикрепить не более "
            f"{max_count} файлов."
        )

    created = []

    try:
        for uploaded_file in files:
            original_name = Path(
                uploaded_file.name.replace("\\", "/")
            ).name

            attachment = TicketAttachment(
                ticket=ticket,
                comment=comment,
                uploaded_by=actor,
                original_name=original_name,
                size=uploaded_file.size,
            )

            attachment.file = uploaded_file
            attachment.save()

            created.append(attachment)

    except Exception:
        for attachment in created:
            attachment.file.delete(save=False)
        raise

    return created
