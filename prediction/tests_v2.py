"""
Tests for the version-2 features: the 20 website features, the two innovations (trust check and what-if simulator)
and the 20-point security checklist. Run everything with:  python manage.py test
"""
import json
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from . import ml
from .models import ContactMessage, DoctorAccessLog, PredictionRecord, Profile
from .tests import PASSWORD, VALID, make_user, needs_model

INPUTS = {k: v for k, v in VALID.items() if k != "patient_label"}
STATIC = Path(__file__).resolve().parent / "static" / "prediction"


def make_record(user, label="", **extra):
    return PredictionRecord.objects.create(user=user, patient_label=label, probability=55.0,
                                           risk_level="MODERATE", **{**INPUTS, **extra})


class FreshCacheTestCase(TestCase):
    """Rate-limit counters live in the cache: start every test with an empty one."""

    def setUp(self):
        cache.clear()


# =============================================================================== 20 website features
class WebsiteFeatureTests(FreshCacheTestCase):
    def test_every_page_has_the_shared_ui_features(self):
        html = self.client.get(reverse("home")).content.decode()
        hooks = {
            "1 dark mode toggle": 'id="theme-toggle"', "2 cookie banner": 'id="cookie-banner"',
            "3 site search": 'action="/search/"', "4 back to top": 'id="back-to-top"',
            "5 mobile menu": 'id="nav-toggle"', "6 loading animation": 'id="page-loader"',
            "8 scroll progress": 'id="scroll-progress"', "10 print stylesheet": "print.css",
            "11 sticky header": 'id="site-header"', "12 skip to content": 'class="skip-link"',
            "17 confirmation dialog": 'id="confirm-dialog"', "18 last updated": "Last updated:",
            "20 floating contact": "fab-contact", "theme without flash": "theme-init.js",
        }
        for name, needle in hooks.items():
            self.assertIn(needle, html, name)

    def test_front_end_files_implement_the_behaviour(self):
        js = (STATIC / "js" / "main.js").read_text()
        css = (STATIC / "css" / "style.css").read_text()
        for needle in ("pw-toggle", "data-copy", "scroll-progress", "back-to-top", "cookie-notice",
                       "confirm-dialog", "aria-expanded", "theme"):
            self.assertIn(needle, js, needle)
        for needle in ('[data-theme="dark"]', "position: sticky", ".faq-item", ".pw-toggle", ":hover", ".spinner"):
            self.assertIn(needle, css, needle)
        self.assertIn("display: none !important", (STATIC / "css" / "print.css").read_text())

    def test_faq_is_expandable(self):
        html = self.client.get(reverse("faq")).content.decode()
        self.assertIn("<details", html)
        self.assertIn("<summary>", html)

    def test_privacy_page(self):
        self.assertContains(self.client.get(reverse("privacy")), "sessionid")

    def test_password_fields_exist_for_the_toggle(self):
        self.assertContains(self.client.get(reverse("login")), 'type="password"')
        self.assertContains(self.client.get(reverse("register")), 'type="password"')

    def test_logged_in_pages_have_confirmation_buttons(self):
        make_user("alice")
        self.client.login(username="alice", password=PASSWORD)
        self.assertContains(self.client.get(reverse("home")), "data-confirm")          # logout
        self.assertContains(self.client.get(reverse("profile")), "data-copy")          # copy example
        self.assertContains(self.client.get(reverse("profile")), "Delete my account")

    # ---- 14 UTM tracking
    def test_utm_first_touch_is_saved_at_registration(self):
        self.client.get("/?utm_source=linkedin&utm_medium=social&utm_campaign=portfolio")
        self.client.get("/?utm_source=other")                                        # first touch wins
        self.client.post(reverse("register"), {"username": "utmuser", "email": "u@example.com",
                                               "password1": PASSWORD, "password2": PASSWORD})
        prof = Profile.objects.get(user__username="utmuser")
        self.assertEqual((prof.utm_source, prof.utm_medium, prof.utm_campaign), ("linkedin", "social", "portfolio"))

    def test_utm_with_unsafe_characters_is_ignored(self):
        self.client.get("/?utm_source=%3Cscript%3Ealert(1)%3C/script%3E")
        self.client.post(reverse("register"), {"username": "utmbad", "email": "b@example.com",
                                               "password1": PASSWORD, "password2": PASSWORD})
        self.assertEqual(Profile.objects.get(user__username="utmbad").utm_source, "")

    # ---- 3 site search
    def test_search_finds_public_pages_and_faq_but_not_private_pages_for_visitors(self):
        html = self.client.get(reverse("search"), {"q": "cookies"}).content.decode()
        self.assertIn("Privacy and cookies", html)
        html = self.client.get(reverse("search"), {"q": "batch"}).content.decode()
        self.assertNotIn("Batch CSV prediction", html)

    def test_search_only_returns_my_own_predictions(self):
        alice, bob = make_user("alice"), make_user("bob")
        make_record(alice, label="Alice-secret-label")
        make_record(bob, label="Bob-secret-label")
        self.client.login(username="alice", password=PASSWORD)
        html = self.client.get(reverse("search"), {"q": "secret-label"}).content.decode()
        self.assertIn("Alice-secret-label", html)
        self.assertNotIn("Bob-secret-label", html)

    def test_search_input_is_escaped_and_sql_safe(self):
        response = self.client.get(reverse("search"), {"q": "<script>alert(1)</script>' OR 1=1 --"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("<script>alert(1)</script>", response.content.decode())

    # ---- 15 / 16 form success and error states, 20 contact
    def test_contact_form_success_state_and_storage(self):
        response = self.client.post(reverse("contact"), {"name": "Ravi", "email": "r@example.com",
                                                         "message": "Hello, a question about the model.", "website": ""})
        self.assertEqual(response.status_code, 302)
        page = self.client.get(response["Location"]).content.decode()
        self.assertIn("form-state-success", page)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(len(ContactMessage.objects.get().ip_hash), 16)

    def test_contact_form_error_state(self):
        response = self.client.post(reverse("contact"), {"name": "", "email": "not-an-email", "message": "short"})
        html = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("form-state-error", html)
        self.assertIn("has-error", html)
        self.assertIn('role="alert"', html)
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_contact_honeypot_blocks_bots_silently(self):
        response = self.client.post(reverse("contact"), {"name": "Bot", "email": "b@example.com",
                                                         "message": "Buy cheap things now please", "website": "http://spam"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_contact_html_is_removed(self):
        self.client.post(reverse("contact"), {"name": "<b>Ravi</b>", "email": "r@example.com",
                                              "message": "Hello <script>alert(1)</script> there, nice project", "website": ""})
        stored = ContactMessage.objects.get()
        self.assertNotIn("<", stored.name + stored.message)

    def test_contact_is_rate_limited(self):
        data = {"name": "Ravi", "email": "r@example.com", "message": "A valid message text", "website": ""}
        codes = [self.client.post(reverse("contact"), data).status_code for _ in range(6)]
        self.assertEqual(codes[:5], [302] * 5)
        self.assertEqual(codes[5], 429)

    def test_form_error_state_on_login(self):
        response = self.client.post(reverse("login"), {"username": "nobody", "password": "wrong"})
        self.assertContains(response, "form-state-error")


# =============================================================================== innovations
@needs_model
class InnovationTests(FreshCacheTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user("alice")
        self.record = make_record(self.user)
        self.client.login(username="alice", password=PASSWORD)
        self.url = reverse("whatif", args=[self.record.pk])

    def post(self, payload, url=None):
        return self.client.post(url or self.url, data=json.dumps(payload), content_type="application/json")

    def test_result_page_shows_trust_check_and_simulator(self):
        html = self.client.get(reverse("result", args=[self.record.pk])).content.decode()
        self.assertIn("Trust check", html)
        self.assertIn('id="whatif"', html)
        self.assertIn("Copy summary", html)

    def test_whatif_returns_before_and_after(self):
        response = self.post({"changes": {"trestbps": 120, "chol": 200}})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body), {"before", "after", "delta", "risk_level"})
        self.assertIn(body["risk_level"], ("LOW", "MODERATE", "HIGH"))

    def test_whatif_rejects_unchangeable_or_invalid_values(self):
        for payload in ({"changes": {"age": 20}}, {"changes": {"trestbps": 9999}}, {"changes": {"chol": "abc"}},
                        {"changes": {}}, {"nothing": 1}, ["list"]):
            self.assertEqual(self.post(payload).status_code, 400, payload)

    def test_whatif_ignores_user_ids_and_uses_stored_values(self):
        bob = make_user("bob")
        other = make_record(bob, age=80)
        # a forged id in the body does nothing: the record comes from the URL and is permission-checked
        self.assertEqual(self.post({"changes": {"chol": 200}, "record": other.pk, "user_id": bob.pk}).status_code, 200)
        self.assertEqual(self.post({"changes": {"chol": 200}}, reverse("whatif", args=[other.pk])).status_code, 403)

    def test_whatif_needs_login_and_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.post({"changes": {"chol": 200}}).status_code, 302)

    @override_settings(RATE_LIMITS={**settings.RATE_LIMITS, "whatif": (2, 60)})
    def test_whatif_is_rate_limited(self):
        codes = [self.post({"changes": {"chol": 200}}).status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])

    def test_reliability_flags_unusual_inputs(self):
        usual = ml.reliability({**INPUTS})
        unusual = ml.reliability({**INPUTS, "age": 119, "chol": 590, "trestbps": 245})
        self.assertIn(usual["level"], ("good", "fair", "low"))
        self.assertIn(unusual["level"], ("fair", "low"))
        self.assertTrue(any("Unusual" in reason for reason in unusual["reasons"]))

    def test_api_whatif_and_trust_in_predict(self):
        token = Profile.objects.get(user=self.user).new_api_token()
        auth = {"HTTP_AUTHORIZATION": f"Token {token}"}
        body = self.client.post(reverse("api_predict"), data=json.dumps(INPUTS), content_type="application/json", **auth).json()
        self.assertIn(body["reliability"]["level"], ("good", "fair", "low"))
        response = self.client.post(reverse("api_whatif"), data=json.dumps({**INPUTS, "changes": {"chol": 200}}),
                                    content_type="application/json", **auth)
        self.assertEqual(response.status_code, 200)
        bad = self.client.post(reverse("api_whatif"), data=json.dumps({**INPUTS, "changes": {"age": 1}}),
                               content_type="application/json", **auth)
        self.assertEqual(bad.status_code, 400)


# =============================================================================== security checklist
class SecuritySettingsTests(FreshCacheTestCase):
    def test_03_no_hard_coded_secret(self):
        self.assertNotIn("django-insecure", settings.SECRET_KEY)
        self.assertGreaterEqual(len(settings.SECRET_KEY), 32)

    def test_19_security_headers_and_no_cors(self):
        response = self.client.get(reverse("home"))
        self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])
        self.assertIn("script-src 'self'", response["Content-Security-Policy"])
        self.assertNotIn("'unsafe-inline'", response["Content-Security-Policy"])
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["Referrer-Policy"], "same-origin")
        self.assertIn("camera=()", response["Permissions-Policy"])
        self.assertNotIn("Access-Control-Allow-Origin", response)
        api = self.client.get(reverse("api_health"), HTTP_ORIGIN="https://evil.example")
        self.assertNotIn("Access-Control-Allow-Origin", api)

    def test_19_private_pages_are_not_cached(self):
        self.assertNotIn("no-store", self.client.get(reverse("home")).get("Cache-Control", ""))
        make_user("alice")
        self.client.login(username="alice", password=PASSWORD)
        self.assertIn("no-store", self.client.get(reverse("history"))["Cache-Control"])

    def test_12_error_pages_hide_details(self):
        response = self.client.get("/definitely/not/here/")
        self.assertEqual(response.status_code, 404)
        html = response.content.decode()
        for leak in ("Traceback", "Request URL", "django.urls", "settings.py", "DEBUG"):
            self.assertNotIn(leak, html)
        self.assertEqual(self.client.get("/api/nothing/").json(), {"error": "Page not found"})

    def test_12_forbidden_page_is_friendly(self):
        make_user("alice")
        self.client.login(username="alice", password=PASSWORD)
        response = self.client.get(reverse("doctor_dashboard"))
        self.assertContains(response, "Access denied", status_code=403)

    def test_10_admin_requires_login_and_can_be_limited_to_ips(self):
        response = self.client.get("/" + settings.ADMIN_URL)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])
        with override_settings(ADMIN_ALLOWED_IPS=["10.9.8.7"]):
            self.assertEqual(self.client.get("/" + settings.ADMIN_URL + "login/").status_code, 404)

    def test_10_normal_user_cannot_use_admin(self):
        make_user("alice")
        self.client.login(username="alice", password=PASSWORD)
        response = self.client.get("/" + settings.ADMIN_URL)
        self.assertEqual(response.status_code, 302)            # sent to the admin login, not allowed in

    def test_10_admin_login_is_throttled(self):
        with override_settings(RATE_LIMITS={**settings.RATE_LIMITS, "admin_login": (2, 60)}):
            url = "/" + settings.ADMIN_URL + "login/"
            codes = [self.client.post(url, {"username": "x", "password": "y"}).status_code for _ in range(3)]
        self.assertEqual(codes[2], 429)

    def test_15_oversized_request_is_rejected(self):
        make_user("alice")
        self.client.login(username="alice", password=PASSWORD)
        big = SimpleUploadedFile("big.csv", b"a,b\n" + b"1,2\n" * 800_000, content_type="text/csv")
        self.assertEqual(self.client.post(reverse("batch"), {"file": big}).status_code, 413)

    def test_15_upload_rules(self):
        make_user("alice")
        self.client.login(username="alice", password=PASSWORD)
        cases = {
            "wrong extension": SimpleUploadedFile("x.exe", b"age\n1\n", content_type="text/csv"),
            "binary content": SimpleUploadedFile("x.csv", b"\x00\x01\x02\x03binary", content_type="text/csv"),
            "wrong type": SimpleUploadedFile("x.csv", b"age\n1\n", content_type="image/png"),
            "just over 1 MB": SimpleUploadedFile("x.csv", b"a,b\n" + b"1,2\n" * 270_000, content_type="text/csv"),
        }
        for name, upload in cases.items():
            response = self.client.post(reverse("batch"), {"file": upload, "action": "predict"})
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(response, "has-error", msg_prefix=name)
        self.assertEqual(PredictionRecord.objects.count(), 0)

    def test_17_login_lockout_per_user_and_ip(self):
        make_user("victim")
        make_user("other")
        for _ in range(5):
            self.assertEqual(self.client.post(reverse("login"), {"username": "victim", "password": "wrong"}).status_code, 200)
        locked = self.client.post(reverse("login"), {"username": "victim", "password": PASSWORD})
        self.assertEqual(locked.status_code, 429)                       # even the right password is refused for now
        self.assertIn("Retry-After", locked)
        self.assertEqual(self.client.post(reverse("login"), {"username": "other", "password": PASSWORD}).status_code, 302)

    def test_17_successful_login_resets_the_counter(self):
        make_user("alice")
        for _ in range(3):
            self.client.post(reverse("login"), {"username": "alice", "password": "wrong"})
        self.assertEqual(self.client.post(reverse("login"), {"username": "alice", "password": PASSWORD}).status_code, 302)
        self.client.logout()
        for _ in range(4):
            self.client.post(reverse("login"), {"username": "alice", "password": "wrong"})
        self.assertEqual(self.client.post(reverse("login"), {"username": "alice", "password": PASSWORD}).status_code, 302)

    @override_settings(RATE_LIMITS={**settings.RATE_LIMITS, "register": (2, 60)})
    def test_17_signup_is_rate_limited(self):
        codes = []
        for i in range(3):
            codes.append(self.client.post(reverse("register"), {"username": f"u{i}", "email": f"u{i}@example.com",
                                                                "password1": PASSWORD, "password2": PASSWORD}).status_code)
            self.client.logout()
        self.assertEqual(codes[2], 429)

    def test_17_spoofed_forwarded_header_does_not_bypass_the_limit(self):
        make_user("victim")
        with override_settings(TRUSTED_PROXY_COUNT=1):
            for i in range(5):                 # the attacker sends a new fake first entry each time
                self.client.post(reverse("login"), {"username": "victim", "password": "x"},
                                 HTTP_X_FORWARDED_FOR=f"6.6.6.{i}, 9.9.9.9")
            blocked = self.client.post(reverse("login"), {"username": "victim", "password": PASSWORD},
                                       HTTP_X_FORWARDED_FOR="7.7.7.7, 9.9.9.9")
        self.assertEqual(blocked.status_code, 429)

    def test_04_private_pages_need_login(self):
        for name, args in (("predict", []), ("history", []), ("batch", []), ("profile", []), ("result", [1]),
                           ("download_report", [1]), ("doctor_dashboard", []), ("batch_template", [])):
            response = self.client.get(reverse(name, args=args))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn("/login/", response["Location"], name)
        for name, args in (("whatif", [1]), ("delete_record", [1]), ("delete_account", [])):
            self.assertEqual(self.client.post(reverse(name, args=args)).status_code, 302, name)

    def test_04_csrf_is_enforced_on_state_changing_pages(self):
        user = make_user("alice")
        record = make_record(user)
        strict = Client(enforce_csrf_checks=True)
        strict.login(username="alice", password=PASSWORD)
        self.assertEqual(strict.post(reverse("delete_record", args=[record.pk])).status_code, 403)
        self.assertTrue(PredictionRecord.objects.filter(pk=record.pk).exists())

    def test_05_06_07_users_cannot_touch_each_others_data(self):
        alice, bob = make_user("alice"), make_user("bob")
        record = make_record(alice, label="Zq9-hidden-label")
        self.client.login(username="bob", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("result", args=[record.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("download_report", args=[record.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("delete_record", args=[record.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("history")), "Zq9-hidden-label")
        self.assertNotContains(self.client.get(reverse("home")), "Zq9-hidden-label")
        self.assertTrue(PredictionRecord.objects.filter(pk=record.pk).exists())

    def test_05_patient_cannot_become_doctor(self):
        make_user("alice")
        self.client.login(username="alice", password=PASSWORD)
        self.client.post(reverse("profile"), {"role": "doctor", "share_with_doctors": "on"})
        self.assertEqual(Profile.objects.get(user__username="alice").role, Profile.ROLE_PATIENT)

    def test_05_doctor_views_are_logged_for_the_patient(self):
        patient, doctor = make_user("pat"), make_user("drhouse", doctor=True)
        Profile.objects.filter(user=patient).update(share_with_doctors=True)             # sharing is opt-in
        record = make_record(patient)
        self.client.login(username="drhouse", password=PASSWORD)
        self.client.get(reverse("doctor_patient", args=[patient.pk]))
        self.client.get(reverse("result", args=[record.pk]))
        self.assertEqual(DoctorAccessLog.objects.filter(patient=patient, doctor=doctor).count(), 2)
        self.client.logout()
        self.client.login(username="pat", password=PASSWORD)
        self.assertContains(self.client.get(reverse("profile")), "drhouse")
        make_record(doctor)                                   # a doctor opening their OWN data is not logged
        self.client.logout()
        self.client.login(username="drhouse", password=PASSWORD)
        self.client.get(reverse("result", args=[PredictionRecord.objects.get(user=doctor).pk]))
        self.assertEqual(DoctorAccessLog.objects.filter(patient=doctor).count(), 0)

    def test_14_user_text_is_escaped_in_pages(self):
        user = make_user("alice")
        record = make_record(user, label='"><img src=x onerror=alert(1)>')       # stored without any clean-up (worst case)
        self.client.login(username="alice", password=PASSWORD)
        for url in (reverse("result", args=[record.pk]), reverse("history"), reverse("home")):
            html = self.client.get(url).content.decode()
            self.assertNotIn("<img src=x", html, url)
            self.assertIn("&lt;img", html, url)

    @needs_model
    def test_14_label_is_cleaned_when_saved(self):
        make_user("alice")
        self.client.login(username="alice", password=PASSWORD)
        self.client.post(reverse("predict"), {**VALID, "patient_label": "<script>alert(1)</script>Ravi"})
        self.assertEqual(PredictionRecord.objects.get().patient_label, "alert(1)Ravi")

    @needs_model
    def test_14_pdf_report_survives_markup_in_the_label(self):
        user = make_user("alice")
        record = make_record(user, label='<img src="file:///etc/passwd"/><b>x')
        self.client.login(username="alice", password=PASSWORD)
        response = self.client.get(reverse("download_report", args=[record.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))

    @needs_model
    def test_14_csv_export_neutralises_formulas(self):
        make_user("alice")
        self.client.login(username="alice", password=PASSWORD)
        csv_text = "label," + ",".join(ml.FEATURES) + "\n" + "=HYPERLINK(\"http://evil\")," + ",".join(str(INPUTS[f]) for f in ml.FEATURES) + "\n"
        upload = SimpleUploadedFile("p.csv", csv_text.encode(), content_type="text/csv")
        response = self.client.post(reverse("batch"), {"file": upload, "action": "download"})
        body = response.content.decode()
        self.assertIn("'=HYPERLINK", body)
        self.assertNotIn("\n=HYPERLINK", body)

    def test_16_query_strings_cannot_inject_sql(self):
        user = make_user("alice")
        make_user("bob")
        make_record(user)
        self.client.login(username="alice", password=PASSWORD)
        for params in ({"level": "' OR 1=1 --"}, {"page": "1; DROP TABLE prediction_predictionrecord"}, {"level": "LOW' --"}):
            self.assertEqual(self.client.get(reverse("history"), params).status_code, 200)
        self.assertEqual(PredictionRecord.objects.count(), 1)

    def test_api_requires_token_and_is_rate_limited(self):
        self.assertEqual(self.client.post(reverse("api_whatif"), data="{}", content_type="application/json").status_code, 401)
        user = make_user("alice")
        token = Profile.objects.get(user=user).new_api_token()
        auth = {"HTTP_AUTHORIZATION": f"Token {token}"}
        with override_settings(RATE_LIMITS={**settings.RATE_LIMITS, "api": (2, 60)}):
            codes = [self.client.get(reverse("api_history"), **auth).status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])

    def test_delete_account_needs_the_password(self):
        user = make_user("alice")
        make_record(user)
        self.client.login(username="alice", password=PASSWORD)
        self.client.post(reverse("delete_account"), {"password": "wrong"})
        self.assertTrue(User.objects.filter(username="alice").exists())
        self.client.post(reverse("delete_account"), {"password": PASSWORD})
        self.assertFalse(User.objects.filter(username="alice").exists())
        self.assertEqual(PredictionRecord.objects.count(), 0)

    def test_delete_record_by_owner(self):
        user = make_user("alice")
        record = make_record(user)
        self.client.login(username="alice", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("delete_record", args=[record.pk])).status_code, 405)
        self.client.post(reverse("delete_record", args=[record.pk]))
        self.assertFalse(PredictionRecord.objects.filter(pk=record.pk).exists())

    def test_18_repository_scan_finds_no_secrets(self):
        script = Path(settings.BASE_DIR) / "scripts" / "security_check.py"
        result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, cwd=settings.BASE_DIR)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
