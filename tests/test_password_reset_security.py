
from datetime import timedelta
from unittest.mock import Mock

import pytest

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.password_reset_models import (
    PasswordResetCode,
)
from apps.accounts.password_reset_service import (
    ResetCodeInvalid,
    create_reset_code,
    create_reset_code_record,
    get_password_fingerprint,
    reset_password_with_code,
)


pytestmark = pytest.mark.django_db


OLD_PASSWORD = "OldPassword123!"
NEW_PASSWORD = "NewPassword456!"


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        username="security_test",
        email="security@example.com",
        password=OLD_PASSWORD,
    )


def test_reset_code_stores_current_email(user):
    result = create_reset_code_record(user)

    record = PasswordResetCode.objects.get(
        pk=result.record_id,
    )

    assert record.email_at_creation == user.email


def test_reset_code_stores_password_fingerprint(user):
    result = create_reset_code_record(user)

    record = PasswordResetCode.objects.get(
        pk=result.record_id,
    )

    assert (
        record.password_fingerprint
        == get_password_fingerprint(user)
    )

    assert len(record.password_fingerprint) == 64

    assert record.password_fingerprint != user.password
    assert record.password_fingerprint != OLD_PASSWORD


def test_inactive_user_cannot_request_code(user):
    user.is_active = False
    user.save(update_fields=["is_active"])

    with pytest.raises(ResetCodeInvalid):
        create_reset_code(user)

    assert not PasswordResetCode.objects.filter(
        user=user,
    ).exists()


def test_deactivated_user_cannot_reset_password(user):
    code = create_reset_code(user)

    user.is_active = False
    user.save(update_fields=["is_active"])

    with pytest.raises(ResetCodeInvalid):
        reset_password_with_code(
            user,
            code,
            NEW_PASSWORD,
        )

    user.refresh_from_db()

    assert user.check_password(OLD_PASSWORD)


def test_email_change_invalidates_previous_code(user):
    code = create_reset_code(user)

    user.email = "changed@example.com"
    user.save(update_fields=["email"])

    result = reset_password_with_code(
        user,
        code,
        NEW_PASSWORD,
    )

    assert result is False

    user.refresh_from_db()

    assert user.check_password(OLD_PASSWORD)


def test_password_change_invalidates_previous_code(user):
    code = create_reset_code(user)

    changed_password = "AdminChanged789!"

    user.set_password(changed_password)
    user.save(update_fields=["password"])

    result = reset_password_with_code(
        user,
        code,
        NEW_PASSWORD,
    )

    assert result is False

    user.refresh_from_db()

    assert user.check_password(changed_password)


def test_wrong_code_is_checked_before_password(
    user,
    monkeypatch,
):
    generated = create_reset_code_record(user)

    wrong_code = (
        "000000"
        if generated.code != "000000"
        else "111111"
    )

    validator = Mock(
        side_effect=ValidationError(
            "Password validation error"
        ),
    )

    monkeypatch.setattr(
        "apps.accounts.password_reset_service."
        "validate_password",
        validator,
    )

    result = reset_password_with_code(
        user,
        wrong_code,
        "123",
    )

    assert result is False

    validator.assert_not_called()

    record = PasswordResetCode.objects.get(
        pk=generated.record_id,
    )

    assert record.attempts == 1


def test_correct_code_validates_new_password(user):
    code = create_reset_code(user)

    with pytest.raises(ValidationError):
        reset_password_with_code(
            user,
            code,
            "123",
        )

    user.refresh_from_db()

    assert user.check_password(OLD_PASSWORD)


def test_weak_password_does_not_consume_valid_code(user):
    result = create_reset_code_record(user)

    with pytest.raises(ValidationError):
        reset_password_with_code(
            user,
            result.code,
            "123",
        )

    record = PasswordResetCode.objects.get(
        pk=result.record_id,
    )

    assert record.used_at is None
    assert record.attempts == 0

    assert reset_password_with_code(
        user,
        result.code,
        NEW_PASSWORD,
    ) is True


def test_new_code_differs_from_previous_code(
    user,
    monkeypatch,
):
    generate = Mock(
        side_effect=[
            "123456",
            "123456",
            "654321",
        ],
    )

    monkeypatch.setattr(
        "apps.accounts.password_reset_service."
        "generate_reset_code",
        generate,
    )

    first = create_reset_code_record(user)

    PasswordResetCode.objects.filter(
        pk=first.record_id,
    ).update(
        created_at=(
            timezone.now() - timedelta(minutes=2)
        ),
    )

    second = create_reset_code_record(user)

    assert first.code == "123456"
    assert second.code == "654321"

    assert generate.call_count == 3


def test_stale_user_cannot_request_code_for_old_email(
    user,
    django_user_model,
):
    django_user_model.objects.filter(
        pk=user.pk,
    ).update(
        email="actual@example.com",
    )

    with pytest.raises(ResetCodeInvalid):
        create_reset_code(user)

    assert not PasswordResetCode.objects.filter(
        user=user,
    ).exists()


def test_legacy_code_without_security_fields_is_invalid(
    user,
):
    result = create_reset_code_record(user)

    PasswordResetCode.objects.filter(
        pk=result.record_id,
    ).update(
        email_at_creation="",
        password_fingerprint="",
    )

    assert reset_password_with_code(
        user,
        result.code,
        NEW_PASSWORD,
    ) is False

    user.refresh_from_db()

    assert user.check_password(OLD_PASSWORD)
