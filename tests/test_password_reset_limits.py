
import pytest

from django.test import RequestFactory

from apps.accounts.password_reset_limits import (
    MAX_REQUESTS_PER_EMAIL,
    MAX_REQUESTS_PER_IP,
    check_reset_request_limits,
    get_client_ip,
    make_cache_key,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def factory():
    return RequestFactory()


def test_get_client_ip(factory):

    request = factory.post(
        "/accounts/password-reset/",
        REMOTE_ADDR="192.168.1.100",
    )

    assert get_client_ip(request) == (
        "192.168.1.100"
    )


def test_forwarded_ip_is_ignored(factory):

    request = factory.post(
        "/accounts/password-reset/",
        REMOTE_ADDR="192.168.1.100",
        HTTP_X_FORWARDED_FOR="8.8.8.8",
        HTTP_X_REAL_IP="1.1.1.1",
    )

    assert get_client_ip(request) == (
        "192.168.1.100"
    )


def test_cache_key_does_not_contain_raw_email():

    email = "employee@example.com"

    key = make_cache_key(
        "email",
        email,
    )

    assert email not in key

    assert key.startswith(
        "password_reset:email:"
    )


def test_email_requests_within_limit(factory):

    request = factory.post(
        "/accounts/password-reset/",
        REMOTE_ADDR="192.168.1.100",
    )

    for _ in range(MAX_REQUESTS_PER_EMAIL):

        assert check_reset_request_limits(
            request,
            "employee@example.com",
        ) is True


def test_email_request_limit_exceeded(factory):

    request = factory.post(
        "/accounts/password-reset/",
        REMOTE_ADDR="192.168.1.100",
    )

    for _ in range(MAX_REQUESTS_PER_EMAIL):

        assert check_reset_request_limits(
            request,
            "employee@example.com",
        ) is True

    assert check_reset_request_limits(
        request,
        "employee@example.com",
    ) is False


def test_ip_request_limit_exceeded(factory):

    request = factory.post(
        "/accounts/password-reset/",
        REMOTE_ADDR="192.168.1.100",
    )

    for index in range(MAX_REQUESTS_PER_IP):

        assert check_reset_request_limits(
            request,
            f"employee{index}@example.com",
        ) is True

    assert check_reset_request_limits(
        request,
        "another@example.com",
    ) is False
