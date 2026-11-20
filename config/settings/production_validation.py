
import ipaddress
import re

from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


ACTIVESYNC_BACKEND = (
    "apps.notifications.backends.activesync."
    "ActiveSyncEmailBackend"
)


def require(condition, message):

    if not condition:

        raise ImproperlyConfigured(message)


def validate_positive_integer(config, name):

    value = config.get(name)

    require(
        isinstance(value, int)
        and not isinstance(value, bool)
        and value > 0,
        f"{name} must be a positive integer.",
    )


def validate_secret_keys(config):

    secret_key = config.get(
        "SECRET_KEY",
        "",
    )

    reset_secret = config.get(
        "PASSWORD_RESET_SECRET_KEY",
        "",
    )

    require(
        isinstance(secret_key, str)
        and len(secret_key) >= 50
        and len(set(secret_key)) >= 5
        and not secret_key.startswith("django-insecure-"),
        "Production SECRET_KEY is missing or insecure.",
    )

    require(
        isinstance(reset_secret, str)
        and re.fullmatch(
            r"[0-9a-fA-F]{64}",
            reset_secret,
        ) is not None,
        (
            "PASSWORD_RESET_SECRET_KEY must be "
            "a 64-character hexadecimal string."
        ),
    )

    require(
        len(set(reset_secret.lower())) >= 5,
        "PASSWORD_RESET_SECRET_KEY is insecure.",
    )

    require(
        secret_key.lower() != reset_secret.lower(),
        (
            "SECRET_KEY and PASSWORD_RESET_SECRET_KEY "
            "must be different."
        ),
    )


def validate_web_security(config):

    require(
        config.get("DEBUG") is False,
        "DEBUG must be False in production.",
    )

    allowed_hosts = config.get(
        "ALLOWED_HOSTS",
        [],
    )

    require(
        isinstance(allowed_hosts, (list, tuple))
        and bool(allowed_hosts),
        "ALLOWED_HOSTS must not be empty.",
    )

    for host in allowed_hosts:

        require(
            isinstance(host, str)
            and bool(host.strip())
            and "*" not in host
            and not host.startswith(".")
            and "://" not in host,
            "ALLOWED_HOSTS contains an unsafe value.",
        )

    trusted_origins = config.get(
        "CSRF_TRUSTED_ORIGINS",
        [],
    )

    require(
        isinstance(trusted_origins, (list, tuple))
        and bool(trusted_origins),
        "CSRF_TRUSTED_ORIGINS must not be empty.",
    )

    for origin in trusted_origins:

        require(
            isinstance(origin, str),
            "Invalid CSRF trusted origin.",
        )

        try:

            parsed = urlsplit(origin)

            valid = (
                parsed.scheme == "https"
                and bool(parsed.hostname)
                and "*" not in origin
                and parsed.username is None
                and parsed.password is None
                and not parsed.path
                and not parsed.query
                and not parsed.fragment
            )

            # Проверяем корректность порта.
            parsed.port

        except ValueError:

            valid = False

        require(
            valid,
            "CSRF trusted origins must be HTTPS origins.",
        )

    for name in (
        "SESSION_COOKIE_SECURE",
        "SESSION_COOKIE_HTTPONLY",
        "CSRF_COOKIE_SECURE",
        "SECURE_SSL_REDIRECT",
        "SECURE_CONTENT_TYPE_NOSNIFF",
    ):

        require(
            config.get(name) is True,
            f"{name} must be True in production.",
        )

    require(
        config.get("SESSION_COOKIE_SAMESITE")
        in ("Lax", "Strict"),
        "Unsafe SESSION_COOKIE_SAMESITE setting.",
    )

    require(
        config.get("CSRF_COOKIE_SAMESITE")
        in ("Lax", "Strict"),
        "Unsafe CSRF_COOKIE_SAMESITE setting.",
    )

    hsts_seconds = config.get(
        "SECURE_HSTS_SECONDS",
        0,
    )

    require(
        isinstance(hsts_seconds, int)
        and not isinstance(hsts_seconds, bool)
        and hsts_seconds >= 3600,
        "SECURE_HSTS_SECONDS must be at least 3600.",
    )


def validate_database(config):

    databases = config.get(
        "DATABASES",
        {},
    )

    default_database = databases.get(
        "default",
        {},
    )

    require(
        default_database.get("ENGINE")
        == "django.db.backends.postgresql",
        "Production requires PostgreSQL.",
    )


def validate_trusted_proxies(config):

    networks = config.get(
        "PASSWORD_RESET_TRUSTED_PROXY_NETWORKS",
        [],
    )

    require(
        isinstance(networks, (list, tuple))
        and bool(networks),
        "Trusted proxy networks must be configured.",
    )

    for value in networks:

        try:

            network = ipaddress.ip_network(
                value.strip(),
                strict=True,
            )

        except (ValueError, AttributeError) as exc:

            raise ImproperlyConfigured(
                "Invalid trusted proxy network."
            ) from exc

        require(
            network.prefixlen
            == network.max_prefixlen,
            (
                "Production trusted proxies must "
                "use individual IP addresses."
            ),
        )

    require(
        config.get("SECURE_PROXY_SSL_HEADER")
        == (
            "HTTP_X_FORWARDED_PROTO",
            "https",
        ),
        "Invalid SECURE_PROXY_SSL_HEADER.",
    )


def validate_email_configuration(config):

    require(
        config.get("EMAIL_BACKEND")
        == ACTIVESYNC_BACKEND,
        "Production requires the ActiveSync email backend.",
    )

    url = config.get(
        "ACTIVESYNC_URL",
        "",
    )

    try:

        parsed = urlsplit(url)

        valid = (
            parsed.scheme == "https"
            and parsed.hostname == "mail.leovit.ru"
            and parsed.port in (None, 443)
            and parsed.username is None
            and parsed.password is None
            and not parsed.query
            and not parsed.fragment
            and parsed.path.rstrip("/")
            == "/Microsoft-Server-ActiveSync"
        )

    except (ValueError, TypeError):

        valid = False

    require(
        valid,
        "Invalid production ActiveSync URL.",
    )

    for name in (
        "ACTIVESYNC_USERNAME",
        "ACTIVESYNC_PASSWORD",
        "ACTIVESYNC_SENDER_EMAIL",
        "DEFAULT_FROM_EMAIL",
    ):

        value = config.get(name)

        require(
            isinstance(value, str)
            and bool(value.strip()),
            f"{name} must be configured.",
        )

    sender = config["ACTIVESYNC_SENDER_EMAIL"]

    try:

        validate_email(sender)

    except ValidationError as exc:

        raise ImproperlyConfigured(
            "Invalid ActiveSync sender email."
        ) from exc

    require(
        sender.casefold() == "cpservice@leovit.ru",
        "Unexpected production ActiveSync sender.",
    )

    from email.utils import getaddresses

    from_addresses = getaddresses(
        [config["DEFAULT_FROM_EMAIL"]]
    )

    require(
        len(from_addresses) == 1
        and from_addresses[0][1].casefold()
        == sender.casefold(),
        (
            "DEFAULT_FROM_EMAIL must match "
            "ACTIVESYNC_SENDER_EMAIL."
        ),
    )

    require(
        config.get("ACTIVESYNC_PROTOCOL_VERSION")
        in ("12.0", "12.1"),
        "Unsupported ActiveSync protocol version.",
    )

    device_id = config.get(
        "ACTIVESYNC_DEVICE_ID",
        "",
    )

    require(
        isinstance(device_id, str)
        and bool(device_id)
        and device_id.isascii()
        and device_id.isalnum()
        and len(device_id) <= 32,
        "Invalid ActiveSync Device ID.",
    )

    device_type = config.get(
        "ACTIVESYNC_DEVICE_TYPE",
        "",
    )

    require(
        isinstance(device_type, str)
        and bool(device_type.strip()),
        "ACTIVESYNC_DEVICE_TYPE must be configured.",
    )

    validate_positive_integer(
        config,
        "ACTIVESYNC_TIMEOUT",
    )

    require(
        config.get("ACTIVESYNC_SAVE_IN_SENT") is False,
        (
            "Saving ActiveSync messages in Sent Items "
            "must be disabled in production."
        ),
    )


def validate_password_reset_configuration(config):

    for name in (
        "PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_IP",
        "PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_EMAIL",
        "PASSWORD_RESET_CODE_RETENTION_DAYS",
        "PASSWORD_RESET_RATE_LIMIT_RETENTION_HOURS",
        "PASSWORD_RESET_CLEANUP_BATCH_SIZE",
    ):

        validate_positive_integer(
            config,
            name,
        )


def validate_production_settings(config):

    validate_secret_keys(config)

    validate_web_security(config)

    validate_database(config)

    validate_trusted_proxies(config)

    validate_email_configuration(config)

    validate_password_reset_configuration(config)
