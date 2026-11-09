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
