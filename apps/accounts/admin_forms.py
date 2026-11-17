
from django import forms
from django.contrib.auth.forms import (
    AdminUserCreationForm,
    UserChangeForm,
)

from .models import User


class EmailValidationMixin:
    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if not email:
            raise forms.ValidationError(
                "Укажите электронную почту."
            )

        duplicates = User.objects.filter(
            email__iexact=email
        )

        if self.instance.pk:
            duplicates = duplicates.exclude(
                pk=self.instance.pk
            )

        if duplicates.exists():
            raise forms.ValidationError(
                "Пользователь с таким email уже существует."
            )

        return email


class PortalUserCreationForm(
    EmailValidationMixin,
    AdminUserCreationForm,
):
    email = forms.EmailField(
        label="Электронная почта",
        required=True,
    )

    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class PortalUserChangeForm(
    EmailValidationMixin,
    UserChangeForm,
):
    email = forms.EmailField(
        label="Электронная почта",
        required=True,
    )

    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"
