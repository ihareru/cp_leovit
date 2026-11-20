
import hashlib
import hmac
import secrets

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings

from django.contrib.auth.password_validation import (
    validate_password,
)
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare

from .password_reset_models import PasswordResetCode

from .password_reset_crypto import (
    hash_reset_code,
    verify_reset_code,
)


CODE_LIFETIME = timedelta(minutes=15)
RESEND_INTERVAL = timedelta(seconds=60)
MAX_ATTEMPTS = 5


class ResetCodeError(Exception):
    """Базовая ошибка восстановления пароля."""


class ResetCodeCooldown(ResetCodeError):
    """Повторный запрос пока недоступен."""


class ResetCodeInvalid(ResetCodeError):
    """Код недействителен."""


@dataclass(frozen=True)
class CreatedResetCode:
    code: str
    record_id: int


def normalize_email(email):
    return email.strip().lower()


def get_password_fingerprint(user):
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        (
            f"password-reset:"
            f"{user.pk}:{user.password}"
        ).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def generate_reset_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_unique_reset_code(previous_record=None):
    while True:
        code = generate_reset_code()

        if previous_record is None:
            return code

        if not verify_reset_code(
            previous_record.user_id,
            code,
            previous_record.code_hash,
        ):
            return code


@transaction.atomic
def create_reset_code_record(user):
    User = type(user)

    locked_user = (
        User.objects
        .select_for_update()
        .get(pk=user.pk)
    )

    if (
        not locked_user.is_active
        or not locked_user.email
        or normalize_email(locked_user.email)
        != normalize_email(user.email)
    ):
        raise ResetCodeInvalid(
            "Восстановление пароля недоступно."
        )

    now = timezone.now()

    latest = (
        PasswordResetCode.objects
        .filter(user=locked_user)
        .order_by("-created_at", "-pk")
        .first()
    )

    if (
        latest is not None
        and latest.created_at > now - RESEND_INTERVAL
    ):
        raise ResetCodeCooldown(
            "Повторный запрос пока недоступен."
        )

    code = generate_unique_reset_code(latest)

    PasswordResetCode.objects.filter(
        user=locked_user,
        used_at__isnull=True,
    ).update(
        used_at=now,
    )

    reset_record = PasswordResetCode.objects.create(
        user=locked_user,
        code_hash=hash_reset_code(
            locked_user.pk,
            code,
        ),
        created_at=now,
        expires_at=now + CODE_LIFETIME,
        email_at_creation=normalize_email(
            locked_user.email
        ),
        password_fingerprint=get_password_fingerprint(
            locked_user
        ),
    )

    return CreatedResetCode(
        code=code,
        record_id=reset_record.pk,
    )


def create_reset_code(user):
    return create_reset_code_record(user).code


def invalidate_reset_code(record_id):
    return PasswordResetCode.objects.filter(
        pk=record_id,
        used_at__isnull=True,
    ).update(
        used_at=timezone.now(),
    )


@transaction.atomic
def reset_password_with_code(user, code, new_password):
    User = type(user)

    locked_user = (
        User.objects
        .select_for_update()
        .get(pk=user.pk)
    )

    error_message = (
        "Неверный или недействительный код."
    )

    if not locked_user.is_active:
        raise ResetCodeInvalid(error_message)

    reset_code = (
        PasswordResetCode.objects
        .select_for_update()
        .filter(
            user=locked_user,
            used_at__isnull=True,
        )
        .order_by("-created_at", "-pk")
        .first()
    )

    now = timezone.now()

    if reset_code is None:
        raise ResetCodeInvalid(error_message)

    if (
        reset_code.expires_at <= now
        or reset_code.attempts >= MAX_ATTEMPTS
    ):
        raise ResetCodeInvalid(error_message)

    current_email = normalize_email(
        locked_user.email
    )

    current_fingerprint = get_password_fingerprint(
        locked_user
    )

    if (
        not current_email
        or current_email != normalize_email(user.email)
        or reset_code.email_at_creation != current_email
        or not constant_time_compare(
            reset_code.password_fingerprint,
            current_fingerprint,
        )
    ):
        return False

    valid = verify_reset_code(
        locked_user.pk,
        code,
        reset_code.code_hash,
    )

    if not valid:
        reset_code.attempts += 1

        reset_code.save(
            update_fields=["attempts"],
        )

        return False

    # Проверяем пароль только после проверки кода.
    validate_password(
        new_password,
        user=locked_user,
    )

    locked_user.set_password(new_password)

    locked_user.save(
        update_fields=["password"],
    )

    reset_code.used_at = now

    reset_code.save(
        update_fields=["used_at"],
    )

    return True
