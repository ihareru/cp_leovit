from django import forms
from django.contrib.auth.forms import AuthenticationForm


class PortalAuthenticationForm(AuthenticationForm):
    remember_me = forms.BooleanField(
        label="Запомнить меня",
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
            }
        ),
    )

    username = forms.EmailField(
        label="Электронная почта",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Введите email",
                "autocomplete": "username",
                "autofocus": True,
            }
        ),
    )

    password = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Введите пароль",
                "autocomplete": "current-password",
            }
        ),
    )
