
from django.core.exceptions import ImproperlyConfigured

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from django.db import DatabaseError

from apps.accounts.password_reset_cleanup import (
    cleanup_password_reset,
)


class Command(BaseCommand):

    help = (
        "Remove expired password reset codes "
        "and rate limit records."
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Show records that would be removed "
                "without deleting them."
            ),
        )

    def handle(self, *args, **options):

        dry_run = options["dry_run"]

        try:

            result = cleanup_password_reset(
                dry_run=dry_run,
            )

        except ImproperlyConfigured as exc:

            raise CommandError(
                str(exc)
            ) from exc

        except DatabaseError as exc:

            raise CommandError(
                "Password reset cleanup database error."
            ) from exc

        if result.dry_run:

            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN: no records were deleted."
                )
            )

            self.stdout.write(
                f"Codes eligible for deletion: "
                f"{result.deleted_codes}"
            )

            self.stdout.write(
                f"Rate limits eligible for deletion: "
                f"{result.deleted_rate_limits}"
            )

            self.stdout.write(
                f"Total eligible records: "
                f"{result.total}"
            )

        else:

            self.stdout.write(
                self.style.SUCCESS(
                    "Password reset cleanup completed."
                )
            )

            self.stdout.write(
                f"Deleted codes: "
                f"{result.deleted_codes}"
            )

            self.stdout.write(
                f"Deleted rate limits: "
                f"{result.deleted_rate_limits}"
            )

            self.stdout.write(
                f"Total deleted records: "
                f"{result.total}"
            )
