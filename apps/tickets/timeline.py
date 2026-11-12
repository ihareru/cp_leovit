from dataclasses import dataclass
from datetime import datetime

from .models import (
    TicketActionHistory,
    TicketDueDateHistory,
    TicketAttachment,
)


@dataclass(frozen=True)
class TicketTimelineEvent:
    kind: str
    title: str
    occurred_at: datetime
    actor: object | None
    comment: str = ""
    old_assignee: object | None = None
    new_assignee: object | None = None
    old_due_date: object | None = None
    new_due_date: object | None = None


def get_ticket_timeline(ticket):
    """
    Формирует общую историю заявки.

    События:
    - создание заявки;
    - принятие в работу;
    - назначение и переназначение;
    - завершение;
    - отклонение;
    - изменение срока выполнения.

    Возвращает события от новых к старым.
    """

    events = []

    # 1. Создание заявки
    events.append(
        TicketTimelineEvent(
            kind="created",
            title="Заявка создана",
            occurred_at=ticket.created_at,
            actor=ticket.author,
        )
    )

    # 2. История действий
    actions = (
        TicketActionHistory.objects
        .filter(ticket=ticket)
        .select_related(
            "actor",
            "old_assignee",
            "new_assignee",
        )
    )

    for action in actions:
        events.append(
            TicketTimelineEvent(
                kind="action",
                title=action.get_action_display(),
                occurred_at=action.created_at,
                actor=action.actor,
                comment=action.comment or "",
                old_assignee=action.old_assignee,
                new_assignee=action.new_assignee,
            )
        )

    # 3. История сроков
    due_date_changes = (
        TicketDueDateHistory.objects
        .filter(ticket=ticket)
        .select_related("changed_by")
    )

    for change in due_date_changes:
        events.append(
            TicketTimelineEvent(
                kind="due_date",
                title="Изменён срок выполнения",
                occurred_at=change.changed_at,
                actor=change.changed_by,
                comment=change.reason or "",
                old_due_date=change.old_due_date,
                new_due_date=change.new_due_date,
            )
        )

    # 4. История удаления вложений
    deleted_attachments = (
        TicketAttachment.objects
        .filter(
            ticket=ticket,
            deleted_at__isnull=False,
        )
        .select_related("deleted_by")
    )

    for attachment in deleted_attachments:
        events.append(
            TicketTimelineEvent(
                kind="attachment_deleted",
                title="Удалено вложение",
                occurred_at=attachment.deleted_at,
                actor=attachment.deleted_by,
                comment=attachment.original_name,
            )
        )

    # 5. Общая сортировка
    events.sort(
        key=lambda event: event.occurred_at,
        reverse=True,
    )

    return events
