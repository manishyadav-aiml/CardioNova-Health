import json
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from prediction import drift, ml
from prediction.models import PredictionRecord

logger = logging.getLogger("prediction.drift")


class Command(BaseCommand):
    help = ("Compares the inputs of recent predictions with the training data (population stability index per input). "
            "Exit code 1 with --fail-on-drift when drift is found, so it can run from cron or CI:  "
            "python manage.py drift_report --days 30 --fail-on-drift")

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30, help="look at predictions of the last N days (default 30)")
        parser.add_argument("--json", action="store_true", help="print the full result as JSON")
        parser.add_argument("--fail-on-drift", action="store_true", help="exit with an error when drift is found")

    def handle(self, *args, **options):
        reference = ml.model_info().get("drift_reference")
        if not reference:
            raise CommandError("The model file has no training reference. Run  python train_model.py  first.")
        since = timezone.now() - timedelta(days=options["days"])
        rows = list(PredictionRecord.objects.filter(created_at__gte=since).values(*ml.FEATURES))
        result = drift.compare(reference, rows)

        if options["json"]:
            self.stdout.write(json.dumps(result, indent=2))
        elif result["overall"] == "insufficient":
            self.stdout.write(f"Not enough data: {result['n']} prediction(s) in the last {options['days']} days "
                              f"(at least {result['min_records']} are needed).")
        else:
            self.stdout.write(f"{result['n']} predictions in the last {options['days']} days "
                              f"(training reference: {result['training_records']} records)")
            self.stdout.write(f"{'input':10} {'adj. PSI':>9}  {'status':8} what changed")
            for f in result["features"]:
                self.stdout.write(f"{f['name']:10} {f['adjusted']:>9}  {f['status']:8} {f['detail']}")
            self.stdout.write(f"Inputs outside the training range: {result['out_of_range_share']:.0%} of predictions")
            self.stdout.write(f"Overall: {result['overall'].upper()}")

        if result["overall"] == "drift":
            logger.warning("input drift detected: %s", ", ".join(result["flagged"]) or "many inputs outside the training range")
            if options["fail_on_drift"]:
                raise CommandError("Input drift detected.")
