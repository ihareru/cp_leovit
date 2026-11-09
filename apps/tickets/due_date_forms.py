from django import forms


class TicketDueDateForm(forms.Form):

    new_due_date = forms.DateField(
        label="Новый срок выполнения",
        required=False,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={
                "class": "form-control",
                "type": "date",
            },
        ),
    )

    reason = forms.CharField(
        label="Причина изменения",
        required=True,
        max_length=2000,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Укажите причину изменения срока",
            }
        ),
    )

    def clean_reason(self):
        reason = self.cleaned_data["reason"].strip()

        if not reason:
            raise forms.ValidationError(
                "Укажите причину изменения срока."
            )

        return reason
