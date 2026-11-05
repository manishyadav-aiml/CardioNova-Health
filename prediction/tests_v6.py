"""
Tests for the clinical-style PDF report: layout (two pages), robustness against odd data, safe text, report number.
Run with:  python manage.py test
"""
import datetime
import re
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.urls import reverse

from . import report, views
from .tests import PASSWORD, make_user, needs_model
from .tests_v2 import FreshCacheTestCase, make_record

VALUES = dict(age=58, sex=1, cp=4, trestbps=140, chol=260, fbs=0, restecg=1, thalach=130, exang=1, oldpeak=2.0, slope=2, ca=1, thal=7)
ROWS = [(name, str(VALUES[name])) for name in report.FEATURE_ORDER]
EXPLANATION = [{"feature": "cp", "label": "Chest pain type", "value": "Asymptomatic", "delta": 16.6},
               {"feature": "age", "label": "Age", "value": "58", "delta": -3.7},
               {"feature": "chol", "label": "Cholesterol", "value": "260", "delta": 1.5}]
LOW_TRUST = {"level": "low", "label": "Low", "range": (1.4, 28.9),
             "reasons": ["Unusual compared with the training data: Age, Cholesterol.", "The fold models disagree strongly.", "Heart rate looks like a resting pulse."]}
NARRATIVE = {"summary": "The model estimates a high probability of heart disease (91.0%) for the values entered.",
             "points": ["Chest pain type (Asymptomatic) raised the estimate by about 16.6 percentage points compared with a typical patient in the training data."],
             "questions": ["What does an estimate like this mean for someone with my history and symptoms?"]}


def record(**changes):
    data = dict(VALUES, risk_level="HIGH", probability=91.0, patient_label="Asha Patel", model_name="Gradient Boosting",
                created_at=datetime.datetime(2026, 11, 5, 10, 30), explanation=EXPLANATION, pk=1)
    data.update(changes)
    return SimpleNamespace(**data)


def page_count(pdf):
    return len(re.findall(rb"/Type\s*/Page(?!s)", pdf))


class ReportBuilderTests(SimpleTestCase):
    def test_typical_report_is_a_two_page_pdf(self):
        pdf = report.build_report(record(), ROWS, None, "Discuss this with a clinician.", {"level": "good", "label": "Good", "range": (89.9, 97.3), "reasons": []}, NARRATIVE)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(page_count(pdf), 2)

    def test_the_worst_case_with_a_low_reliability_box_still_fits_two_pages(self):
        pdf = report.build_report(record(risk_level="LOW", probability=9.7), ROWS, None, "Advice text.", LOW_TRUST, NARRATIVE)
        self.assertEqual(page_count(pdf), 2)

    def test_moderate_label_does_not_wrap(self):
        # "MODERATE" is the longest risk word; the card shrinks its font instead of breaking the word
        pdf = report.build_report(record(risk_level="MODERATE", probability=39.7), ROWS, None, "", None, None)
        self.assertEqual(page_count(pdf), 2)

    def test_hostile_text_is_escaped_not_interpreted(self):
        hostile = "<b>bold</b> <script>alert(1)</script> & <font color='red'>"
        explanation = [{"feature": "age", "label": hostile, "value": hostile, "delta": 2.0}]
        pdf = report.build_report(record(patient_label=hostile, explanation=explanation), ROWS, None, hostile,
                                  {"level": "low", "label": "Low", "range": None, "reasons": [hostile]}, {"summary": hostile, "points": [hostile], "questions": [hostile]})
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_missing_data_never_breaks_the_report(self):
        for rec in (SimpleNamespace(), record(created_at=None, explanation=[], patient_label=""), record(probability=None, risk_level="UNKNOWN"),
                    record(explanation=[{"label": "x", "value": "y", "delta": "not a number"}]), record(probability=100.0), record(probability=0.0)):
            self.assertTrue(report.build_report(rec, [], None, "", None, None).startswith(b"%PDF"))

    def test_fallback_report_number_is_not_the_database_id(self):
        from reportlab import rl_config
        old = rl_config.invariant
        rl_config.invariant = 1                                      # reportlab then writes no random document id or timestamp
        try:
            one = report.build_report(record(pk=1), ROWS, None, "", None, None)
            two = report.build_report(record(pk=2), ROWS, None, "", None, None)
        finally:
            rl_config.invariant = old
        self.assertEqual(one, two)                                   # same content, different ids: nothing from the id is printed

    def test_status_rules_follow_the_documented_guides(self):
        self.assertEqual(report._guide_and_status("trestbps", 118, 50)[1], "Within guide")
        self.assertEqual(report._guide_and_status("trestbps", 125, 50)[1], "Borderline")
        self.assertEqual(report._guide_and_status("trestbps", 150, 50)[1], "Above guide")
        self.assertEqual(report._guide_and_status("chol", 245, 50)[1], "Above guide")
        self.assertEqual(report._guide_and_status("chol", 110, 50)[1], "Check value")
        self.assertEqual(report._guide_and_status("thalach", 62, 21)[1], "Check value")           # a resting pulse, not an exercise maximum
        self.assertEqual(report._guide_and_status("thalach", 150, 50)[1], "Within guide")
        self.assertEqual(report._guide_and_status("thalach", 120, 50)[1], "Below age guide")
        self.assertEqual(report._guide_and_status("exang", 1, 50)[1], "Present")
        self.assertEqual(report._guide_and_status("thal", 7, 50)[1], "Defect reported")
        self.assertEqual(report._guide_and_status("age", 50, 50)[2], None)                         # no status for age


@needs_model
class ReportDownloadTests(FreshCacheTestCase):
    def test_download_uses_a_keyed_report_number(self):
        user = make_user("alice")
        rec = make_record(user)
        number = views._report_number(rec)
        self.assertRegex(number, r"^CN-\d{6}-[0-9A-F]{8}$")
        self.assertNotIn(f"{rec.pk:06X}", number)
        self.client.login(username="alice", password=PASSWORD)
        response = self.client.get(reverse("download_report", args=[rec.pk]))
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertEqual(page_count(response.content), 2)
