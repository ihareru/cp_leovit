from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.organization.models import Department

from django.db import models


class TicketAccess(models.Model):
    """
    Служебная модель для глобальных разрешений
    сервиса заявок.
    """

    class Meta:
        managed = False
        default_permissions = ()
        permissions = [
            (
                "view_all_tickets",
                "Может просматривать все заявки",
            ),
        ]
        verbose_name = "Право доступа к заявкам"
        verbose_name_plural = "Права доступа к заявкам"


class TicketCounter(models.Model):
    """
    Счётчик номеров заявок.

    Используется для безопасной нумерации
    при одновременном создании заявок.
    """

    name = models.CharField(
        max_length=30,
        primary_key=True,
    )

    last_number = models.PositiveBigIntegerField(
        default=0,
    )

    class Meta:
        verbose_name = "Счётчик заявок"
        verbose_name_plural = "Счётчики заявок"

    def __str__(self):
        return f"{self.name}: {self.last_number}"


class Ticket(models.Model):

    class Status(models.TextChoices):
        CREATED = "created", "Создана"
        IN_PROGRESS = "in_progress", "В работе"
        COMPLETED = "completed", "Исполнена"
        REJECTED = "rejected", "Отклонена"

    number = models.PositiveBigIntegerField(
        "Номер заявки",
        unique=True,
        editable=False,
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_tickets",
        verbose_name="Автор",
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="tickets",
        verbose_name="Отдел",
    )

    title = models.CharField(
        "Название заявки",
        max_length=255,
    )

    description = models.TextField(
        "Описание",
    )

    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_tickets",
        verbose_name="Исполнитель",
    )

    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
    )

    requested_due_date = models.DateField(
        "Желаемый срок выполнения",
        null=True,
        blank=True,
    )

    due_date = models.DateField(
        "Текущий срок выполнения",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        "Дата создания",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "Дата изменения",
        auto_now=True,
    )

    assigned_at = models.DateTimeField(
        "Дата назначения",
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        "Дата исполнения",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"
        ordering = ["-created_at", "-number"]

    def __str__(self):
        return f"№{self.number} — {self.title}"

    def clean(self):
        super().clean()

        if self.department_id and not self.department.is_active:
            raise ValidationError({
                "department": "Нельзя создать заявку в неактивный отдел."
            })

    @classmethod
    def next_number(cls):
        """
        Получение следующего номера заявки.

        Счётчик должен быть предварительно создан
        миграцией данных.
        """

        counter = TicketCounter.objects.select_for_update().get(
            name="tickets",
        )

        counter.last_number += 1
        counter.save(update_fields=["last_number"])

        return counter.last_number

    def save(self, *args, **kwargs):
        if self._state.adding:
            with transaction.atomic():
                if self.number is None:
                    self.number = self.next_number()

                if self.due_date is None:
                    self.due_date = self.requested_due_date

                return super().save(*args, **kwargs)

        return super().save(*args, **kwargs)


class TicketDueDateHistory(models.Model):

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="due_date_history",
        verbose_name="Заявка",
    )

    old_due_date = models.DateField(
        "Предыдущий срок",
        null=True,
        blank=True,
    )

    new_due_date = models.DateField(
        "Новый срок",
        null=True,
        blank=True,
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ticket_due_date_changes",
        verbose_name="Кто изменил",
    )

    reason = models.TextField(
        "Причина изменения",
        blank=True,
    )

    changed_at = models.DateTimeField(
        "Дата изменения",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "История срока заявки"
        verbose_name_plural = "История сроков заявок"
        ordering = ["-changed_at"]

    def __str__(self):
        return f"Заявка №{self.ticket.number}: {self.old_due_date} → {self.new_due_date}"
