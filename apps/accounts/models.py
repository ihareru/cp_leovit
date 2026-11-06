from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Пользователь корпоративного портала.

    Создание пользователей разрешено
    только администраторам.
    """

    email = models.EmailField(
        "Электронная почта",
        blank=True,
    )

    middle_name = models.CharField(
        "Отчество",
        max_length=150,
        blank=True,
    )

    position = models.CharField(
        "Должность",
        max_length=255,
        blank=True,
    )

    phone = models.CharField(
        "Телефон",
        max_length=50,
        blank=True,
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["last_name", "first_name", "username"]

    def __str__(self):
        full_name = " ".join(
            part
            for part in [
                self.last_name,
                self.first_name,
                self.middle_name,
            ]
            if part
        )

        return full_name or self.username
