from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.db import transaction

from .models import TicketComment
from .permissions import can_comment_ticket
from .selectors import get_visible_tickets


@transaction.atomic
def add_ticket_comment(*, ticket_id, actor, text):
    """
    Добавляет комментарий к заявке.

    Проверяет:
    - доступ пользователя к заявке;
    - право комментирования;
    - наличие текста;
    - максимальную длину комментария.

    Не изменяет саму заявку.
    """

    # Получаем только заявку, доступную пользователю.
    # select_for_update() здесь не используется.
    ticket = get_visible_tickets(actor).get(
        pk=ticket_id
    )

    # Проверяем право комментирования.
    if not can_comment_ticket(actor, ticket):
        raise PermissionDenied(
            "Нет прав на комментирование заявки."
        )

    # Нормализуем текст.
    text = (text or "").strip()

    if not text:
        raise ValidationError(
            "Комментарий не может быть пустым."
        )

    if len(text) > 5000:
        raise ValidationError(
            "Комментарий не может превышать 5000 символов."
        )

    # Сохраняем комментарий.
    return TicketComment.objects.create(
        ticket=ticket,
        author=actor,
        text=text,
    )
