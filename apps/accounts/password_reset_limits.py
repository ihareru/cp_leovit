
import hashlib
import hmac
from django.conf import settings
from .client_ip import get_client_ip
import logging

from datetime import timedelta

from django.db import (
    DatabaseError,
    connection,
    transaction,
)

from django.utils import timezone

from .password_reset_crypto import get_reset_secret

from .password_reset_rate_models import (
    PasswordResetRateLimit,
)


logger = logging.getLogger(__name__)


WINDOW_SECONDS = 15 * 60

MAX_REQUESTS_PER_IP = 20
MAX_REQUESTS_PER_EMAIL = 5


def make_cache_key(kind, value):
    """
    Формирование защищённого идентификатора.

    Название функции сохранено для совместимости
    с существующими тестами.
    """

    payload = (
        f"password-reset-rate:{kind}:{value}"
    ).encode("utf-8")

    digest = hmac.new(
        get_reset_secret(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return f"password_reset:{kind}:{digest}"


def increment_counter(key):
    """
    Атомарное увеличение счётчика PostgreSQL.

    Если запись отсутствует, создаётся новая.

    Если период ограничения истёк,
    начинается новый период со значения 1.
    """

    now = timezone.now()

    expires_at = now + timedelta(
        seconds=WINDOW_SECONDS,
    )

    table_name = connection.ops.quote_name(
        PasswordResetRateLimit._meta.db_table
    )

    sql = f"""
        INSERT INTO {table_name} AS rate_limit
            (
                key,
                count,
                expires_at,
                updated_at
            )
        VALUES
            (%s, 1, %s, %s)

        ON CONFLICT (key)
        DO UPDATE SET

            count = CASE
                WHEN rate_limit.expires_at
                    <= EXCLUDED.updated_at
                THEN 1
                ELSE rate_limit.count + 1
            END,

            expires_at = CASE
                WHEN rate_limit.expires_at
                    <= EXCLUDED.updated_at
                THEN EXCLUDED.expires_at
                ELSE rate_limit.expires_at
            END,

            updated_at = GREATEST(
                rate_limit.updated_at,
                EXCLUDED.updated_at
            )

        RETURNING count
    """

    with connection.cursor() as cursor:

        cursor.execute(
            sql,
            [
                key,
                expires_at,
                now,
            ],
        )

        result = cursor.fetchone()

    return result[0]


def check_reset_request_limits(request, email):
    """
    Проверка ограничений восстановления пароля.

    Оба счётчика обновляются в одной транзакции.
    При недоступности БД запрос блокируется.
    """

    ip = get_client_ip(request)

    normalized_email = email.strip().lower()

    ip_key = make_cache_key(
        "ip",
        ip,
    )

    email_key = make_cache_key(
        "email",
        normalized_email,
    )

    try:
        with transaction.atomic():

            ip_count = increment_counter(
                ip_key,
            )

            # Не создаём новые email-счётчики,
            # если IP уже превысил ограничение.
            if ip_count > MAX_REQUESTS_PER_IP:
                allowed = False

            else:
                email_count = increment_counter(
                    email_key,
                )

                allowed = (
                    email_count
                    <= MAX_REQUESTS_PER_EMAIL
                )

    except DatabaseError:

        logger.error(
            "Password reset rate limit database error"
        )

        return False

    if not allowed:

        logger.warning(
            "Password reset rate limit exceeded"
        )

    return allowed



def check_reset_confirm_limits(request, email):
    """
    Ограничение количества попыток подтверждения
    восстановления пароля.

    Счётчики независимы от отправки кодов.
    """

    ip = get_client_ip(request)

    normalized_email = email.strip().lower()

    ip_key = make_cache_key(
        "confirm_ip",
        ip,
    )

    email_key = make_cache_key(
        "confirm_email",
        normalized_email,
    )

    max_per_ip = (
        settings
        .PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_IP
    )

    max_per_email = (
        settings
        .PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_EMAIL
    )

    try:
        with transaction.atomic():

            ip_count = increment_counter(
                ip_key,
            )

            if ip_count > max_per_ip:

                allowed = False

            else:

                email_count = increment_counter(
                    email_key,
                )

                allowed = (
                    email_count <= max_per_email
                )

    except DatabaseError:

        logger.error(
            "Password reset confirmation "
            "rate limit database error"
        )

        return False

    if not allowed:

        logger.warning(
            "Password reset confirmation "
            "rate limit exceeded"
        )

    return allowed
