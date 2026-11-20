
from datetime import timedelta
from io import StringIO

import pytest

from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError
from django.utils import timezone

from apps.accounts.password_reset_cleanup import (
    cleanup_password_reset,
)

from apps.accounts.password_reset_models import (
    PasswordResetCode,
)

from apps.accounts.password_reset_rate_models import (
    PasswordResetRateLimit,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def user(django_user_model):

    return django_user_model.objects.create_user(
        username="cleanup_test",
        email="cleanup@example.com",
        password="OldPassword123!",
    )


@pytest.fixture
def now():

    return timezone.now()


def create_code(
    user,
    expires_at,
    used_at=None,
    attempts=0,
):

    return PasswordResetCode.objects.create(
        user=user,
        code_hash="test-cleanup-hash",
        email_at_creation=user.email,
        password_fingerprint="a" * 64,
        created_at=(
            expires_at
            - timedelta(minutes=15)
        ),
        expires_at=expires_at,
        used_at=used_at,
        attempts=attempts,
    )


def create_rate_limit(
    key,
    expires_at,
):

    return PasswordResetRateLimit.objects.create(
        key=key,
        count=5,
        expires_at=expires_at,
        updated_at=(
            expires_at
            - timedelta(minutes=15)
        ),
    )


def test_active_code_is_preserved(user, now):

    record = create_code(
        user,
        expires_at=now + timedelta(minutes=10),
    )

    result = cleanup_password_reset()

    assert result.deleted_codes == 0

    assert PasswordResetCode.objects.filter(
        pk=record.pk,
    ).exists()


def test_recently_expired_code_is_preserved(
    user,
    now,
):

    record = create_code(
        user,
        expires_at=now - timedelta(days=1),
    )

    result = cleanup_password_reset()

    assert result.deleted_codes == 0

    assert PasswordResetCode.objects.filter(
        pk=record.pk,
    ).exists()


def test_old_expired_code_is_deleted(user, now):

    record = create_code(
        user,
        expires_at=now - timedelta(days=8),
    )

    result = cleanup_password_reset()

    assert result.deleted_codes == 1

    assert not PasswordResetCode.objects.filter(
        pk=record.pk,
    ).exists()


def test_recently_used_code_is_preserved(
    user,
    now,
):

    record = create_code(
        user,
        expires_at=now - timedelta(hours=1),
        used_at=now - timedelta(hours=2),
    )

    result = cleanup_password_reset()

    assert result.deleted_codes == 0

    assert PasswordResetCode.objects.filter(
        pk=record.pk,
    ).exists()


def test_old_used_code_is_deleted(user, now):

    record = create_code(
        user,
        expires_at=now - timedelta(days=8),
        used_at=(
            now
            - timedelta(days=8, minutes=5)
        ),
    )

    result = cleanup_password_reset()

    assert result.deleted_codes == 1

    assert not PasswordResetCode.objects.filter(
        pk=record.pk,
    ).exists()


def test_old_exhausted_code_is_deleted(
    user,
    now,
):

    record = create_code(
        user,
        expires_at=now - timedelta(days=8),
        attempts=5,
    )

    result = cleanup_password_reset()

    assert result.deleted_codes == 1

    assert not PasswordResetCode.objects.filter(
        pk=record.pk,
    ).exists()


def test_recent_exhausted_code_is_preserved(
    user,
    now,
):

    record = create_code(
        user,
        expires_at=now - timedelta(minutes=10),
        attempts=5,
    )

    result = cleanup_password_reset()

    assert result.deleted_codes == 0

    assert PasswordResetCode.objects.filter(
        pk=record.pk,
    ).exists()


def test_active_rate_limit_is_preserved(now):

    record = create_rate_limit(
        "active-counter",
        expires_at=now + timedelta(minutes=10),
    )

    result = cleanup_password_reset()

    assert result.deleted_rate_limits == 0

    assert PasswordResetRateLimit.objects.filter(
        pk=record.pk,
    ).exists()


def test_recent_expired_rate_limit_is_preserved(
    now,
):

    record = create_rate_limit(
        "recent-counter",
        expires_at=now - timedelta(hours=2),
    )

    result = cleanup_password_reset()

    assert result.deleted_rate_limits == 0

    assert PasswordResetRateLimit.objects.filter(
        pk=record.pk,
    ).exists()


def test_old_rate_limit_is_deleted(now):

    record = create_rate_limit(
        "old-counter",
        expires_at=now - timedelta(hours=25),
    )

    result = cleanup_password_reset()

    assert result.deleted_rate_limits == 1

    assert not PasswordResetRateLimit.objects.filter(
        pk=record.pk,
    ).exists()


def test_dry_run_does_not_delete_records(
    user,
    now,
):

    create_code(
        user,
        expires_at=now - timedelta(days=8),
    )

    create_rate_limit(
        "old-counter",
        expires_at=now - timedelta(days=2),
    )

    result = cleanup_password_reset(
        dry_run=True,
    )

    assert result.dry_run is True
    assert result.deleted_codes == 1
    assert result.deleted_rate_limits == 1
    assert result.total == 2

    assert PasswordResetCode.objects.count() == 1

    assert (
        PasswordResetRateLimit.objects.count()
        == 1
    )


def test_empty_database_cleanup():

    result = cleanup_password_reset()

    assert result.deleted_codes == 0
    assert result.deleted_rate_limits == 0
    assert result.total == 0
    assert result.dry_run is False


def test_cleanup_can_be_run_repeatedly(
    user,
    now,
):

    create_code(
        user,
        expires_at=now - timedelta(days=8),
    )

    first = cleanup_password_reset()
    second = cleanup_password_reset()

    assert first.deleted_codes == 1
    assert second.deleted_codes == 0


def test_batch_cleanup(
    user,
    now,
    settings,
):

    settings.PASSWORD_RESET_CLEANUP_BATCH_SIZE = 2

    for _ in range(5):

        create_code(
            user,
            expires_at=now - timedelta(days=8),
        )

    for index in range(5):

        create_rate_limit(
            f"old-counter-{index}",
            expires_at=now - timedelta(days=2),
        )

    result = cleanup_password_reset()

    assert result.deleted_codes == 5
    assert result.deleted_rate_limits == 5
    assert result.total == 10

    assert not PasswordResetCode.objects.exists()

    assert not (
        PasswordResetRateLimit.objects.exists()
    )


def test_custom_code_retention(
    user,
    now,
    settings,
):

    settings.PASSWORD_RESET_CODE_RETENTION_DAYS = 2

    create_code(
        user,
        expires_at=now - timedelta(days=3),
    )

    result = cleanup_password_reset()

    assert result.deleted_codes == 1


def test_custom_rate_limit_retention(
    now,
    settings,
):

    settings.PASSWORD_RESET_RATE_LIMIT_RETENTION_HOURS = 2

    create_rate_limit(
        "old-counter",
        expires_at=now - timedelta(hours=3),
    )

    result = cleanup_password_reset()

    assert result.deleted_rate_limits == 1


@pytest.mark.parametrize(
    "setting_name",
    [
        "PASSWORD_RESET_CODE_RETENTION_DAYS",
        "PASSWORD_RESET_RATE_LIMIT_RETENTION_HOURS",
        "PASSWORD_RESET_CLEANUP_BATCH_SIZE",
    ],
)
def test_invalid_cleanup_setting(
    settings,
    setting_name,
):

    setattr(
        settings,
        setting_name,
        0,
    )

    with pytest.raises(ImproperlyConfigured):

        cleanup_password_reset()


def test_management_command_dry_run(
    user,
    now,
):

    create_code(
        user,
        expires_at=now - timedelta(days=8),
    )

    output = StringIO()

    call_command(
        "cleanup_password_reset",
        "--dry-run",
        stdout=output,
    )

    assert "DRY RUN" in output.getvalue()

    assert (
        "Total eligible records: 1"
        in output.getvalue()
    )

    assert PasswordResetCode.objects.count() == 1


def test_management_command_deletes_records(
    user,
    now,
):

    create_code(
        user,
        expires_at=now - timedelta(days=8),
    )

    output = StringIO()

    call_command(
        "cleanup_password_reset",
        stdout=output,
    )

    assert (
        "Total deleted records: 1"
        in output.getvalue()
    )

    assert not PasswordResetCode.objects.exists()


def test_management_command_database_error(
    monkeypatch,
):

    def fail(*args, **kwargs):

        raise DatabaseError(
            "Database unavailable"
        )

    monkeypatch.setattr(
        "apps.accounts.management.commands."
        "cleanup_password_reset."
        "cleanup_password_reset",
        fail,
    )

    with pytest.raises(
        CommandError,
        match="database error",
    ):

        call_command(
            "cleanup_password_reset",
        )


def test_used_code_with_recent_usage_is_preserved(
    user,
    now,
):

    record = create_code(
        user,
        expires_at=now - timedelta(days=8),
        used_at=now - timedelta(days=1),
    )

    result = cleanup_password_reset()

    assert result.deleted_codes == 0

    assert PasswordResetCode.objects.filter(
        pk=record.pk,
    ).exists()


def test_cleanup_does_not_delete_user(
    user,
    now,
):

    create_code(
        user,
        expires_at=now - timedelta(days=8),
    )

    cleanup_password_reset()

    user.refresh_from_db()

    assert user.is_active

    assert user.check_password(
        "OldPassword123!",
    )
