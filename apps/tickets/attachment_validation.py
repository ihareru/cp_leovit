from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError


ALLOWED_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".docx",
    ".xlsx",
    ".txt",
    ".zip",
}


def validate_ticket_attachment(uploaded_file):
    if uploaded_file is None:
        raise ValidationError("Выберите файл.")

    extension = Path(uploaded_file.name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            "Недопустимый формат файла."
        )

    max_size = settings.TICKET_ATTACHMENT_MAX_SIZE

    if uploaded_file.size > max_size:
        raise ValidationError(
            "Размер файла не должен превышать 10 МБ."
        )

    if uploaded_file.size == 0:
        raise ValidationError(
            "Нельзя загрузить пустой файл."
        )

    if len(Path(uploaded_file.name).name) > 255:
        raise ValidationError(
            "Слишком длинное имя файла."
        )
