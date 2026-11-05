"""
Tests for the second round of upgrades: two-factor login, Redis-ready rate limits, input drift monitoring,
experiment tracking. Run with:  python manage.py test
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import types
from io import StringIO
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from ml_pipeline import tracking

from . import drift, ml, totp, views
from .models import PredictionRecord, Profile
from .tests import PASSWORD, make_user, needs_model
from .tests_v2 import INPUTS, FreshCacheTestCase, make_record


# =============================================================================== TOTP (RFC 6238)
class TotpTests(SimpleTestCase):
    SECRET = base64.b32encode(b"12345678901234567890").decode().rstrip("=")      # the RFC's test key

    def test_rfc_6238_test_vectors(self):
        vectors = {59: "94287082", 1111111109: "07081804", 1111111111: "14050471",
                   1234567890: "89005924", 2000000000: "69279037", 20000000000: "65353130"}
        for when, expected in vectors.items():
            self.assertEqual(totp.totp_at(self.SECRET, when, digits=8), expected)
            self.assertEqual(totp.totp_at(self.SECRET, when), expected[-6:])

    def test_verify_accepts_one_step_of_clock_drift_only(self):
        secret, now = totp.new_secret(), 1_700_000_000
        code = totp.totp_at(secret, now)
        self.assertEqual(totp.verify(secret, code, now=now), now // 30)
        self.assertEqual(totp.verify(secret, code, now=now + 30), now // 30)
        self.assertIsNone(totp.verify(secret, code, now=now + 120))

    def test_a_code_cannot_be_replayed(self):
        secret, now = totp.new_secret(), 1_700_000_000
        code = totp.totp_at(secret, now)
        step = totp.verify(secret, code, now=now)
        self.assertIsNone(totp.verify(secret, code, now=now, last_step=step))

    def test_garbage_is_refused(self):
        secret = totp.new_secret()
        for bad in ("", "12345", "abcdef", "1234567", "12 34 56 78"):
            self.assertIsNone(totp.verify(secret, bad))

    def test_secret_uri_and_recovery_codes(self):
        secret = totp.new_secret()
        self.assertEqual(len(secret), 32)
        self.assertTrue(totp.otpauth_uri(secret, "alice").startswith("otpauth://totp/CardioNova%20Health%3Aalice?secret="))
        codes = totp.new_recovery_codes()
        self.assertEqual(len(set(codes)), 8)
        self.assertEqual(totp.normalise_recovery_code(codes[0].upper()), codes[0].replace("-", ""))


# =============================================================================== two-factor login flow
def User_of(name):
    from django.contrib.auth.models import User
    return User.objects.get(username=name)


def enable_two_factor(user):
    profile = Profile.objects.get(user=user)
    secret = totp.new_secret()
    profile.totp_secret, profile.totp_enabled = secret, True
    profile.save()
    return secret, profile.new_recovery_codes()


class TwoFactorLoginTests(FreshCacheTestCase):
    def password_step(self, username="alice", **extra):
        return self.client.post(reverse("login"), {"username": username, "password": PASSWORD, **extra})

    def logged_in(self):
        return "_auth_user_id" in self.client.session

    def test_password_alone_does_not_log_in(self):
        make_user("alice")
        enable_two_factor(User_of("alice"))
        response = self.password_step()
        self.assertRedirects(response, reverse("twofactor_verify"), fetch_redirect_response=False)
        self.assertFalse(self.logged_in())
        self.assertEqual(self.client.get(reverse("history")).status_code, 302)       # still sent to the login page

    def test_users_without_two_factor_log_in_as_before(self):
        make_user("bob")
        self.assertRedirects(self.password_step("bob"), reverse("home"), fetch_redirect_response=False)
        self.assertTrue(self.logged_in())

    def test_correct_code_finishes_the_login_and_keeps_next(self):
        user = make_user("alice")
        secret, _ = enable_two_factor(user)
        self.password_step(next=reverse("history"))
        response = self.client.post(reverse("twofactor_verify"), {"code": totp.totp_at(secret)})
        self.assertRedirects(response, reverse("history"), fetch_redirect_response=False)
        self.assertTrue(self.logged_in())

    def test_wrong_code_is_refused(self):
        user = make_user("alice")
        secret, _ = enable_two_factor(user)
        self.password_step()
        wrong = "000000" if totp.totp_at(secret) != "000000" else "111111"
        response = self.client.post(reverse("twofactor_verify"), {"code": wrong})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not correct")
        self.assertFalse(self.logged_in())

    def test_the_same_code_cannot_be_used_twice(self):
        user = make_user("alice")
        secret, _ = enable_two_factor(user)
        code = totp.totp_at(secret)
        self.password_step()
        self.client.post(reverse("twofactor_verify"), {"code": code})
        self.assertTrue(self.logged_in())
        self.client.post(reverse("logout"))
        self.password_step()
        again = self.client.post(reverse("twofactor_verify"), {"code": code})
        self.assertEqual(again.status_code, 200)
        self.assertFalse(self.logged_in())

    def test_recovery_code_works_exactly_once(self):
        user = make_user("alice")
        _, codes = enable_two_factor(user)
        self.password_step()
        self.client.post(reverse("twofactor_verify"), {"code": codes[0]})
        self.assertTrue(self.logged_in())
        self.assertEqual(len(Profile.objects.get(user=user).recovery_hashes), 7)
        self.client.post(reverse("logout"))
        self.password_step()
        again = self.client.post(reverse("twofactor_verify"), {"code": codes[0]})
        self.assertEqual(again.status_code, 200)
        self.assertFalse(self.logged_in())

    def test_too_many_wrong_codes_lock_the_step(self):
        user = make_user("alice")
        secret, _ = enable_two_factor(user)
        self.password_step()
        wrong = "000000" if totp.totp_at(secret) != "000000" else "111111"
        for _ in range(5):
            self.client.post(reverse("twofactor_verify"), {"code": wrong})
        blocked = self.client.post(reverse("twofactor_verify"), {"code": totp.totp_at(secret)})
        self.assertEqual(blocked.status_code, 429)
        self.assertFalse(self.logged_in())

    def test_verify_page_needs_the_password_step_first(self):
        self.assertRedirects(self.client.get(reverse("twofactor_verify")), reverse("login"), fetch_redirect_response=False)

    def test_pending_login_expires(self):
        user = make_user("alice")
        enable_two_factor(user)
        self.password_step()
        session = self.client.session
        session[views.PENDING_2FA]["time"] -= 1000
        session.save()
        self.assertRedirects(self.client.get(reverse("twofactor_verify")), reverse("login"), fetch_redirect_response=False)

    def test_an_outside_next_address_is_ignored(self):
        user = make_user("alice")
        secret, _ = enable_two_factor(user)
        self.password_step(next="https://evil.example/steal")
        response = self.client.post(reverse("twofactor_verify"), {"code": totp.totp_at(secret)})
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)


class TwoFactorSetupTests(FreshCacheTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("alice")
        self.client.login(username="alice", password=PASSWORD)

    def test_full_setup_flow(self):
        started = self.client.post(reverse("twofactor_setup"), {"action": "start"})
        self.assertContains(started, "Set up in 3 steps")
        secret = self.client.session[views.TOTP_SETUP_KEY]
        self.assertContains(started, totp.group(secret))
        done = self.client.post(reverse("twofactor_setup"), {"action": "confirm", "code": totp.totp_at(secret)})
        self.assertContains(done, "recovery codes")
        profile = Profile.objects.get(user=self.user)
        self.assertTrue(profile.totp_enabled)
        self.assertEqual(profile.totp_secret, secret)
        self.assertEqual(len(profile.recovery_hashes), 8)

    def test_wrong_confirmation_code_does_not_enable(self):
        self.client.post(reverse("twofactor_setup"), {"action": "start"})
        secret = self.client.session[views.TOTP_SETUP_KEY]
        wrong = "000000" if totp.totp_at(secret) != "000000" else "111111"
        response = self.client.post(reverse("twofactor_setup"), {"action": "confirm", "code": wrong})
        self.assertContains(response, "not correct")
        self.assertFalse(Profile.objects.get(user=self.user).totp_enabled)

    def test_recovery_codes_are_not_stored_in_clear(self):
        _, codes = enable_two_factor(self.user)
        stored = json.dumps(Profile.objects.get(user=self.user).recovery_hashes)
        for code in codes:
            self.assertNotIn(code.replace("-", ""), stored)

    def test_disable_needs_password_and_code(self):
        secret, _ = enable_two_factor(self.user)
        wrong_password = self.client.post(reverse("twofactor_setup"), {"action": "disable", "password": "nope", "code": totp.totp_at(secret)})
        self.assertContains(wrong_password, "not correct")
        self.assertTrue(Profile.objects.get(user=self.user).totp_enabled)
        self.client.post(reverse("twofactor_setup"), {"action": "disable", "password": PASSWORD, "code": totp.totp_at(secret)})
        profile = Profile.objects.get(user=self.user)
        self.assertFalse(profile.totp_enabled)
        self.assertEqual((profile.totp_secret, profile.recovery_hashes), ("", []))

    def test_profile_page_links_to_the_setup(self):
        self.assertContains(self.client.get(reverse("profile")), "Set up two-factor login")

    @override_settings(REQUIRE_2FA_FOR_DOCTORS=True)
    def test_doctors_can_be_forced_to_use_two_factor(self):
        make_user("doc", doctor=True)
        self.client.logout()
        self.client.login(username="doc", password=PASSWORD)
        self.assertRedirects(self.client.get(reverse("doctor_dashboard")), reverse("twofactor_setup"), fetch_redirect_response=False)
        enable_two_factor(User_of("doc"))
        self.assertEqual(self.client.get(reverse("doctor_dashboard")).status_code, 200)


# =============================================================================== rate-limit store (Redis)
class RateLimitStoreTests(FreshCacheTestCase):
    def broken_cache(self):
        cache = mock.MagicMock()
        for name in ("get", "add", "incr", "set", "delete"):
            getattr(cache, name).side_effect = ConnectionError("redis down")
        return cache

    def test_login_still_works_when_the_store_is_down(self):
        make_user("alice")
        with mock.patch("prediction.security.cache", self.broken_cache()):
            response = self.client.post(reverse("login"), {"username": "alice", "password": PASSWORD})
        self.assertEqual(response.status_code, 302)

    @override_settings(RATE_LIMIT_FAIL_OPEN=False)
    def test_fail_closed_blocks_when_the_store_is_down(self):
        make_user("alice")
        with mock.patch("prediction.security.cache", self.broken_cache()):
            response = self.client.post(reverse("login"), {"username": "alice", "password": PASSWORD})
        self.assertEqual(response.status_code, 429)

    def test_health_reports_which_store_is_used(self):
        body = self.client.get(reverse("api_health")).json()
        self.assertEqual(body["rate_limit_store"], "local-memory")
        self.assertTrue(body["rate_limit_store_ok"])

    def test_redis_is_used_when_redis_url_is_set(self):
        env = {**os.environ, "DJANGO_DEBUG": "1", "REDIS_URL": "redis://localhost:6379/0"}
        out = subprocess.run([sys.executable, "-c", "import heart_disease.settings as s; print(s.CACHES['default']['BACKEND'], s.CACHES['default']['KEY_PREFIX'])"],
                             env=env, cwd=settings.BASE_DIR, capture_output=True, text=True)
        self.assertIn("RedisCache cardionova", out.stdout, out.stderr)


# =============================================================================== drift monitoring
def sample_rows(n=120, shift=0):
    base = list(INPUTS.items())
    rows = []
    for i in range(n):
        row = dict(base)
        row["age"] = 40 + (i % 30) + shift
        row["chol"] = 180 + (i * 7) % 120
        row["trestbps"] = 110 + (i * 3) % 50
        row["thalach"] = 120 + (i * 5) % 70
        row["oldpeak"] = float(i % 4)
        row["sex"], row["cp"], row["ca"], row["thal"] = i % 2, 1 + i % 4, i % 4, (3, 6, 7)[i % 3]
        rows.append(row)
    return rows


class DriftCoreTests(SimpleTestCase):
    def setUp(self):
        self.rows = sample_rows(300)
        self.reference = drift.build_reference({k: [r[k] for r in self.rows] for k in self.rows[0]})

    def test_same_population_is_stable(self):
        result = drift.compare(self.reference, sample_rows(120))
        self.assertIn(result["overall"], ("stable",))
        self.assertEqual(result["flagged"], [])

    def test_shifted_age_is_flagged(self):
        result = drift.compare(self.reference, sample_rows(120, shift=25))
        self.assertEqual(result["overall"], "drift")
        self.assertIn("age", result["flagged"])

    def test_new_category_is_flagged(self):
        rows = sample_rows(120)
        for row in rows:
            row["cp"] = 9
        result = drift.compare(self.reference, rows)
        self.assertIn("cp", result["flagged"])
        self.assertIn("never seen", next(f for f in result["features"] if f["name"] == "cp")["detail"])

    def test_too_few_records_are_not_judged(self):
        self.assertEqual(drift.compare(self.reference, sample_rows(10))["overall"], "insufficient")

    def test_psi_of_identical_shares_is_zero(self):
        self.assertAlmostEqual(drift.psi([0.2, 0.3, 0.5], [0.2, 0.3, 0.5]), 0.0)
        self.assertGreater(drift.psi([0.2, 0.3, 0.5], [0.6, 0.3, 0.1]), 0.25)

    def test_out_of_range_names_only(self):
        self.assertEqual(drift.out_of_range({"age": 120, "chol": 200}, {"age": (30, 80), "chol": (100, 400)}), ["age"])


@needs_model
class DriftAppTests(FreshCacheTestCase):
    def test_reference_is_stored_with_the_model(self):
        reference = ml.model_info().get("drift_reference")
        self.assertTrue(reference and reference["n"] > 100 and set(reference["numeric"]) == set(drift.NUMERIC))

    def test_command_reports_not_enough_data(self):
        out = StringIO()
        call_command("drift_report", stdout=out)
        self.assertIn("Not enough data", out.getvalue())

    def test_command_finds_drift_and_can_fail(self):
        user = make_user("alice")
        for _ in range(40):
            make_record(user, age=80, chol=500)                 # 40 identical, unusual records
        out = StringIO()
        call_command("drift_report", stdout=out)
        self.assertIn("DRIFT", out.getvalue())
        with self.assertRaises(CommandError):
            call_command("drift_report", "--fail-on-drift", stdout=StringIO())

    def test_page_is_for_staff_only(self):
        make_user("alice")
        self.client.login(username="alice", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("drift_report")).status_code, 403)
        staff = make_user("boss")
        staff.is_staff = True
        staff.save()
        self.client.login(username="boss", password=PASSWORD)
        self.assertContains(self.client.get(reverse("drift_report")), "Input drift monitor")

    def test_saving_an_unusual_prediction_logs_feature_names_only(self):
        user = make_user("alice")
        values = {**INPUTS, "age": 99, "chol": 600}
        with self.assertLogs("prediction.drift", level="WARNING") as captured:
            views.save_prediction(user, values, "x", PredictionRecord.SOURCE_FORM, 0.4, [])
        message = captured.output[0]
        self.assertIn("age", message)
        self.assertNotIn("99", message)
        self.assertNotIn("600", message)


# =============================================================================== experiment tracking
class TrackingTests(SimpleTestCase):
    def setUp(self):
        self.info = json.loads((settings.BASE_DIR / "model" / "model_info.json").read_text())
        self.tmp = Path(tempfile.mkdtemp())

    def record(self, **kwargs):
        return tracking.record(self.info, settings.BASE_DIR / "dataset" / "heart.csv", settings.BASE_DIR / "model" / "heart_disease_model.pkl",
                               self.tmp / "experiments.jsonl", 42, **kwargs)

    def test_every_run_is_logged_with_a_data_fingerprint(self):
        summary, sent = self.record()
        self.assertFalse(sent)
        self.assertEqual(len(summary["dataset_sha256"]), 16)
        self.assertEqual(len(tracking.latest_runs(self.tmp / "experiments.jsonl")), 1)

    def test_mlflow_receives_params_metrics_and_artifacts(self):
        calls = []
        fake = types.ModuleType("mlflow")

        class Run:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False
        fake.set_tracking_uri = lambda uri: calls.append(("uri", uri))
        fake.set_experiment = lambda name: calls.append(("experiment", name))
        fake.start_run = lambda run_name=None: Run()
        fake.log_params = lambda params: calls.append(("params", params))
        fake.log_metrics = lambda metrics: calls.append(("metrics", metrics))
        fake.set_tags = lambda tags: calls.append(("tags", tags))
        fake.log_artifact = lambda path: calls.append(("artifact", path))
        with mock.patch.dict(sys.modules, {"mlflow": fake}):
            _, sent = self.record(use_mlflow=True, artifacts=[settings.BASE_DIR / "model" / "model_info.json"])
        self.assertTrue(sent)
        kinds = [c[0] for c in calls]
        for needed in ("experiment", "params", "metrics", "tags", "artifact"):
            self.assertIn(needed, kinds)

    def test_without_mlflow_installed_the_run_is_still_saved(self):
        with mock.patch.dict(sys.modules, {"mlflow": None}):
            _, sent = self.record(use_mlflow=True)
        self.assertFalse(sent)
        self.assertTrue((self.tmp / "experiments.jsonl").exists())



class TrackingPageTests(FreshCacheTestCase):
    def test_model_page_lists_training_runs(self):
        self.assertContains(self.client.get(reverse("model")), "experiment log")
