from django import forms

from apps.organization.models import Department
from .models import Ticket


class TicketCreateForm(forms.ModelForm):

    class Meta:
        model = Ticket

        fields = [
            "department",
            "title",
            "description",
            "requested_due_date",
        ]

        widgets = {
            "department": forms.Select(
                attrs={"class": "form-select"}
            ),
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Кратко опишите проблему",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Подробное описание заявки",
                }
            ),
            "requested_due_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
                format="%Y-%m-%d",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["department"].queryset = (
            Department.objects.filter(is_active=True)
            .order_by("name")
        )

        self.fields["department"].empty_label = (
            "Выберите отдел"
        )

        self.fields["requested_due_date"].input_formats = [
            "%Y-%m-%d",
        ]

        self.fields["description"].widget.attrs[
            "placeholder"
        ] = "Опишите проблему, необходимые действия и другую информацию"
