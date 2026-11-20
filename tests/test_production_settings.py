
import secrets

import pytest

from django.core.exceptions import ImproperlyConfigured

from config.settings.production_validation import (
    validate_production_settings,
)


@pytest.fixture
def config():

    return {
        "DEBUG": False,

        "SECRET_KEY": secrets.token_urlsafe(64),

        "PASSWORD_RESET_SECRET_KEY": (
            secrets.token_hex(32)
        ),

        "ALLOWED_HOSTS": [
            "cp.leovit.ru",
        ],

        "CSRF_TRUSTED_ORIGINS": [
            "https://cp.leovit.ru",
        ],

        "SESSION_COOKIE_SECURE": True,

        "SESSION_COOKIE_HTTPONLY": True,

        "SESSION_COOKIE_SAMESITE": "Lax",

        "CSRF_COOKIE_SECURE": True,

        "CSRF_COOKIE_SAMESITE": "Lax",

        "SECURE_SSL_REDIRECT": True,

        "SECURE_CONTENT_TYPE_NOSNIFF": True,

        "SECURE_HSTS_SECONDS": 3600,

        "SECURE_PROXY_SSL_HEADER": (
            "HTTP_X_FORWARDED_PROTO",
            "https",
        ),

        "PASSWORD_RESET_TRUSTED_PROXY_NETWORKS": [
            "127.0.0.1/32",
        ],

        "DATABASES": {
            "default": {
                "ENGINE": (
                    "django.db.backends.postgresql"
                ),
            },
        },

        "EMAIL_BACKEND": (
            "apps.notifications.backends.activesync."
            "ActiveSyncEmailBackend"
        ),

        "ACTIVESYNC_URL": (
            "https://mail.leovit.ru/"
            "Microsoft-Server-ActiveSync"
        ),

        "ACTIVESYNC_USERNAME": (
            r"LEOVIT\cpservice"
        ),

        "ACTIVESYNC_PASSWORD": "test-password",

        "ACTIVESYNC_SENDER_EMAIL": (
            "cpservice@leovit.ru"
        ),

        "DEFAULT_FROM_EMAIL": (
            "Leovit Portal <cpservice@leovit.ru>"
        ),

        "ACTIVESYNC_PROTOCOL_VERSION": "12.1",

        "ACTIVESYNC_DEVICE_ID": (
            "LeovitPortalProd001"
        ),

        "ACTIVESYNC_DEVICE_TYPE": "LeovitPortal",

        "ACTIVESYNC_TIMEOUT": 30,

        "ACTIVESYNC_SAVE_IN_SENT": False,

        "PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_IP": 100,

        "PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_EMAIL": 15,

        "PASSWORD_RESET_CODE_RETENTION_DAYS": 7,

        "PASSWORD_RESET_RATE_LIMIT_RETENTION_HOURS": 24,

        "PASSWORD_RESET_CLEANUP_BATCH_SIZE": 1000,
    }


def test_valid_production_configuration(config):

    validate_production_settings(config)


@pytest.mark.parametrize(
    "name,value",
    [
        ("DEBUG", True),

        ("SECRET_KEY", ""),

        ("SECRET_KEY", "short-key"),

        (
            "SECRET_KEY",
            "django-insecure-" + "abc123" * 15,
        ),

        (
            "PASSWORD_RESET_SECRET_KEY",
            "",
        ),

        (
            "PASSWORD_RESET_SECRET_KEY",
            "abc123",
        ),

        (
            "PASSWORD_RESET_SECRET_KEY",
            "z" * 64,
        ),

        (
            "PASSWORD_RESET_SECRET_KEY",
            "a" * 64,
        ),

        (
            "ALLOWED_HOSTS",
            [],
        ),

        (
            "ALLOWED_HOSTS",
            ["*"],
        ),

        (
            "ALLOWED_HOSTS",
            [".leovit.ru"],
        ),

        (
            "CSRF_TRUSTED_ORIGINS",
            [],
        ),

        (
            "CSRF_TRUSTED_ORIGINS",
            ["http://cp.leovit.ru"],
        ),

        (
            "CSRF_TRUSTED_ORIGINS",
            ["https://*.leovit.ru"],
        ),

        (
            "SESSION_COOKIE_SECURE",
            False,
        ),

        (
            "SESSION_COOKIE_HTTPONLY",
            False,
        ),

        (
            "SESSION_COOKIE_SAMESITE",
            "None",
        ),

        (
            "CSRF_COOKIE_SECURE",
            False,
        ),

        (
            "CSRF_COOKIE_SAMESITE",
            "None",
        ),

        (
            "SECURE_SSL_REDIRECT",
            False,
        ),

        (
            "SECURE_CONTENT_TYPE_NOSNIFF",
            False,
        ),

        (
            "SECURE_HSTS_SECONDS",
            0,
        ),

        (
            "SECURE_PROXY_SSL_HEADER",
            None,
        ),

        (
            "PASSWORD_RESET_TRUSTED_PROXY_NETWORKS",
            [],
        ),

        (
            "PASSWORD_RESET_TRUSTED_PROXY_NETWORKS",
            ["0.0.0.0/0"],
        ),

        (
            "PASSWORD_RESET_TRUSTED_PROXY_NETWORKS",
            ["192.168.1.0/24"],
        ),

        (
            "PASSWORD_RESET_TRUSTED_PROXY_NETWORKS",
            ["invalid-address"],
        ),

        (
            "EMAIL_BACKEND",
            "django.core.mail.backends.console.EmailBackend",
        ),

        (
            "EMAIL_BACKEND",
            "django.core.mail.backends.locmem.EmailBackend",
        ),

        (
            "ACTIVESYNC_URL",
            "http://mail.leovit.ru/Microsoft-Server-ActiveSync",
        ),

        (
            "ACTIVESYNC_URL",
            "https://example.com/Microsoft-Server-ActiveSync",
        ),

        (
            "ACTIVESYNC_USERNAME",
            "",
        ),

        (
            "ACTIVESYNC_PASSWORD",
            "",
        ),

        (
            "ACTIVESYNC_SENDER_EMAIL",
            "invalid-email",
        ),

        (
            "ACTIVESYNC_SENDER_EMAIL",
            "other@leovit.ru",
        ),

        (
            "DEFAULT_FROM_EMAIL",
            "other@leovit.ru",
        ),

        (
            "ACTIVESYNC_PROTOCOL_VERSION",
            "14.1",
        ),

        (
            "ACTIVESYNC_DEVICE_ID",
            "",
        ),

        (
            "ACTIVESYNC_DEVICE_ID",
            "a" * 33,
        ),

        (
            "ACTIVESYNC_DEVICE_TYPE",
            "",
        ),

        (
            "ACTIVESYNC_TIMEOUT",
            0,
        ),

        (
            "ACTIVESYNC_SAVE_IN_SENT",
            True,
        ),

        (
            "PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_IP",
            0,
        ),

        (
            "PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_EMAIL",
            -1,
        ),

        (
            "PASSWORD_RESET_CODE_RETENTION_DAYS",
            0,
        ),

        (
            "PASSWORD_RESET_RATE_LIMIT_RETENTION_HOURS",
            0,
        ),

        (
            "PASSWORD_RESET_CLEANUP_BATCH_SIZE",
            0,
        ),
    ],
)
def test_invalid_production_configuration(
    config,
    name,
    value,
):

    config[name] = value

    with pytest.raises(ImproperlyConfigured):

        validate_production_settings(config)


def test_identical_secret_keys_are_rejected(config):

    config["SECRET_KEY"] = (
        config["PASSWORD_RESET_SECRET_KEY"]
    )

    with pytest.raises(
        ImproperlyConfigured,
        match="must be different",
    ):

        validate_production_settings(config)


def test_sqlite_is_rejected(config):

    config["DATABASES"]["default"]["ENGINE"] = (
        "django.db.backends.sqlite3"
    )

    with pytest.raises(
        ImproperlyConfigured,
        match="PostgreSQL",
    ):

        validate_production_settings(config)


def test_ipv6_loopback_proxy_is_allowed(config):

    config[
        "PASSWORD_RESET_TRUSTED_PROXY_NETWORKS"
    ] = [
        "::1/128",
    ]

    validate_production_settings(config)


def test_multiple_individual_proxies_are_allowed(config):

    config[
        "PASSWORD_RESET_TRUSTED_PROXY_NETWORKS"
    ] = [
        "127.0.0.1/32",
        "::1/128",
    ]

    validate_production_settings(config)


def test_secret_is_not_exposed_in_error(config):

    secret = "private-test-password"

    config["ACTIVESYNC_PASSWORD"] = secret

    config["ACTIVESYNC_URL"] = (
        "http://mail.leovit.ru"
    )

    with pytest.raises(
        ImproperlyConfigured,
    ) as exc_info:

        validate_production_settings(config)

    assert secret not in str(exc_info.value)
