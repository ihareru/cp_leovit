
import base64
import logging
import ssl
import urllib.error
import urllib.parse
import urllib.request

from email.utils import getaddresses

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend


logger = logging.getLogger(__name__)


class ActiveSyncError(Exception):
    """Ошибка отправки письма через ActiveSync."""


class NoRedirectHandler(
    urllib.request.HTTPRedirectHandler
):
    """Запрещает перенаправление запросов с авторизацией."""

    def redirect_request(
        self,
        req,
        fp,
        code,
        msg,
        headers,
        newurl,
    ):
        return None


class ActiveSyncEmailBackend(BaseEmailBackend):

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(
            fail_silently=fail_silently,
            **kwargs,
        )

        self.url = settings.ACTIVESYNC_URL
        self.username = settings.ACTIVESYNC_USERNAME
        self.password = settings.ACTIVESYNC_PASSWORD

        self.protocol_version = (
            settings.ACTIVESYNC_PROTOCOL_VERSION
        )

        self.device_id = settings.ACTIVESYNC_DEVICE_ID
        self.device_type = settings.ACTIVESYNC_DEVICE_TYPE
        self.timeout = settings.ACTIVESYNC_TIMEOUT

        self.sender = settings.ACTIVESYNC_SENDER_EMAIL

        self._validate_settings()

        self.opener = None

        self.save_in_sent = settings.ACTIVESYNC_SAVE_IN_SENT

    def _validate_settings(self):
        if not self.url:
            raise ImproperlyConfigured(
                "ACTIVESYNC_URL is not configured."
            )

        parsed_url = urllib.parse.urlsplit(self.url)

        if (
            parsed_url.scheme != "https"
            or not parsed_url.hostname
            or parsed_url.username
            or parsed_url.password
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise ImproperlyConfigured(
                "ActiveSync requires a valid HTTPS URL."
            )

        if not self.username:
            raise ImproperlyConfigured(
                "ACTIVESYNC_USERNAME is not configured."
            )

        if not self.password:
            raise ImproperlyConfigured(
                "ACTIVESYNC_PASSWORD is not configured."
            )

        if not self.sender:
            raise ImproperlyConfigured(
                "ACTIVESYNC_SENDER_EMAIL is not configured."
            )

        if self.protocol_version not in ("12.0", "12.1"):
            raise ImproperlyConfigured(
                "Unsupported ActiveSync protocol version."
            )

        if self.timeout <= 0:
            raise ImproperlyConfigured(
                "ACTIVESYNC_TIMEOUT must be positive."
            )

        if (
            not self.device_id
            or not self.device_id.isascii()
            or not self.device_id.isalnum()
            or len(self.device_id) > 32
        ):
            raise ImproperlyConfigured(
                "Invalid ActiveSync Device ID."
            )

    def open(self):
        if self.opener is not None:
            return False

        context = ssl.create_default_context()

        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(
                context=context,
            ),
            NoRedirectHandler(),
        )

        return True

    def close(self):
        if self.opener is not None:
            self.opener.close()
            self.opener = None

    def _build_url(self):

        params = {
            "Cmd": "SendMail",
            "User": self.username,
            "DeviceId": self.device_id,
            "DeviceType": self.device_type,
        }

        if self.save_in_sent:
            params["SaveInSent"] = ""

        encoded_params = urllib.parse.urlencode(
            params,
        )

        return f"{self.url}?{encoded_params}"

    def _build_headers(self):
        credentials = base64.b64encode(
            f"{self.username}:{self.password}".encode(
                "utf-8"
            )
        ).decode("ascii")

        return {
            "Authorization": f"Basic {credentials}",
            "MS-ASProtocolVersion": (
                self.protocol_version
            ),
            "Content-Type": "message/rfc822",
            "User-Agent": "LeovitPortal/1.0",
        }

    def _send(self, email_message):
        if not email_message.recipients():
            return False

        mime_message = email_message.message()

        sender_addresses = getaddresses(
            mime_message.get_all("From", [])
        )

        if (
            len(sender_addresses) != 1
            or sender_addresses[0][1].casefold()
            != self.sender.casefold()
        ):
            raise ActiveSyncError(
                "Sender must match the service mailbox."
            )

        # ActiveSync 12.1 получает адреса получателей
        # непосредственно из MIME-сообщения.
        if email_message.bcc:
            raise ActiveSyncError(
                "BCC is not supported by this backend."
            )

        request = urllib.request.Request(
            url=self._build_url(),
            data=mime_message.as_bytes(linesep="\r\n"),
            headers=self._build_headers(),
            method="POST",
        )

        try:
            with self.opener.open(
                request,
                timeout=self.timeout,
            ) as response:

                status = response.status
                body = response.read()

                if status != 200:
                    raise ActiveSyncError(
                        f"Unexpected HTTP status: {status}"
                    )

                if body:
                    raise ActiveSyncError(
                        "Unexpected ActiveSync response body."
                    )

        except urllib.error.HTTPError as exc:
            exc.close()

            raise ActiveSyncError(
                f"ActiveSync HTTP error: {exc.code}"
            ) from exc

        except (OSError, urllib.error.URLError) as exc:
            raise ActiveSyncError(
                "ActiveSync connection failed."
            ) from exc

        return True

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent_count = 0
        opened = False

        try:
            opened = self.open()

            for email_message in email_messages:
                try:
                    if self._send(email_message):
                        sent_count += 1

                except Exception:
                    logger.error(
                        "ActiveSync email sending failed."
                    )

                    if not self.fail_silently:
                        raise

            return sent_count

        finally:
            if opened:
                self.close()
