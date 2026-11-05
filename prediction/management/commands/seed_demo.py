import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from prediction import ml
from prediction.models import PredictionRecord, Profile
from prediction.views import build_explanation, save_prediction

# Six invented visits (not real patients) that cover the three risk levels.
SAMPLES = [
    dict(age=45, sex=0, cp=2, trestbps=120, chol=200, fbs=0, restecg=0, thalach=170, exang=0, oldpeak=0.0, slope=1, ca=0, thal=3),
    dict(age=52, sex=1, cp=3, trestbps=130, chol=230, fbs=0, restecg=0, thalach=150, exang=0, oldpeak=1.0, slope=2, ca=0, thal=3),
    dict(age=55, sex=1, cp=3, trestbps=135, chol=240, fbs=0, restecg=0, thalach=145, exang=0, oldpeak=1.5, slope=2, ca=1, thal=6),
    dict(age=58, sex=1, cp=4, trestbps=140, chol=260, fbs=0, restecg=1, thalach=130, exang=1, oldpeak=2.0, slope=2, ca=1, thal=7),
    dict(age=63, sex=1, cp=4, trestbps=150, chol=280, fbs=1, restecg=2, thalach=110, exang=1, oldpeak=3.0, slope=2, ca=2, thal=7),
    dict(age=41, sex=0, cp=2, trestbps=110, chol=190, fbs=0, restecg=0, thalach=175, exang=0, oldpeak=0.0, slope=1, ca=0, thal=3),
]


class Command(BaseCommand):
    help = ("Creates a demo patient (opted in to sharing, with six sample records) and a demo doctor, "
            "so that every page and button can be tried:  python manage.py seed_demo")

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="allow this when DEBUG is off (throw-away demo servers only)")

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Refusing to create demo accounts while DEBUG is off. "
                               "Use --force only on a throw-away demo server.")
        if not ml.model_loaded():
            raise CommandError("No trained model found. Run  python train_model.py  first.")

        User = get_user_model()
        passwords = {}
        for username, role in (("demo_patient", Profile.ROLE_PATIENT), ("demo_doctor", Profile.ROLE_DOCTOR)):
            if User.objects.filter(username=username).exists():
                self.stdout.write(f"{username} already exists (password unchanged).")
                continue
            password = secrets.token_urlsafe(12)
            user = User.objects.create_user(username=username, email=f"{username}@example.com", password=password)
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = role
            profile.share_with_doctors = role == Profile.ROLE_PATIENT      # the demo patient has opted in
            profile.save()
            passwords[username] = password

        patient = User.objects.get(username="demo_patient")
        if not PredictionRecord.objects.filter(user=patient).exists():
            now = timezone.now()
            for number, values in enumerate(SAMPLES, start=1):
                record = save_prediction(patient, values, f"Demo visit {number}", PredictionRecord.SOURCE_FORM,
                                         ml.predict_probability(values), build_explanation(values))
                weeks_ago = len(SAMPLES) - number
                PredictionRecord.objects.filter(pk=record.pk).update(created_at=now - timedelta(weeks=weeks_ago))
            self.stdout.write(f"Created {len(SAMPLES)} sample records for demo_patient.")

        for username, password in passwords.items():
            self.stdout.write(self.style.SUCCESS(f"{username}  password: {password}   (shown once)"))
