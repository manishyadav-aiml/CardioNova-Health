import hashlib
import secrets

from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Extra data for every user: role, privacy choice and API token."""

    ROLE_PATIENT = "patient"
    ROLE_DOCTOR = "doctor"
    ROLE_CHOICES = [(ROLE_PATIENT, "Patient"), (ROLE_DOCTOR, "Doctor")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_PATIENT)
    share_with_doctors = models.BooleanField(default=True)
    api_token_hash = models.CharField(max_length=64, blank=True, db_index=True)
    # First-touch campaign data (UTM parameters) saved at registration; contains no personal data.
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} ({self.role})"

    @property
    def is_doctor(self):
        return self.role == self.ROLE_DOCTOR

    def new_api_token(self):
        """Creates a new API token, stores only its SHA-256 hash and returns the raw token once."""
        raw = secrets.token_urlsafe(32)
        self.api_token_hash = hash_token(raw)
        self.save(update_fields=["api_token_hash"])
        return raw


def hash_token(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


class PredictionRecord(models.Model):
    """One heart disease risk prediction."""

    SOURCE_FORM = "form"
    SOURCE_BATCH = "batch"
    SOURCE_API = "api"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="predictions")
    patient_label = models.CharField(max_length=100, blank=True)

    # The 13 input attributes (same names as the columns of heart.csv)
    age = models.PositiveSmallIntegerField()
    sex = models.PositiveSmallIntegerField()
    cp = models.PositiveSmallIntegerField()
    trestbps = models.PositiveSmallIntegerField()
    chol = models.PositiveSmallIntegerField()
    fbs = models.PositiveSmallIntegerField()
    restecg = models.PositiveSmallIntegerField()
    thalach = models.PositiveSmallIntegerField()
    exang = models.PositiveSmallIntegerField()
    oldpeak = models.FloatField()
    slope = models.PositiveSmallIntegerField()
    ca = models.PositiveSmallIntegerField()
    thal = models.PositiveSmallIntegerField()

    # Result
    probability = models.FloatField()                       # percent
    risk_level = models.CharField(max_length=10)
    explanation = models.JSONField(default=list, blank=True)
    model_name = models.CharField(max_length=60, blank=True)
    source = models.CharField(max_length=10, default=SOURCE_FORM)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.risk_level} ({self.probability:.1f}%)"


class DoctorAccessLog(models.Model):
    """Written every time a doctor opens a patient's data. The patient can read this log."""

    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="access_given")
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="access_log")
    record = models.ForeignKey(PredictionRecord, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-viewed_at"]

    def __str__(self):
        return f"{self.doctor} viewed {self.patient} at {self.viewed_at:%Y-%m-%d %H:%M}"


class ContactMessage(models.Model):
    """Message sent with the contact form (read in the admin site only)."""

    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField(max_length=2000)
    ip_hash = models.CharField(max_length=16, blank=True)      # salted hash, not the raw address
    handled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.created_at:%Y-%m-%d})"
