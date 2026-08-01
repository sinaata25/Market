from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from accounts.models import Otp


class Command(BaseCommand):
    help = "Delete expired OTP diagnostic rows after the configured retention period"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=settings.SHOP["OTP_RETENTION_DAYS"],
            help="Retention in days (defaults to OTP_RETENTION_DAYS)",
        )

    def handle(self, *args, **options):
        days = options["days"]
        if not 1 <= days <= 365:
            raise CommandError("--days must be between 1 and 365")

        cutoff = timezone.now() - timezone.timedelta(days=days)
        regular_row = Q(send_token__isnull=True) & (
            Q(sent_at__lt=cutoff)
            | Q(sent_at__isnull=True, expires_at__lt=cutoff)
        )
        stale_pending_row = Q(send_token__isnull=False) & (
            Q(pending_expires_at__lt=cutoff)
            | Q(
                pending_expires_at__isnull=True,
                send_started_at__lt=cutoff,
            )
            | Q(
                pending_expires_at__isnull=True,
                send_started_at__isnull=True,
                expires_at__lt=cutoff,
            )
        )
        deleted, _details = Otp.objects.filter(
            regular_row | stale_pending_row
        ).delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} expired OTP rows"))
