from django import forms


class TicketCompleteForm(forms.Form):
    comment = forms.CharField(
        label="Результат выполнения",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
            }
        ),
    )


class TicketRejectForm(forms.Form):
    reason = forms.CharField(
        label="Причина отклонения",
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
            }
        ),
    )

    def clean_reason(self):
        reason = self.cleaned_data["reason"].strip()

        if not reason:
            raise forms.ValidationError(
                "Укажите причину отклонения."
            )

        return reason
