from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.organization.models import DepartmentMembership
from .permissions import (
    can_execute_department_tickets,
    can_manage_department_tickets,
)

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

def can_be_assigned(user, department):
    """
    Пользователь может исполнять заявки отдела,
    если он активный исполнитель или руководитель
    этого отдела.
    """
    return (
        user is not None
        and user.is_authenticated
        and user.is_active
        and department.is_active
        and can_execute_department_tickets(user, department)
    )


@transaction.atomic
def take_ticket(*, ticket_id, actor):
    """
    Исполнитель или руководитель самостоятельно
    берёт свободную заявку своего отдела.
    """

    ticket = (
        Ticket.objects
        .select_for_update()
        .select_related("department")
        .get(pk=ticket_id)
    )

    if not can_be_assigned(actor, ticket.department):
        raise PermissionDenied(
            "Нет прав на принятие этой заявки."
        )

    if ticket.status != Ticket.Status.CREATED:
        raise ValidationError(
            "В работу можно взять только новую заявку."
        )

    if ticket.assignee_id is not None:
        raise ValidationError(
            "У заявки уже есть исполнитель."
        )

    ticket.assignee = actor
    ticket.status = Ticket.Status.IN_PROGRESS
    ticket.assigned_at = timezone.now()

    ticket.save(
        update_fields=[
            "assignee",
            "status",
            "assigned_at",
            "updated_at",
        ]
    )

    return ticket


@transaction.atomic
def assign_ticket(*, ticket_id, assignee, actor):
    """
    Руководитель назначает исполнителя.

    Допускается назначение самого руководителя.
    """

    ticket = (
        Ticket.objects
        .select_for_update()
        .select_related("department")
        .get(pk=ticket_id)
    )

    if not can_manage_department_tickets(
        actor,
        ticket.department,
    ):
        raise PermissionDenied(
            "Нет прав на назначение исполнителя."
        )

    if ticket.status not in (
        Ticket.Status.CREATED,
        Ticket.Status.IN_PROGRESS,
    ):
        raise ValidationError(
            "Нельзя назначить исполнителя "
            "для завершённой или отклонённой заявки."
        )

    if not can_be_assigned(assignee, ticket.department):
        raise ValidationError(
            "Выбранный сотрудник не является "
            "исполнителем или руководителем этого отдела."
        )

    if ticket.assignee_id == assignee.pk:
        return ticket

    ticket.assignee = assignee
    ticket.status = Ticket.Status.IN_PROGRESS
    ticket.assigned_at = timezone.now()

    ticket.save(
        update_fields=[
            "assignee",
            "status",
            "assigned_at",
            "updated_at",
        ]
    )

    return ticket
