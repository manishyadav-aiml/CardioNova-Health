"""
Tests for the review fixes and the data-entry check / plain-language summary:
opt-in doctor sharing, real client address in the password-reset limits, the safe DEBUG default,
the rate-limited e-mail-link reset, and the two new helpers in ml.py.
Run with:  python manage.py test
"""
import os
import subprocess
import sys
import unittest
from unittest import mock

from django.conf import settings
from django.core import mail
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from . import ml
from .models import Profile
from .tests import PASSWORD, make_user, needs_model
from .tests_v2 import INPUTS, FreshCacheTestCase, make_record


# =============================================================================== data-entry checks (no database, no model)
class InputWarningTests(SimpleTestCase):
    TYPICAL = {k: v for k, v in INPUTS.items()}

    def test_typical_values_raise_no_warning(self):
        self.assertEqual(ml.input_warnings(self.TYPICAL), [])

    def test_resting_pulse_entered_as_exercise_maximum(self):
        found = ml.input_warnings({**self.TYPICAL, "age": 21, "thalach": 62})
        self.assertEqual(len(found), 1)
        self.assertIn("Maximum heart rate", found[0])

    def test_low_blood_pressure_and_cholesterol(self):
        found = ml.input_warnings({**self.TYPICAL, "trestbps": 85, "chol": 110})
        self.assertEqual(len(found), 2)
        self.assertTrue(any("blood pressure" in w for w in found))
        self.assertTrue(any("mmol/L" in w for w in found))


class NarrativeTests(SimpleTestCase):
    EXPLANATION = [
        {"feature": "thal", "label": "Thal test", "value": "7 - Reversible defect", "delta": 14.2},
        {"feature": "chol", "label": "Cholesterol", "value": "250", "delta": -2.0},
        {"feature": "age", "label": "Age", "value": "55", "delta": 0.4},
    ]

    def test_summary_names_level_and_probability(self):
        text = ml.narrative(72.5, "HIGH", self.EXPLANATION)
        self.assertIn("high", text["summary"])
        self.assertIn("72.5%", text["summary"])

    def test_only_effects_of_one_point_or_more_are_listed(self):
        points = ml.narrative(40.0, "MODERATE", self.EXPLANATION)["points"]
        self.assertTrue(any("Thal test" in p and "raised" in p for p in points))
        self.assertTrue(any("Cholesterol" in p and "lowered" in p for p in points))
        self.assertFalse(any("Age" in p for p in points))

    def test_questions_follow_the_main_factors_and_level(self):
        questions = ml.narrative(72.5, "HIGH", self.EXPLANATION)["questions"]
        self.assertTrue(any("test results" in q for q in questions))
        self.assertTrue(any("blood pressure, cholesterol" in q for q in questions))
        self.assertTrue(any("further tests" in q for q in questions))
        low = ml.narrative(10.0, "LOW", [])["questions"]
        self.assertTrue(any("routine check-ups" in q for q in low))

    def test_low_trust_adds_a_caution(self):
        trust = {"level": "low", "label": "Low", "reasons": [], "range": (5.0, 40.0)}
        result = ml.narrative(20.0, "LOW", self.EXPLANATION, trust)
        self.assertTrue(any("Trust check is Low" in p for p in result["points"]))
        self.assertTrue(any("5.0%" in p and "40.0%" in p for p in result["points"]))
        self.assertTrue(any("measured and recorded correctly" in q for q in result["questions"]))

    def test_record_without_stored_factors(self):
        result = ml.narrative(55.0, "MODERATE", [])
        self.assertEqual(result["points"], ["Factor details are not stored for this record."])

    def test_wording_never_claims_a_diagnosis(self):
        text = " ".join(ml.narrative(80.0, "HIGH", self.EXPLANATION)["points"]).lower()
        self.assertNotIn("you have", text)
        self.assertNotIn("diagnos", text)


@needs_model
class SummaryOnPagesTests(FreshCacheTestCase):
    def test_result_page_has_the_plain_language_summary(self):
        user = make_user("alice")
        record = make_record(user)
        self.client.login(username="alice", password=PASSWORD)
        html = self.client.get(reverse("result", args=[record.pk])).content.decode()
        self.assertIn('id="plain-summary"', html)
        self.assertIn("Questions you could ask a doctor", html)

    def test_reliability_reports_data_entry_warnings(self):
        trust = ml.reliability({**INPUTS, "age": 21, "thalach": 62})
        self.assertTrue(trust["warnings"])
        self.assertTrue(any("Maximum heart rate" in r for r in trust["reasons"]))


# =============================================================================== doctor sharing is opt-in
class SharingDefaultTests(FreshCacheTestCase):
    def test_new_patients_are_not_shared(self):
        user = make_user("alice")
        self.assertFalse(Profile.objects.get(user=user).share_with_doctors)

    def test_registration_does_not_share(self):
        self.client.post(reverse("register"), {"username": "newuser", "email": "new@example.com",
                                               "password1": PASSWORD, "password2": PASSWORD})
        self.assertFalse(Profile.objects.get(user__username="newuser").share_with_doctors)

    def test_doctor_cannot_see_a_patient_who_never_opted_in(self):
        patient = make_user("zq9patient")
        make_user("doc", doctor=True)
        record = make_record(patient)
        self.client.login(username="doc", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("doctor_patient", args=[patient.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("result", args=[record.pk])).status_code, 403)
        self.assertNotContains(self.client.get(reverse("doctor_dashboard")), "zq9patient")

    def test_patient_can_opt_in(self):
        patient = make_user("pat")
        make_user("doc", doctor=True)
        make_record(patient)
        self.client.login(username="pat", password=PASSWORD)
        self.client.post(reverse("profile"), {"share_with_doctors": "on"})
        self.assertTrue(Profile.objects.get(user=patient).share_with_doctors)
        self.client.logout()
        self.client.login(username="doc", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("doctor_patient", args=[patient.pk])).status_code, 200)


# =============================================================================== password reset
class PasswordResetLimitTests(FreshCacheTestCase):
    def post_otp(self, email, forwarded):
        return self.client.post(reverse("password_reset_request"), {"email": email}, HTTP_X_FORWARDED_FOR=forwarded)

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_limits_use_the_real_client_address_behind_a_proxy(self):
        make_user("alice")
        for i in range(12):                                   # one visitor uses up the per-address allowance
            self.post_otp(f"nobody{i}@example.com", "10.0.0.1")
        self.assertEqual(len(mail.outbox), 0)
        self.post_otp("alice@example.com", "10.0.0.2")        # a different visitor behind the same proxy is not affected
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_the_same_address_stays_limited(self):
        make_user("alice")
        for i in range(10):
            self.post_otp(f"nobody{i}@example.com", "10.0.0.1")
        self.post_otp("alice@example.com", "10.0.0.1")
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(RATE_LIMITS={**settings.RATE_LIMITS, "password_reset_link": (2, 60)})
    def test_email_link_reset_is_rate_limited(self):
        make_user("alice")
        url = reverse("password_reset_link")
        with mock.patch("django.contrib.auth.forms.PasswordResetForm.save") as save:
            codes = [self.client.post(url, {"email": "alice@example.com"}).status_code for _ in range(4)]
        self.assertEqual(codes, [302, 302, 302, 302])         # always the same answer: nothing is revealed
        self.assertEqual(save.call_count, 2)                  # but only two requests reached the mail code


# =============================================================================== safe defaults
class SafeDefaultsTests(SimpleTestCase):
    @unittest.skipIf((settings.BASE_DIR / ".env").exists(), "a local .env file may legitimately set these values")
    def test_debug_is_off_unless_switched_on(self):
        env = {k: v for k, v in os.environ.items() if k not in ("DJANGO_DEBUG", "DJANGO_SECRET_KEY")}
        env["DJANGO_SETTINGS_MODULE"] = "heart_disease.settings"
        result = subprocess.run([sys.executable, "-c", "import heart_disease.settings"], env=env,
                                capture_output=True, text=True, cwd=settings.BASE_DIR)
        self.assertNotEqual(result.returncode, 0)             # no key + no DEBUG flag -> refuses to start
        self.assertIn("DJANGO_SECRET_KEY", result.stderr)

    def test_scikit_learn_is_pinned_to_the_version_of_the_committed_model(self):
        text = (settings.BASE_DIR / "requirements.txt").read_text()
        self.assertIn("scikit-learn==", text)
