
from django.db import models


class PasswordResetRateLimit(models.Model):

    key = models.CharField(
        "Ключ ограничения",
        max_length=128,
        unique=True,
        editable=False,
    )

    count = models.PositiveBigIntegerField(
        "Количество запросов",
        default=0,
    )

    expires_at = models.DateTimeField(
        "Действует до",
        db_index=True,
    )

    updated_at = models.DateTimeField(
        "Дата последнего запроса",
    )

    class Meta:
        verbose_name = (
            "Ограничение восстановления пароля"
        )

        verbose_name_plural = (
            "Ограничения восстановления пароля"
        )

        db_table = (
            "accounts_password_reset_rate_limit"
        )

    def __str__(self):
        return f"Rate limit #{self.pk}: {self.count}"
