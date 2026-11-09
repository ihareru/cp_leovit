from django.db import models

from apps.accounts.models import User


class FormsSectionAccess(User):
    """
    Служебная proxy-модель для разрешения доступа
    к разделу «Формы».

    Отдельную таблицу в PostgreSQL не создаёт.
    """

    class Meta:
        proxy = True
        verbose_name = "Доступ к формам"
        verbose_name_plural = "Доступ к формам"
        default_permissions = ()
        permissions = [
            ("access_forms", "Может открывать раздел Формы"),
        ]
