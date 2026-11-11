from django import forms

from .attachment_validation import (
    validate_ticket_attachment,
)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            if self.required:
                raise forms.ValidationError(
                    "Выберите хотя бы один файл."
                )
            return []

        files = data if isinstance(data, (list, tuple)) else [data]

        cleaned_files = []

        for uploaded_file in files:
            cleaned_file = super().clean(
                uploaded_file,
                initial,
            )

            validate_ticket_attachment(cleaned_file)
            cleaned_files.append(cleaned_file)

        return cleaned_files


class TicketAttachmentForm(forms.Form):
    # Оставляем старое поле для совместимости
    # с существующими тестами и запросами.
    file = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    files = MultipleFileField(
        label="Прикрепить файлы",
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

    def clean_file(self):
        uploaded_file = self.cleaned_data.get("file")

        if uploaded_file is not None:
            validate_ticket_attachment(uploaded_file)

        return uploaded_file

    def clean(self):
        cleaned_data = super().clean()

        files = list(cleaned_data.get("files") or [])
        single_file = cleaned_data.get("file")

        if single_file is not None:
            files.append(single_file)

        cleaned_data["all_files"] = files

        return cleaned_data
