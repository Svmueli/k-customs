from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from payments.models import MpesaStkAttempt
from payments.services import reconcile_unresolved_callbacks


class Command(BaseCommand):
    help = "Report stuck M-Pesa attempts and safely replay already-recorded unresolved callbacks."

    def add_arguments(self, parser):
        parser.add_argument("--older-than-minutes", type=int, default=15)
        parser.add_argument("--replay-unresolved", action="store_true")

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(minutes=options["older_than_minutes"])
        attempts = MpesaStkAttempt.objects.filter(
            status__in=[
                MpesaStkAttempt.Status.DISPATCHING,
                MpesaStkAttempt.Status.UNKNOWN,
                MpesaStkAttempt.Status.ACCEPTED,
            ],
            updated_at__lte=cutoff,
        ).order_by("pk")
        for attempt in attempts:
            replayed = 0
            if options["replay_unresolved"]:
                replayed = reconcile_unresolved_callbacks(
                    checkout_request_id=attempt.checkout_request_id,
                )
            self.stdout.write(
                f"attempt={attempt.pk} status={attempt.status} checkout={attempt.checkout_request_id or '-'} replayed={replayed}"
            )
        self.stdout.write(f"stuck_attempts={attempts.count()}")
