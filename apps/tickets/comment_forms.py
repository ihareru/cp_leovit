from django import forms

from .models import TicketComment
from .attachment_forms import (
    MultipleFileField,
    MultipleFileInput,
)

class TicketCommentForm(forms.ModelForm):
    
    files = MultipleFileField(
        label="Файлы к комментарию",
        required=False,
        widget=MultipleFileInput(
            attrs={
                "class": "form-control",
                "accept": (
                    ".pdf,.jpg,.jpeg,.png,"
                    ".docx,.xlsx,.txt,.zip"
                ),
            }
        ),
    )

    class Meta:
        model = TicketComment
        fields = ["text"]

        widgets = {
            "text": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "maxlength": 5000,
                    "placeholder": (
                        "Напишите комментарий к заявке..."
                    ),
                }
            ),
        }

        labels = {
            "text": "Комментарий",
        }

    def clean_text(self):
        text = self.cleaned_data["text"].strip()

        if not text:
            raise forms.ValidationError(
                "Введите текст комментария."
            )

        return text
