import json
import unittest

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from . import batch, ml
from .forms import PredictionForm
from .models import PredictionRecord, Profile

needs_model = unittest.skipUnless(ml.MODEL_FILE.exists() and ml.SCALER_FILE.exists(),
                                  "model files are missing (run python train_model.py)")

VALID = {"patient_label": "", "age": 55, "sex": 1, "cp": 4, "trestbps": 140, "chol": 250, "fbs": 0,
         "restecg": 1, "thalach": 130, "exang": 1, "oldpeak": 2.0, "slope": 2, "ca": 1, "thal": 7}
PASSWORD = "S3cure-pass-123"


def make_user(name, doctor=False):
    user = User.objects.create_user(name, f"{name}@example.com", PASSWORD)
    if doctor:
        Profile.objects.filter(user=user).update(role=Profile.ROLE_DOCTOR)
    return user


class RiskLevelTests(SimpleTestCase):
    def test_limits(self):
        self.assertEqual(ml.risk_level(0.0), "LOW")
        self.assertEqual(ml.risk_level(0.299), "LOW")
        self.assertEqual(ml.risk_level(0.30), "MODERATE")
        self.assertEqual(ml.risk_level(0.599), "MODERATE")
        self.assertEqual(ml.risk_level(0.60), "HIGH")
        self.assertEqual(ml.risk_level(1.0), "HIGH")


class FormCodingTests(SimpleTestCase):
    def test_form_choices_match_ml_rules(self):
        for name, allowed in ml.CATEGORY_VALUES.items():
            choices = {value for value, _ in PredictionForm.base_fields[name].choices}
            self.assertEqual(choices, allowed, name)

    def test_out_of_range_rejected(self):
        form = PredictionForm({**VALID, "age": 200})
        self.assertFalse(form.is_valid())
        self.assertIn("age", form.errors)


@needs_model
class BatchModuleTests(SimpleTestCase):
    def test_validate_and_predict(self):
        text = batch.sample_csv() + "Bad,200,1,4,140,250,0,1,130,1,2.0,2,1,7\n"
        valid, errors = batch.validate(batch.parse(text.encode()))
        self.assertEqual(len(valid), 1)
        self.assertEqual(errors[0][0], 3)
        result = batch.predict(valid)
        self.assertIn(result.loc[0, "risk_level"], ("LOW", "MODERATE", "HIGH"))

    def test_missing_column(self):
        with self.assertRaises(batch.BatchError):
            batch.parse(b"age,sex\n50,1\n")


class AccountTests(TestCase):
    def test_register_creates_patient_profile(self):
        response = self.client.post(reverse("register"), {
            "username": "newuser", "email": "new@example.com",
            "password1": PASSWORD, "password2": PASSWORD})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Profile.objects.get(user__username="newuser").role, Profile.ROLE_PATIENT)

    def test_predict_requires_login(self):
        response = self.client.get(reverse("predict"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])


@needs_model
class PredictionFlowTests(TestCase):
    def setUp(self):
        self.user = make_user("alice")
        self.client.login(username="alice", password=PASSWORD)

    def test_predict_saves_record_with_explanation(self):
        response = self.client.post(reverse("predict"), VALID)
        self.assertEqual(response.status_code, 302)
        record = PredictionRecord.objects.get(user=self.user)
        self.assertIn(record.risk_level, ("LOW", "MODERATE", "HIGH"))
        self.assertIsInstance(record.explanation, list)
        self.assertEqual(self.client.get(reverse("result", args=[record.pk])).status_code, 200)

    def test_pdf_report(self):
        self.client.post(reverse("predict"), VALID)
        record = PredictionRecord.objects.get(user=self.user)
        response = self.client.get(reverse("download_report", args=[record.pk]))
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_other_patient_cannot_open_result(self):
        self.client.post(reverse("predict"), VALID)
        record = PredictionRecord.objects.get(user=self.user)
        make_user("bob")
        self.client.logout()
        self.client.login(username="bob", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("result", args=[record.pk])).status_code, 403)

    def test_history_and_batch_upload(self):
        self.assertEqual(self.client.get(reverse("history")).status_code, 200)
        upload = SimpleUploadedFile("p.csv", batch.sample_csv().encode(), content_type="text/csv")
        response = self.client.post(reverse("batch"), {"file": upload, "action": "predict"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PredictionRecord.objects.filter(user=self.user, source="batch").count(), 1)


@needs_model
class DoctorTests(TestCase):
    def setUp(self):
        self.patient = make_user("pat")
        self.doctor = make_user("doc", doctor=True)
        self.client.login(username="pat", password=PASSWORD)
        self.client.post(reverse("predict"), VALID)
        self.record = PredictionRecord.objects.get(user=self.patient)
        self.client.logout()

    def test_patient_cannot_open_doctor_dashboard(self):
        self.client.login(username="pat", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("doctor_dashboard")).status_code, 403)

    def test_doctor_sees_shared_patient(self):
        self.client.login(username="doc", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("doctor_dashboard")).status_code, 200)
        self.assertEqual(self.client.get(reverse("doctor_patient", args=[self.patient.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("result", args=[self.record.pk])).status_code, 200)

    def test_doctor_blocked_when_patient_stops_sharing(self):
        Profile.objects.filter(user=self.patient).update(share_with_doctors=False)
        self.client.login(username="doc", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("doctor_patient", args=[self.patient.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("result", args=[self.record.pk])).status_code, 403)


@needs_model
class ApiTests(TestCase):
    def setUp(self):
        self.user = make_user("apiuser")
        self.token = Profile.objects.get(user=self.user).new_api_token()
        self.auth = {"HTTP_AUTHORIZATION": f"Token {self.token}"}

    def post(self, payload, **extra):
        return self.client.post(reverse("api_predict"), data=json.dumps(payload),
                                content_type="application/json", **extra)

    def test_health_needs_no_token(self):
        self.assertEqual(self.client.get(reverse("api_health")).status_code, 200)

    def test_token_required(self):
        self.assertEqual(self.post(VALID).status_code, 401)
        self.assertEqual(self.post(VALID, HTTP_AUTHORIZATION="Token wrong").status_code, 401)

    def test_predict_and_save(self):
        response = self.post({**VALID, "save": True}, **self.auth)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn(body["risk_level"], ("LOW", "MODERATE", "HIGH"))
        self.assertTrue(PredictionRecord.objects.filter(pk=body["record_id"], source="api").exists())
        history = self.client.get(reverse("api_history"), **self.auth).json()
        self.assertEqual(history["count"], 1)

    def test_invalid_input(self):
        response = self.post({**VALID, "age": 500}, **self.auth)
        self.assertEqual(response.status_code, 400)
        self.assertIn("age", response.json()["fields"])
