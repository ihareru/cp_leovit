from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Department(models.Model):
    name = models.CharField(
        "Название отдела",
        max_length=150,
        unique=True,
    )

    code = models.SlugField(
        "Код отдела",
        max_length=50,
        unique=True,
        allow_unicode=False,
    )

    notification_email = models.EmailField(
        "Email для уведомлений",
        blank=True,
    )

    is_active = models.BooleanField(
        "Активен",
        default=True,
    )

    created_at = models.DateTimeField(
        "Дата создания",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "Дата изменения",
        auto_now=True,
    )

    class Meta:
        verbose_name = "Отдел"
        verbose_name_plural = "Отделы"
        ordering = ["name"]

    def __str__(self):
        return self.name


class DepartmentMembership(models.Model):
    class Role(models.TextChoices):
        MEMBER = "member", "Сотрудник"
        MANAGER = "manager", "Руководитель"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="department_memberships",
        verbose_name="Сотрудник",
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Отдел",
    )

    role = models.CharField(
        "Роль",
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )

    is_active = models.BooleanField(
        "Активен",
        default=True,
    )

    created_at = models.DateTimeField(
        "Дата добавления",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Участник отдела"
        verbose_name_plural = "Участники отделов"
        ordering = ["department__name", "user__username"]

        constraints = [
            models.UniqueConstraint(
                fields=["user", "department"],
                name="unique_user_department",
            ),
        ]

    def __str__(self):
        return (
            f"{self.user} — "
            f"{self.department} "
            f"({self.get_role_display()})"
        )

    def clean(self):
        super().clean()

        if self.is_active and not self.department.is_active:
            raise ValidationError({
                "department": (
                    "Нельзя добавить активного участника "
                    "в неактивный отдел."
                )
            })
