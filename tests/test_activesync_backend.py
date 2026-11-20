
import base64
import urllib.error
import urllib.parse

from email import policy
from email.parser import BytesParser
from unittest.mock import MagicMock, patch

import pytest

from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage

from apps.notifications.backends.activesync import (
    ActiveSyncEmailBackend,
    ActiveSyncError,
)


@pytest.fixture(autouse=True)
def activesync_settings(settings):
    settings.ACTIVESYNC_URL = (
        "https://mail.example.com/Microsoft-Server-ActiveSync"
    )
    settings.ACTIVESYNC_USERNAME = r"DOMAIN\cpservice"
    settings.ACTIVESYNC_PASSWORD = "test-password"
    settings.ACTIVESYNC_SENDER_EMAIL = "cpservice@example.com"
    settings.ACTIVESYNC_PROTOCOL_VERSION = "12.1"
    settings.ACTIVESYNC_DEVICE_ID = "PortalTest001"
    settings.ACTIVESYNC_DEVICE_TYPE = "LeovitPortal"
    settings.ACTIVESYNC_TIMEOUT = 30
    settings.ACTIVESYNC_SAVE_IN_SENT = False


@pytest.fixture
def message():
    return EmailMessage(
        subject="Тестовое письмо",
        body="Проверка почтового backend.",
        from_email="Leovit Portal <cpservice@example.com>",
        to=["employee@example.com"],
    )


@pytest.fixture
def mock_opener():
    with patch(
        "apps.notifications.backends.activesync."
        "urllib.request.build_opener"
    ) as builder:

        opener = builder.return_value

        response = MagicMock()
        response.status = 200
        response.read.return_value = b""

        opener.open.return_value.__enter__.return_value = (
            response
        )

        yield opener, response


def test_successful_send(message, mock_opener):
    backend = ActiveSyncEmailBackend()

    assert backend.send_messages([message]) == 1

    opener, _ = mock_opener
    opener.open.assert_called_once()


def test_request_parameters(message, mock_opener):
    backend = ActiveSyncEmailBackend()
    backend.send_messages([message])

    opener, _ = mock_opener
    request = opener.open.call_args.args[0]

    parsed = urllib.parse.urlsplit(request.full_url)

    params = urllib.parse.parse_qs(
        parsed.query,
        keep_blank_values=True,
    )

    assert parsed.scheme == "https"
    assert request.get_method() == "POST"
    assert params["Cmd"] == ["SendMail"]
    assert params["User"] == [r"DOMAIN\cpservice"]
    assert params["DeviceId"] == ["PortalTest001"]
    assert params["DeviceType"] == ["LeovitPortal"]
    assert "SaveInSent" not in params


def test_authorization_header(message, mock_opener):
    backend = ActiveSyncEmailBackend()
    backend.send_messages([message])

    opener, _ = mock_opener
    request = opener.open.call_args.args[0]

    expected = base64.b64encode(
        b"DOMAIN\\cpservice:test-password"
    ).decode("ascii")

    assert request.get_header(
        "Authorization"
    ) == f"Basic {expected}"


def test_protocol_headers(message, mock_opener):
    backend = ActiveSyncEmailBackend()
    backend.send_messages([message])

    opener, _ = mock_opener
    request = opener.open.call_args.args[0]

    headers = {
        key.lower(): value
        for key, value in request.header_items()
    }

    assert headers["ms-asprotocolversion"] == "12.1"
    assert headers["content-type"] == "message/rfc822"


def test_mime_message(message, mock_opener):
    backend = ActiveSyncEmailBackend()
    backend.send_messages([message])

    opener, _ = mock_opener
    request = opener.open.call_args.args[0]

    parsed_message = BytesParser(
        policy=policy.default
    ).parsebytes(request.data)

    assert parsed_message["Subject"] == "Тестовое письмо"
    assert parsed_message["To"] == "employee@example.com"
    assert "cpservice@example.com" in str(
        parsed_message["From"]
    )
    assert "Проверка почтового backend." in (
        parsed_message.get_content()
    )


def test_no_recipients(mock_opener):
    message = EmailMessage(
        subject="Test",
        body="Test",
        to=[],
    )

    backend = ActiveSyncEmailBackend()

    assert backend.send_messages([message]) == 0

    opener, _ = mock_opener
    opener.open.assert_not_called()


def test_empty_message_list():
    backend = ActiveSyncEmailBackend()

    assert backend.send_messages([]) == 0


def test_http_error(message, mock_opener):
    opener, _ = mock_opener

    opener.open.side_effect = urllib.error.HTTPError(
        url="https://mail.example.com",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=None,
    )

    backend = ActiveSyncEmailBackend()

    with pytest.raises(ActiveSyncError, match="401"):
        backend.send_messages([message])


def test_fail_silently(message, mock_opener):
    opener, _ = mock_opener

    opener.open.side_effect = urllib.error.URLError(
        "Connection failed"
    )

    backend = ActiveSyncEmailBackend(
        fail_silently=True,
    )

    assert backend.send_messages([message]) == 0


def test_unexpected_response_body(message, mock_opener):
    _, response = mock_opener
    response.read.return_value = b"Unexpected data"

    backend = ActiveSyncEmailBackend()

    with pytest.raises(ActiveSyncError):
        backend.send_messages([message])


def test_https_required(settings):
    settings.ACTIVESYNC_URL = "http://mail.example.com"

    with pytest.raises(ImproperlyConfigured):
        ActiveSyncEmailBackend()


def test_password_required(settings):
    settings.ACTIVESYNC_PASSWORD = ""

    with pytest.raises(ImproperlyConfigured):
        ActiveSyncEmailBackend()


def test_sender_must_match_service_account(
    message,
    mock_opener,
):
    message.from_email = "another@example.com"

    backend = ActiveSyncEmailBackend()

    with pytest.raises(ActiveSyncError):
        backend.send_messages([message])

    opener, _ = mock_opener
    opener.open.assert_not_called()


def test_bcc_not_supported(message, mock_opener):
    message.bcc = ["hidden@example.com"]

    backend = ActiveSyncEmailBackend()

    with pytest.raises(ActiveSyncError):
        backend.send_messages([message])

    opener, _ = mock_opener
    opener.open.assert_not_called()


def test_multiple_messages(message, mock_opener):
    backend = ActiveSyncEmailBackend()

    result = backend.send_messages([
        message,
        message,
        message,
    ])

    assert result == 3

    opener, _ = mock_opener
    assert opener.open.call_count == 3


def test_connection_cleanup(message, mock_opener):
    backend = ActiveSyncEmailBackend()
    backend.send_messages([message])

    opener, _ = mock_opener
    opener.close.assert_called_once()

    assert backend.opener is None



def test_save_in_sent_is_disabled_by_default(
    activesync_settings,
):

    from urllib.parse import (
        parse_qs,
        urlsplit,
    )

    from apps.notifications.backends.activesync import (
        ActiveSyncEmailBackend,
    )

    backend = ActiveSyncEmailBackend()

    params = parse_qs(
        urlsplit(
            backend._build_url(),
        ).query,
        keep_blank_values=True,
    )

    assert "SaveInSent" not in params


def test_save_in_sent_can_be_enabled(
    activesync_settings,
    settings,
):

    from urllib.parse import (
        parse_qs,
        urlsplit,
    )

    from apps.notifications.backends.activesync import (
        ActiveSyncEmailBackend,
    )

    settings.ACTIVESYNC_SAVE_IN_SENT = True

    backend = ActiveSyncEmailBackend()

    params = parse_qs(
        urlsplit(
            backend._build_url(),
        ).query,
        keep_blank_values=True,
    )

    assert params["SaveInSent"] == [""]
