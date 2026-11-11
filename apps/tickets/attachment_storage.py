import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateTicketStorage(FileSystemStorage):
    def __init__(self):
        super().__init__(
            location=None,
            base_url=None,
        )

    @property
    def base_location(self):
        return str(settings.PRIVATE_UPLOAD_ROOT)

    @property
    def location(self):
        return os.path.abspath(self.base_location)


private_ticket_storage = PrivateTicketStorage()
