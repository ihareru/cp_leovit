from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.organization.models import DepartmentMembership
from .permissions import (
    can_execute_department_tickets,
    can_manage_department_tickets,
)

from .models import Ticket, TicketDueDateHistory, TicketActionHistory
from .permissions import can_change_ticket_due_date


@transaction.atomic
def change_ticket_due_date(
    *,
    ticket,
    new_due_date,
    changed_by,
    reason="",
):
    """
    Изменение срока выполнения заявки.

    Изменять срок может руководитель отдела
    или администратор портала.

    Каждое фактическое изменение фиксируется
    в TicketDueDateHistory.
    """

    locked_ticket = (
        Ticket.objects
        .select_for_update()
        .select_related("department")
        .get(pk=ticket.pk)
    )

    # Проверка прав отдельно от статуса: закрытая заявка для
    # уполномоченного пользователя должна давать ValidationError.
    is_manager = can_manage_department_tickets(
        changed_by,
        locked_ticket.department,
    )
    is_assigned_executor = (
        changed_by is not None
        and getattr(changed_by, "is_authenticated", False)
        and locked_ticket.assignee_id == changed_by.pk
        and can_execute_department_tickets(
            changed_by,
            locked_ticket.department,
        )
    )

    if not (is_manager or is_assigned_executor):
        raise PermissionDenied(
            "Нет прав на изменение срока заявки."
        )

    # Проверка статуса
    if locked_ticket.status not in (
        Ticket.Status.CREATED,
        Ticket.Status.IN_PROGRESS,
    ):
        raise ValidationError(
            "Нельзя изменить срок закрытой заявки."
        )

    old_due_date = locked_ticket.due_date

    # Если срок не изменился, историю не создаём
    if old_due_date == new_due_date:
        return locked_ticket

    # Причина обязательна
    reason = (reason or "").strip()

    if not reason:
        raise ValidationError(
            "Необходимо указать причину изменения срока."
        )

    locked_ticket.due_date = new_due_date

    locked_ticket.save(
        update_fields=[
            "due_date",
            "updated_at",
        ]
    )

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

    TicketActionHistory.objects.create(
        ticket=ticket,
        action=TicketActionHistory.Action.TAKEN,
        actor=actor,
        new_assignee=actor,
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

    previous_assignee = ticket.assignee

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

    TicketActionHistory.objects.create(
        ticket=ticket,
        action=(
            TicketActionHistory.Action.REASSIGNED
            if previous_assignee is not None
            else TicketActionHistory.Action.ASSIGNED
        ),
        actor=actor,
        old_assignee=previous_assignee,
        new_assignee=assignee,
    )

    return ticket


@transaction.atomic
def complete_ticket(*, ticket_id, actor, comment=""):
    ticket = (
        Ticket.objects
        .select_for_update()
        .select_related("department")
        .get(pk=ticket_id)
    )

    if not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied

    can_complete = (
        ticket.assignee_id == actor.pk
        and can_execute_department_tickets(
            actor, ticket.department
        )
    ) or can_manage_department_tickets(
        actor, ticket.department
    )

    if not can_complete:
        raise PermissionDenied(
            "Нет прав на завершение заявки."
        )

    if ticket.status != Ticket.Status.IN_PROGRESS:
        raise ValidationError(
            "Завершить можно только заявку в работе."
        )

    if ticket.assignee_id is None:
        raise ValidationError(
            "У заявки отсутствует исполнитель."
        )

    ticket.status = Ticket.Status.COMPLETED
    ticket.completed_at = timezone.now()

    ticket.save(
        update_fields=[
            "status",
            "completed_at",
            "updated_at",
        ]
    )

    TicketActionHistory.objects.create(
        ticket=ticket,
        action=TicketActionHistory.Action.COMPLETED,
        actor=actor,
        comment=comment.strip(),
    )

    return ticket


@transaction.atomic
def reject_ticket(*, ticket_id, actor, reason):
    ticket = (
        Ticket.objects
        .select_for_update()
        .select_related("department")
        .get(pk=ticket_id)
    )

    if not can_manage_department_tickets(
        actor, ticket.department
    ):
        raise PermissionDenied(
            "Нет прав на отклонение заявки."
        )

    reason = (reason or "").strip()

    if not reason:
        raise ValidationError(
            "Укажите причину отклонения."
        )

    if ticket.status not in (
        Ticket.Status.CREATED,
        Ticket.Status.IN_PROGRESS,
    ):
        raise ValidationError(
            "Заявка уже закрыта."
        )

    ticket.status = Ticket.Status.REJECTED

    ticket.save(
        update_fields=["status", "updated_at"]
    )

    TicketActionHistory.objects.create(
        ticket=ticket,
        action=TicketActionHistory.Action.REJECTED,
        actor=actor,
        comment=reason,
    )

    return ticket
