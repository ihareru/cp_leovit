
import pytest

from django.contrib.auth.hashers import (
    check_password,
    make_password,
)
from django.core.exceptions import ImproperlyConfigured

from apps.accounts.password_reset_crypto import (
    derive_reset_code,
    get_reset_secret,
    hash_reset_code,
    is_valid_code_format,
    verify_reset_code,
)


USER_ID = 100
OTHER_USER_ID = 200

CODE = "123456"
WRONG_CODE = "654321"


def test_secret_has_required_length():
    secret = get_reset_secret()

    assert isinstance(secret, bytes)
    assert len(secret) == 32


def test_correct_code_is_accepted():
    encoded = hash_reset_code(
        USER_ID,
        CODE,
    )

    assert verify_reset_code(
        USER_ID,
        CODE,
        encoded,
    )


def test_wrong_code_is_rejected():
    encoded = hash_reset_code(
        USER_ID,
        CODE,
    )

    assert not verify_reset_code(
        USER_ID,
        WRONG_CODE,
        encoded,
    )


def test_hash_is_bound_to_user():
    encoded = hash_reset_code(
        USER_ID,
        CODE,
    )

    assert not verify_reset_code(
        OTHER_USER_ID,
        CODE,
        encoded,
    )


def test_hash_contains_version():
    encoded = hash_reset_code(
        USER_ID,
        CODE,
    )

    assert encoded.startswith("v1$")
    assert len(encoded) <= 255


def test_raw_code_is_not_django_password():
    encoded = hash_reset_code(
        USER_ID,
        CODE,
    )

    password_hash = encoded.split(
        "$",
        1,
    )[1]

    assert not check_password(
        CODE,
        password_hash,
    )

    assert check_password(
        derive_reset_code(USER_ID, CODE),
        password_hash,
    )


def test_same_code_has_different_hashes():
    first = hash_reset_code(
        USER_ID,
        CODE,
    )

    second = hash_reset_code(
        USER_ID,
        CODE,
    )

    assert first != second

    assert verify_reset_code(
        USER_ID,
        CODE,
        first,
    )

    assert verify_reset_code(
        USER_ID,
        CODE,
        second,
    )


def test_secret_change_invalidates_code(settings):
    encoded = hash_reset_code(
        USER_ID,
        CODE,
    )

    settings.PASSWORD_RESET_SECRET_KEY = "b2" * 32

    assert not verify_reset_code(
        USER_ID,
        CODE,
        encoded,
    )


def test_missing_secret_is_rejected(settings):
    settings.PASSWORD_RESET_SECRET_KEY = ""

    with pytest.raises(ImproperlyConfigured):
        hash_reset_code(
            USER_ID,
            CODE,
        )


def test_invalid_secret_is_rejected(settings):
    settings.PASSWORD_RESET_SECRET_KEY = "short-key"

    with pytest.raises(ImproperlyConfigured):
        get_reset_secret()


def test_non_hexadecimal_secret_is_rejected(settings):
    settings.PASSWORD_RESET_SECRET_KEY = "z" * 64

    with pytest.raises(ImproperlyConfigured):
        get_reset_secret()


def test_unknown_hash_version_is_rejected():
    encoded = hash_reset_code(
        USER_ID,
        CODE,
    )

    encoded = encoded.replace(
        "v1$",
        "v99$",
        1,
    )

    assert not verify_reset_code(
        USER_ID,
        CODE,
        encoded,
    )


def test_legacy_hash_is_rejected():
    encoded = make_password(CODE)

    assert not verify_reset_code(
        USER_ID,
        CODE,
        encoded,
    )


def test_invalid_code_formats_are_rejected():
    invalid_codes = [
        "",
        "12345",
        "1234567",
        "abcdef",
        "12345a",
        "１２３４５６",
        "123 56",
        None,
        123456,
    ]

    encoded = hash_reset_code(
        USER_ID,
        CODE,
    )

    for invalid_code in invalid_codes:

        assert not is_valid_code_format(
            invalid_code,
        )

        assert not verify_reset_code(
            USER_ID,
            invalid_code,
            encoded,
        )


def test_leading_zero_is_supported():
    encoded = hash_reset_code(
        USER_ID,
        "000123",
    )

    assert verify_reset_code(
        USER_ID,
        "000123",
        encoded,
    )


def test_invalid_code_cannot_be_hashed():
    with pytest.raises(ValueError):
        hash_reset_code(
            USER_ID,
            "123",
        )
