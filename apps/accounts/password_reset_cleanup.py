
import logging

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .password_reset_models import PasswordResetCode
from .password_reset_rate_models import (
    PasswordResetRateLimit,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CleanupResult:

    deleted_codes: int
    deleted_rate_limits: int
    dry_run: bool = False

    @property
    def total(self):

        return (
            self.deleted_codes
            + self.deleted_rate_limits
        )


def validate_positive_integer(name, value):

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
    ):

        raise ImproperlyConfigured(
            f"{name} must be a positive integer."
        )

    return value


def get_cleanup_settings():

    code_retention_days = validate_positive_integer(
        "PASSWORD_RESET_CODE_RETENTION_DAYS",
        settings.PASSWORD_RESET_CODE_RETENTION_DAYS,
    )

    rate_limit_retention_hours = (
        validate_positive_integer(
            "PASSWORD_RESET_RATE_LIMIT_RETENTION_HOURS",
            settings.PASSWORD_RESET_RATE_LIMIT_RETENTION_HOURS,
        )
    )

    batch_size = validate_positive_integer(
        "PASSWORD_RESET_CLEANUP_BATCH_SIZE",
        settings.PASSWORD_RESET_CLEANUP_BATCH_SIZE,
    )

    return (
        code_retention_days,
        rate_limit_retention_hours,
        batch_size,
    )


def delete_in_batches(queryset, batch_size):

    total_deleted = 0

    while True:

        with transaction.atomic():

            ids = list(
                queryset
                .order_by("pk")
                .select_for_update(
                    skip_locked=True,
                )
                .values_list(
                    "pk",
                    flat=True,
                )[:batch_size]
            )

            if not ids:

                break

            _, deleted_by_model = (
                queryset
                .filter(pk__in=ids)
                .delete()
            )

            deleted_count = deleted_by_model.get(
                queryset.model._meta.label,
                0,
            )

            total_deleted += deleted_count

    return total_deleted


def cleanup_password_reset(
    *,
    dry_run=False,
):

    (
        code_retention_days,
        rate_limit_retention_hours,
        batch_size,
    ) = get_cleanup_settings()

    now = timezone.now()

    code_cutoff = now - timedelta(
        days=code_retention_days,
    )

    rate_limit_cutoff = now - timedelta(
        hours=rate_limit_retention_hours,
    )

    expired_codes = (
        PasswordResetCode.objects.filter(
            Q(
                used_at__isnull=True,
                expires_at__lte=code_cutoff,
            )
            |
            Q(
                used_at__isnull=False,
                used_at__lte=code_cutoff,
                expires_at__lte=now,
            )
        )
    )

    expired_rate_limits = (
        PasswordResetRateLimit.objects.filter(
            expires_at__lte=rate_limit_cutoff,
        )
    )

    if dry_run:

        return CleanupResult(
            deleted_codes=expired_codes.count(),
            deleted_rate_limits=(
                expired_rate_limits.count()
            ),
            dry_run=True,
        )

    deleted_codes = delete_in_batches(
        expired_codes,
        batch_size,
    )

    deleted_rate_limits = delete_in_batches(
        expired_rate_limits,
        batch_size,
    )

    result = CleanupResult(
        deleted_codes=deleted_codes,
        deleted_rate_limits=deleted_rate_limits,
    )

    logger.info(
        "Password reset cleanup completed: "
        "codes=%s, rate_limits=%s",
        result.deleted_codes,
        result.deleted_rate_limits,
    )

    return result
