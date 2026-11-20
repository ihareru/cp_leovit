from django import forms
from django.core.exceptions import ValidationError


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label="Электронная почта",
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Введите email",
                "autocomplete": "email",
                "autofocus": True,
            }
        ),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class PasswordResetConfirmForm(forms.Form):
    code = forms.CharField(
        label="Код подтверждения",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "000000",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "maxlength": "6",
            }
        ),
    )

    new_password1 = forms.CharField(
        label="Новый пароль",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "autocomplete": "new-password",
            }
        ),
    )

    new_password2 = forms.CharField(
        label="Повторите новый пароль",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "autocomplete": "new-password",
            }
        ),
    )

    def clean_code(self):
        code = self.cleaned_data["code"]

        if (
            len(code) != 6
            or not code.isascii()
            or not code.isdigit()
        ):
            raise forms.ValidationError(
                "Введите шестизначный цифровой код."
            )

        return code

    def clean(self):

        cleaned_data = super().clean()

        password1 = cleaned_data.get(
            "new_password1"
        )

        password2 = cleaned_data.get(
            "new_password2"
        )

        if (
                password1
                and password2
                and password1 != password2
        ):
            self.add_error(
                "new_password2",
                "Пароли не совпадают.",
            )

        return cleaned_data

