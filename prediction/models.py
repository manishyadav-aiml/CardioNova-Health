import hashlib
import hmac
import secrets

from django.conf import settings
from django.db import models

from . import totp


class Profile(models.Model):
    """Extra data for every user: role, privacy choice and API token."""

    ROLE_PATIENT = "patient"
    ROLE_DOCTOR = "doctor"
    ROLE_CHOICES = [(ROLE_PATIENT, "Patient"), (ROLE_DOCTOR, "Doctor")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_PATIENT)
    share_with_doctors = models.BooleanField(default=False)     # opt-in: nobody is shared until the patient agrees
    api_token_hash = models.CharField(max_length=64, blank=True, db_index=True)
    # Two-factor login (TOTP). The secret is needed in clear text to check codes: protect the database itself
    # (disk encryption, restricted access). Recovery codes are stored only as keyed hashes.
    totp_secret = models.CharField(max_length=64, blank=True)
    totp_enabled = models.BooleanField(default=False)
    totp_last_step = models.BigIntegerField(default=0)           # newest accepted time step: a code cannot be used twice
    recovery_hashes = models.JSONField(default=list, blank=True)
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

    def check_totp(self, code):
        """True when `code` is a valid, not yet used authenticator code. The step is stored atomically, so two
        simultaneous requests cannot both use the same code."""
        step = totp.verify(self.totp_secret, code, last_step=self.totp_last_step) if self.totp_secret else None
        if step is None:
            return False
        if Profile.objects.filter(pk=self.pk, totp_last_step__lt=step).update(totp_last_step=step):
            self.totp_last_step = step
            return True
        return False

    def new_recovery_codes(self):
        """Replaces all recovery codes; returns the clear codes once (only hashes are stored)."""
        codes = totp.new_recovery_codes()
        self.recovery_hashes = [hash_recovery_code(c) for c in codes]
        self.save(update_fields=["recovery_hashes"])
        return codes

    def use_recovery_code(self, code):
        """Consumes one recovery code. Compares against every stored hash so timing does not reveal which matched."""
        wanted = hash_recovery_code(code)
        matched = None
        for stored in self.recovery_hashes:
            if hmac.compare_digest(stored, wanted):
                matched = stored
        if matched is None:
            return False
        self.recovery_hashes = [h for h in self.recovery_hashes if h != matched]
        self.save(update_fields=["recovery_hashes"])
        return True

    def disable_two_factor(self):
        self.totp_secret, self.totp_enabled, self.totp_last_step, self.recovery_hashes = "", False, 0, []
        self.save(update_fields=["totp_secret", "totp_enabled", "totp_last_step", "recovery_hashes"])

    def new_api_token(self):
        """Creates a new API token, stores only its SHA-256 hash and returns the raw token once."""
        raw = secrets.token_urlsafe(32)
        self.api_token_hash = hash_token(raw)
        self.save(update_fields=["api_token_hash"])
        return raw


def hash_recovery_code(code):
    """Keyed hash (the secret key acts as a pepper), so a leaked database alone cannot be used to guess codes."""
    return hmac.new(settings.SECRET_KEY.encode(), b"recovery:" + totp.normalise_recovery_code(code).encode(),
                    hashlib.sha256).hexdigest()


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
