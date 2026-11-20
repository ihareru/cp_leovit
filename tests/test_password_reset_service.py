from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.password_reset_models import PasswordResetCode
from apps.accounts.password_reset_service import (
    ResetCodeCooldown,
    ResetCodeInvalid,
    create_reset_code,
    reset_password_with_code,
)
from apps.accounts.password_reset_crypto import verify_reset_code


pytestmark = pytest.mark.django_db


@pytest.fixture
def reset_user(django_user_model):
    return django_user_model.objects.create_user(
        username="reset_user",
        email="reset_user@example.com",
        password="OldPassword123!",
    )


def test_create_code(reset_user):
    code = create_reset_code(reset_user)

    assert len(code) == 6
    assert code.isascii()
    assert code.isdigit()

    record = PasswordResetCode.objects.get(
        user=reset_user,
    )

    assert record.code_hash != code

    assert record.code_hash.startswith("v1$")

    assert verify_reset_code(
        reset_user.pk,
        code,
        record.code_hash,
    )

    assert record.used_at is None
    assert record.attempts == 0
    assert record.is_valid is True


def test_code_expires_in_15_minutes(reset_user):
    create_reset_code(reset_user)

    record = PasswordResetCode.objects.get(
        user=reset_user,
    )

    assert record.expires_at - record.created_at == (
        timedelta(minutes=15)
    )


def test_successful_password_reset(reset_user):
    code = create_reset_code(reset_user)

    result = reset_password_with_code(
        reset_user,
        code,
        "NewPassword123!",
    )

    assert result is True

    reset_user.refresh_from_db()

    assert reset_user.check_password(
        "NewPassword123!"
    )

    record = PasswordResetCode.objects.get(
        user=reset_user,
    )

    assert record.used_at is not None


def test_code_cannot_be_reused(reset_user):
    code = create_reset_code(reset_user)

    assert reset_password_with_code(
        reset_user,
        code,
        "NewPassword123!",
    )

    with pytest.raises(ResetCodeInvalid):
        reset_password_with_code(
            reset_user,
            code,
            "AnotherPassword123!",
        )


def test_five_invalid_attempts(reset_user):
    code = create_reset_code(reset_user)

    wrong_code = (
        "000000" if code != "000000" else "999999"
    )

    for _ in range(5):
        assert reset_password_with_code(
            reset_user,
            wrong_code,
            "NewPassword123!",
        ) is False

    record = PasswordResetCode.objects.get(
        user=reset_user,
    )

    assert record.attempts == 5

    with pytest.raises(ResetCodeInvalid):
        reset_password_with_code(
            reset_user,
            code,
            "NewPassword123!",
        )


def test_expired_code(reset_user):
    code = create_reset_code(reset_user)

    PasswordResetCode.objects.filter(
        user=reset_user,
    ).update(
        expires_at=timezone.now() - timedelta(seconds=1),
    )

    with pytest.raises(ResetCodeInvalid):
        reset_password_with_code(
            reset_user,
            code,
            "NewPassword123!",
        )


def test_resend_cooldown(reset_user):
    create_reset_code(reset_user)

    with pytest.raises(ResetCodeCooldown):
        create_reset_code(reset_user)


def test_new_code_invalidates_previous(reset_user):
    old_code = create_reset_code(reset_user)

    PasswordResetCode.objects.filter(
        user=reset_user,
    ).update(
        created_at=timezone.now() - timedelta(seconds=61),
    )

    new_code = create_reset_code(reset_user)

    # Проверяем, что старый код погашен.
    old_record = (
        PasswordResetCode.objects
        .filter(user=reset_user)
        .order_by("created_at")
        .first()
    )

    assert old_record.used_at is not None

    # Старый код не должен менять пароль.
    assert reset_password_with_code(
        reset_user,
        old_code,
        "NewPassword123!",
    ) is False

    reset_user.refresh_from_db()

    assert reset_user.check_password(
        "OldPassword123!"
    )

    # Новый код должен работать.
    assert reset_password_with_code(
        reset_user,
        new_code,
        "NewPassword123!",
    ) is True

    reset_user.refresh_from_db()

    assert reset_user.check_password(
        "NewPassword123!"
    )


@pytest.mark.django_db
def test_invalidate_only_selected_reset_code(
    django_user_model,
):
    from datetime import timedelta

    from django.utils import timezone

    from apps.accounts.password_reset_service import (
        create_reset_code_record,
        invalidate_reset_code,
    )

    user = django_user_model.objects.create_user(
        username="invalidate_test",
        email="invalidate@example.com",
        password="OldPassword123!",
    )

    first = create_reset_code_record(user)

    PasswordResetCode.objects.filter(
        pk=first.record_id,
    ).update(
        created_at=timezone.now() - timedelta(minutes=2),
    )

    second = create_reset_code_record(user)

    invalidate_reset_code(first.record_id)

    second_record = PasswordResetCode.objects.get(
        pk=second.record_id,
    )

    assert second_record.used_at is None
    assert second_record.is_valid is True
