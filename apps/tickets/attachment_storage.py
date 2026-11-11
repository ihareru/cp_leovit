from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.functional import LazyObject


class PrivateTicketStorage(LazyObject):
    def _setup(self):
        self._wrapped = FileSystemStorage(
            location=settings.PRIVATE_UPLOAD_ROOT,
            base_url=None,
        )


private_ticket_storage = PrivateTicketStorage()
