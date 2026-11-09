from django import forms
from django.contrib.auth import get_user_model

from apps.organization.models import DepartmentMembership


class TicketAssignForm(forms.Form):

    assignee = forms.ModelChoiceField(
        label="Исполнитель",
        queryset=get_user_model().objects.none(),
        empty_label="Выберите исполнителя",
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    def __init__(self, *args, department, **kwargs):
        super().__init__(*args, **kwargs)

        User = get_user_model()

        self.fields["assignee"].queryset = (
            User.objects.filter(
                is_active=True,
                department_memberships__department=department,
                department_memberships__is_active=True,
                department_memberships__role__in=[
                    DepartmentMembership.Role.EXECUTOR,
                    DepartmentMembership.Role.MANAGER,
                ],
            )
            .distinct()
            .order_by("last_name", "first_name", "username")
        )

        if not department.is_active:
            self.fields["assignee"].queryset = User.objects.none()

        self.fields["assignee"].label_from_instance = (
            lambda user: user.get_full_name() or user.username
        )
