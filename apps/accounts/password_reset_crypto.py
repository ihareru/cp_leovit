
import hashlib
import hmac
import re

from django.conf import settings
from django.contrib.auth.hashers import (
    check_password,
    make_password,
)
from django.core.exceptions import ImproperlyConfigured


HASH_VERSION = "v1"


def get_reset_secret():
    """
    Получение отдельного секретного ключа
    для кодов восстановления пароля.
    """

    value = getattr(
        settings,
        "PASSWORD_RESET_SECRET_KEY",
        "",
    )

    if (
        not isinstance(value, str)
        or re.fullmatch(
            r"[0-9a-fA-F]{64}",
            value,
        ) is None
    ):
        raise ImproperlyConfigured(
            "PASSWORD_RESET_SECRET_KEY must be "
            "a 64-character hexadecimal string."
        )

    return bytes.fromhex(value)


def is_valid_code_format(code):
    """
    Проверка формата шестизначного кода.
    """

    return (
        isinstance(code, str)
        and len(code) == 6
        and code.isascii()
        and code.isdigit()
    )


def derive_reset_code(user_id, code):
    """
    Криптографическое преобразование кода
    с привязкой к пользователю.
    """

    if not is_valid_code_format(code):
        raise ValueError(
            "Invalid password reset code format."
        )

    secret = get_reset_secret()

    payload = (
        f"password-reset:{HASH_VERSION}:"
        f"{user_id}:{code}"
    ).encode("utf-8")

    return hmac.new(
        secret,
        payload,
        hashlib.sha256,
    ).hexdigest()


def hash_reset_code(user_id, code):
    """
    Создание защищённого хеша кода восстановления.
    """

    derived_code = derive_reset_code(
        user_id,
        code,
    )

    encoded = make_password(derived_code)

    return f"{HASH_VERSION}${encoded}"


def verify_reset_code(user_id, code, encoded):
    """
    Проверка кода восстановления.
    """

    if not is_valid_code_format(code):
        return False

    if not isinstance(encoded, str):
        return False

    version, separator, password_hash = (
        encoded.partition("$")
    )

    if (
        not separator
        or version != HASH_VERSION
        or not password_hash
    ):
        return False

    derived_code = derive_reset_code(
        user_id,
        code,
    )

    return check_password(
        derived_code,
        password_hash,
    )
