
import pytest

from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory

from apps.accounts.client_ip import (
    get_client_ip,
    get_trusted_proxy_networks,
)


@pytest.fixture
def factory():
    return RequestFactory()


def test_direct_client_ip(factory):

    request = factory.get(
        "/",
        REMOTE_ADDR="192.168.1.50",
    )

    assert get_client_ip(request) == (
        "192.168.1.50"
    )


def test_untrusted_real_ip_is_ignored(factory):

    request = factory.get(
        "/",
        REMOTE_ADDR="192.168.1.50",
        HTTP_X_REAL_IP="8.8.8.8",
    )

    assert get_client_ip(request) == (
        "192.168.1.50"
    )


def test_trusted_proxy_real_ip(
    factory,
    settings,
):

    settings.PASSWORD_RESET_TRUSTED_PROXY_NETWORKS = [
        "127.0.0.1/32"
    ]

    request = factory.get(
        "/",
        REMOTE_ADDR="127.0.0.1",
        HTTP_X_REAL_IP="192.168.1.50",
    )

    assert get_client_ip(request) == (
        "192.168.1.50"
    )


def test_trusted_proxy_without_header(
    factory,
    settings,
):

    settings.PASSWORD_RESET_TRUSTED_PROXY_NETWORKS = [
        "127.0.0.1/32"
    ]

    request = factory.get(
        "/",
        REMOTE_ADDR="127.0.0.1",
    )

    assert get_client_ip(request) == "unknown"


def test_invalid_real_ip_is_rejected(
    factory,
    settings,
):

    settings.PASSWORD_RESET_TRUSTED_PROXY_NETWORKS = [
        "127.0.0.1/32"
    ]

    request = factory.get(
        "/",
        REMOTE_ADDR="127.0.0.1",
        HTTP_X_REAL_IP="invalid-address",
    )

    assert get_client_ip(request) == "unknown"


def test_multiple_real_ip_addresses_are_rejected(
    factory,
    settings,
):

    settings.PASSWORD_RESET_TRUSTED_PROXY_NETWORKS = [
        "127.0.0.1/32"
    ]

    request = factory.get(
        "/",
        REMOTE_ADDR="127.0.0.1",
        HTTP_X_REAL_IP="8.8.8.8, 1.1.1.1",
    )

    assert get_client_ip(request) == "unknown"


def test_forwarded_for_is_ignored(
    factory,
    settings,
):

    settings.PASSWORD_RESET_TRUSTED_PROXY_NETWORKS = [
        "127.0.0.1/32"
    ]

    request = factory.get(
        "/",
        REMOTE_ADDR="127.0.0.1",
        HTTP_X_REAL_IP="192.168.1.50",
        HTTP_X_FORWARDED_FOR="8.8.8.8",
    )

    assert get_client_ip(request) == (
        "192.168.1.50"
    )


def test_ipv6_address(factory):

    request = factory.get(
        "/",
        REMOTE_ADDR="2001:db8::10",
    )

    assert get_client_ip(request) == (
        "2001:db8::10"
    )


def test_ipv4_mapped_ipv6(factory):

    request = factory.get(
        "/",
        REMOTE_ADDR="::ffff:192.168.1.50",
    )

    assert get_client_ip(request) == (
        "192.168.1.50"
    )


def test_invalid_remote_address(factory):

    request = factory.get(
        "/",
        REMOTE_ADDR="invalid",
        HTTP_X_REAL_IP="8.8.8.8",
    )

    assert get_client_ip(request) == "unknown"


def test_invalid_proxy_network(settings):

    settings.PASSWORD_RESET_TRUSTED_PROXY_NETWORKS = [
        "invalid-network"
    ]

    with pytest.raises(ImproperlyConfigured):

        get_trusted_proxy_networks()


def test_trusting_all_networks_is_forbidden(settings):

    for value in (
        "0.0.0.0/0",
        "::/0",
    ):

        settings.PASSWORD_RESET_TRUSTED_PROXY_NETWORKS = [
            value
        ]

        with pytest.raises(ImproperlyConfigured):

            get_trusted_proxy_networks()
