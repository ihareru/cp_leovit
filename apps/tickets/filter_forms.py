from django import forms

from django.contrib.auth import get_user_model

from apps.organization.models import Department
from .models import Ticket


class TicketFilterForm(forms.Form):

    q = forms.CharField(
        label="Поиск по номеру или названию",
        required=False,
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Номер заявки или название",
            }
        ),
    )

    status = forms.ChoiceField(
        label="Статус",
        required=False,
        choices=[
            ("", "Все статусы"),
            *Ticket.Status.choices,
        ],
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    department = forms.ModelChoiceField(
        label="Отдел",
        queryset=Department.objects.none(),
        required=False,
        empty_label="Все отделы",
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    assignee = forms.ModelChoiceField(
        label="Исполнитель",
        queryset=get_user_model().objects.none(),
        required=False,
        empty_label="Все исполнители",
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    def __init__(self, *args, visible_tickets=None, **kwargs):
        super().__init__(*args, **kwargs)

        if visible_tickets is None:
            visible_tickets = Ticket.objects.none()

        department_ids = visible_tickets.values_list(
            "department_id",
            flat=True,
        ).distinct()

        assignee_ids = (
            visible_tickets
            .filter(assignee__isnull=False)
            .values_list("assignee_id", flat=True)
            .distinct()
        )

        self.fields["department"].queryset = (
            Department.objects.filter(
                pk__in=department_ids,
            ).order_by("name")
        )

        User = get_user_model()

        self.fields["assignee"].queryset = (
            User.objects.filter(
                pk__in=assignee_ids,
            ).order_by("last_name", "first_name", "username")
        )

        self.fields["assignee"].label_from_instance = (
            lambda user: user.get_full_name() or user.username
        )
