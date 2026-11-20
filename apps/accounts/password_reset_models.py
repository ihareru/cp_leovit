from django.conf import settings
from django.db import models
from django.utils import timezone


class PasswordResetCode(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_codes",
        verbose_name="Пользователь",
    )

    code_hash = models.CharField(
        "Хеш кода",
        max_length=255,
    )

    email_at_creation = models.EmailField(
        "Email на момент создания",
        max_length=254,
        default="",
        editable=False,
    )

    password_fingerprint = models.CharField(
        "Отпечаток текущего пароля",
        max_length=64,
        default="",
        editable=False,
    )

    created_at = models.DateTimeField(
        "Дата создания",
        default=timezone.now,
        db_index=True,
    )

    expires_at = models.DateTimeField(
        "Действует до",
    )

    attempts = models.PositiveSmallIntegerField(
        "Количество неверных попыток",
        default=0,
    )

    used_at = models.DateTimeField(
        "Дата использования",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Код восстановления пароля"
        verbose_name_plural = "Коды восстановления пароля"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "-created_at"],
                name="acc_reset_user_created_idx",
            ),
        ]

    @property
    def is_valid(self):
        return (
            self.used_at is None
            and self.attempts < 5
            and timezone.now() < self.expires_at
        )

    def __str__(self):
        return f"Восстановление пароля: пользователь #{self.user_id}"
