from django.db import transaction

from .models import Ticket, TicketDueDateHistory


@transaction.atomic
def change_ticket_due_date(
    *,
    ticket,
    new_due_date,
    changed_by,
    reason="",
):
    """
    Изменяет срок заявки и сохраняет историю.
    """

    locked_ticket = Ticket.objects.select_for_update().get(
        pk=ticket.pk,
    )

    old_due_date = locked_ticket.due_date

    if old_due_date == new_due_date:
        return locked_ticket

    locked_ticket.due_date = new_due_date
    locked_ticket.save(update_fields=["due_date", "updated_at"])

    TicketDueDateHistory.objects.create(
        ticket=locked_ticket,
        old_due_date=old_due_date,
        new_due_date=new_due_date,
        changed_by=changed_by,
        reason=reason,
    )

    return locked_ticket
