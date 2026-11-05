"""CardioNova Health: clinical-style PDF report.

Layout (A4, two pages):
  page 1  letterhead, report title, patient/report information, risk result with a risk meter,
          result-reliability box, summary of findings
  page 2  clinical parameters with general guide ranges and status, factors influencing the estimate,
          suggested next steps, clinician-review block (optional), method notes and disclaimer
Every page has a confidentiality footer with the report number and "Page x of y".

The report is honest about what it is: a machine-learning estimate from an educational project, not a
hospital-issued diagnostic report. Nothing here invents a hospital, a licence or a signature.

build_report(record, rows, username=None, advice="", reliability=None, narrative=None, report_no=None)
returns the PDF as bytes. `username` is accepted for compatibility and is never printed.
All text that comes from users or the database is escaped before it reaches ReportLab.
"""
import hashlib
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.graphics.barcode.code128 import Code128
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, KeepTogether, PageTemplate, Paragraph, Spacer,
                                Table, TableStyle)

# ------------------------------------------------------------------------------------------------ palette
NAVY = colors.HexColor("#12395F")
NAVY_DARK = colors.HexColor("#0B2A47")
TEAL = colors.HexColor("#0E8C8F")
TEAL_LIGHT = colors.HexColor("#E6F5F5")
PAPER = colors.HexColor("#F4F7FA")
GRID = colors.HexColor("#CBD6E2")
TEXT = colors.HexColor("#1B2A3A")
MUTED = colors.HexColor("#5C6B7C")
WHITE = colors.white
GREEN = colors.HexColor("#2E9E62")
AMBER = colors.HexColor("#D9992B")
RED = colors.HexColor("#D64550")
GREEN_BG, AMBER_BG, RED_BG = colors.HexColor("#E5F5EC"), colors.HexColor("#FBF1DC"), colors.HexColor("#FBE6E8")

LEVEL_COLOR = {"LOW": GREEN, "MODERATE": AMBER, "HIGH": RED}
LEVEL_WORD = {"LOW": "LOW", "MODERATE": "MODERATE", "HIGH": "HIGH"}
TRUST_COLOR = {"good": GREEN, "fair": AMBER, "low": RED}

PAGE_W, PAGE_H = A4
MARGIN = 1.5 * cm
CONTENT_W = PAGE_W - 2 * MARGIN
FIRST_TOP = 3.55 * cm            # room for the letterhead on page 1
LATER_TOP = 1.75 * cm
BOTTOM = 1.7 * cm

# ------------------------------------------------------------------------------------------------ small helpers


def _s(value):
    """Text for ReportLab markup: escaped, never None."""
    return escape(str(value if value is not None else ""))


def _num(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _fmt(value):
    number = _num(value)
    if number is None:
        return _s(value)
    return f"{number:g}"


def _styles():
    base = getSampleStyleSheet()

    def make(name, parent="BodyText", **kw):
        return ParagraphStyle(name, parent=base[parent], **kw)

    s = {}
    s["body"] = make("CNBody", fontSize=8.8, leading=11.6, textColor=TEXT, spaceAfter=2)
    s["small"] = make("CNSmall", fontSize=7.4, leading=9.4, textColor=MUTED, spaceAfter=1)
    s["cell"] = make("CNCell", fontSize=8.2, leading=10, textColor=TEXT, spaceAfter=0)
    s["cell_b"] = make("CNCellB", parent="BodyText", fontName="Helvetica-Bold", fontSize=8.2, leading=10, textColor=NAVY)
    s["cell_s"] = make("CNCellS", fontSize=7.4, leading=9, textColor=MUTED, spaceAfter=0)
    s["head"] = make("CNHead", fontName="Helvetica-Bold", fontSize=7.8, leading=9.6, textColor=WHITE)
    s["section"] = make("CNSection", parent="Heading2", fontName="Helvetica-Bold", fontSize=10.6, leading=13, textColor=NAVY,
                        spaceBefore=7, spaceAfter=3)
    s["status"] = make("CNStatus", fontName="Helvetica-Bold", fontSize=7.6, leading=9, alignment=TA_CENTER)
    s["center"] = make("CNCenter", fontSize=8.2, leading=10, alignment=TA_CENTER, textColor=TEXT)
    s["risk_word"] = make("CNRiskWord", parent="Normal", fontName="Helvetica-Bold", fontSize=26, leading=29, alignment=TA_CENTER, textColor=WHITE)
    s["risk_label"] = make("CNRiskLabel", parent="Normal", fontName="Helvetica-Bold", fontSize=7.8, leading=10, alignment=TA_CENTER, textColor=WHITE)
    s["risk_prob"] = make("CNRiskProb", parent="Normal", fontName="Helvetica-Bold", fontSize=17, leading=20, alignment=TA_CENTER, textColor=WHITE)
    s["bullet"] = make("CNBullet", fontSize=8.6, leading=11.2, textColor=TEXT, leftIndent=10, bulletIndent=1, spaceAfter=1.5)
    s["label"] = make("CNLabel", fontName="Helvetica-Bold", fontSize=7.6, leading=9.4, textColor=MUTED)
    s["value"] = make("CNValue", fontSize=9.2, leading=11.4, textColor=TEXT)
    return s


# ------------------------------------------------------------------------------------------------ general guide ranges
# General, widely quoted adult guide values, shown for context only. They are NOT personal targets and NOT a diagnosis.
FEATURE_ORDER = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg", "thalach", "exang", "oldpeak", "slope", "ca", "thal"]
UNITS = {"age": "years", "trestbps": "mm Hg", "chol": "mg/dl", "thalach": "bpm", "oldpeak": "mm"}
GROUPS = [
    ("Patient", ["age", "sex"]),
    ("Symptoms", ["cp", "exang"]),
    ("Resting measurements", ["trestbps", "chol", "fbs", "restecg"]),
    ("Exercise stress test", ["thalach", "oldpeak", "slope"]),
    ("Imaging / laboratory", ["ca", "thal"]),
]
TITLES = {
    "age": "Age", "sex": "Sex", "cp": "Chest pain type", "trestbps": "Resting blood pressure (systolic)",
    "chol": "Serum cholesterol", "fbs": "Fasting blood sugar > 120 mg/dl", "restecg": "Resting ECG",
    "thalach": "Maximum heart rate achieved", "exang": "Exercise-induced angina", "oldpeak": "ST depression (exercise)",
    "slope": "Slope of peak exercise ST segment", "ca": "Major vessels (fluoroscopy)", "thal": "Thalassemia (thal) test",
}


def _guide_and_status(name, value, age):
    """(guide text, status text, colour) for one input. Colour None means no status is given."""
    v = _num(value)
    if name == "age":
        return "Risk generally rises with age", "", None
    if name == "sex":
        return "Reported as entered", "", None
    if name == "cp":
        return "Interpreted by a clinician", "", None
    if name == "trestbps":
        guide = "Under 120; 120-129 borderline; 130+ high"
        if v is None:
            return guide, "", None
        if v < 90:
            return guide, "Below guide", AMBER
        if v < 120:
            return guide, "Within guide", GREEN
        if v < 130:
            return guide, "Borderline", AMBER
        return guide, "Above guide", RED
    if name == "chol":
        guide = "Under 200; 200-239 borderline; 240+ high"
        if v is None:
            return guide, "", None
        if v < 125:
            return guide, "Check value", AMBER
        if v < 200:
            return guide, "Within guide", GREEN
        if v < 240:
            return guide, "Borderline", AMBER
        return guide, "Above guide", RED
    if name == "fbs":
        guide = "Fasting glucose under 100 mg/dl is usual"
        return guide, ("Above 120" if v == 1 else "Within guide") if v is not None else "", (RED if v == 1 else GREEN) if v is not None else None
    if name == "restecg":
        guide = "Normal expected"
        return guide, ("Within guide" if v == 0 else "Review by clinician") if v is not None else "", (GREEN if v == 0 else AMBER) if v is not None else None
    if name == "thalach":
        predicted = 220 - age if age else None
        guide = f"Age-predicted maximum about {predicted:g} bpm" if predicted else "Age-predicted maximum: 220 minus age"
        if v is None or not predicted:
            return guide, "", None
        share = v / predicted
        if share < 0.5:
            return guide, "Check value", AMBER
        if share < 0.85:
            return guide, "Below age guide", AMBER
        return guide, "Within guide", GREEN
    if name == "exang":
        return "No chest pain on exercise expected", ("Present" if v == 1 else "Absent") if v is not None else "", (RED if v == 1 else GREEN) if v is not None else None
    if name == "oldpeak":
        guide = "Under 1.0 mm is usual"
        if v is None:
            return guide, "", None
        if v < 1.0:
            return guide, "Within guide", GREEN
        if v < 2.0:
            return guide, "Borderline", AMBER
        return guide, "Above guide", RED
    if name == "slope":
        guide = "Upsloping is usual"
        return guide, {1: "Upsloping", 2: "Flat", 3: "Downsloping"}.get(int(v) if v is not None else -1, ""), \
            {1: GREEN, 2: AMBER, 3: RED}.get(int(v) if v is not None else -1)
    if name == "ca":
        guide = "None (0) is usual"
        return guide, ("None" if v == 0 else "Present") if v is not None else "", (GREEN if v == 0 else RED) if v is not None else None
    if name == "thal":
        guide = "Normal is usual"
        if v is None:
            return guide, "", None
        return guide, ("Normal" if v == 3 else "Defect reported"), (GREEN if v == 3 else RED)
    return "", "", None


def _tint(color):
    return {GREEN: GREEN_BG, AMBER: AMBER_BG, RED: RED_BG}.get(color, PAPER)


# ------------------------------------------------------------------------------------------------ drawn flowables
class RiskMeter(Flowable):
    """Horizontal bar with the project's three bands (0-30, 30-60, 60-100 %) and a marker at the estimate."""

    def __init__(self, probability, width=10.4 * cm, height=1.55 * cm):
        super().__init__()
        self.probability, self.width, self.height = max(0.0, min(100.0, probability)), width, height

    def wrap(self, avail_w, avail_h):
        return self.width, self.height

    def draw(self):
        c, w = self.canv, self.width
        bar_y, bar_h = 0.42 * cm, 0.46 * cm
        bands = [(0, 30, GREEN, "LOW"), (30, 60, AMBER, "MODERATE"), (60, 100, RED, "HIGH")]
        for low, high, color, word in bands:
            x0, x1 = w * low / 100.0, w * high / 100.0
            c.setFillColor(color)
            c.rect(x0, bar_y, x1 - x0 - 0.6, bar_h, stroke=0, fill=1)
            c.setFillColor(WHITE if color != AMBER else NAVY_DARK)
            c.setFont("Helvetica-Bold", 6.6)
            c.drawCentredString((x0 + x1) / 2 - 0.3, bar_y + 0.16 * cm, word)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 6.8)
        for tick in (0, 30, 60, 100):
            c.drawCentredString(w * tick / 100.0, 0.1 * cm, f"{tick}%")
        x = w * self.probability / 100.0
        c.setStrokeColor(NAVY_DARK)
        c.setLineWidth(1.4)
        c.line(x, bar_y + bar_h, x, bar_y + bar_h + 0.1 * cm)         # short tick above the bar ...
        c.line(x, bar_y - 0.07 * cm, x, bar_y)                          # ... and below it, so the labels stay readable
        c.setFillColor(NAVY_DARK)
        p = c.beginPath()
        p.moveTo(x - 0.17 * cm, bar_y + bar_h + 0.32 * cm)
        p.lineTo(x + 0.17 * cm, bar_y + bar_h + 0.32 * cm)
        p.lineTo(x, bar_y + bar_h + 0.1 * cm)
        p.close()
        c.drawPath(p, stroke=0, fill=1)
        label = f"{self.probability:.1f}%"
        c.setFont("Helvetica-Bold", 8.2)
        text_w = c.stringWidth(label, "Helvetica-Bold", 8.2)
        left = min(max(x - text_w / 2, 0), w - text_w)
        c.drawString(left, bar_y + bar_h + 0.36 * cm, label)


class FactorChart(Flowable):
    """Diverging bars: how much each input moved the estimate (percentage points) against a typical patient."""

    ROW = 0.52 * cm

    def __init__(self, items, width=CONTENT_W):
        super().__init__()
        self.items, self.width = items, width

    def wrap(self, avail_w, avail_h):
        self.height = self.ROW * (len(self.items) + 1) + 0.15 * cm
        return self.width, self.height

    def draw(self):
        c, w = self.canv, self.width
        label_w, value_w = 7.4 * cm, 2.0 * cm
        bars_w = w - label_w - value_w
        centre = label_w + bars_w / 2
        biggest = max([abs(d) for _, d in self.items] + [5.0])
        y = self.height - self.ROW
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(TEAL)
        c.drawRightString(centre - 0.2 * cm, y + 0.18 * cm, "lowers the estimate")
        c.setFillColor(RED)
        c.drawString(centre + 0.2 * cm, y + 0.18 * cm, "raises the estimate")
        top = y
        for label, delta in self.items:
            y -= self.ROW
            c.setFillColor(TEXT)
            c.setFont("Helvetica", 8)
            c.drawString(0, y + 0.2 * cm, label)
            length = (bars_w / 2 - 0.2 * cm) * min(abs(delta) / biggest, 1.0)
            c.setFillColor(RED if delta > 0 else TEAL)
            if delta > 0:
                c.rect(centre, y + 0.12 * cm, length, 0.32 * cm, stroke=0, fill=1)
            else:
                c.rect(centre - length, y + 0.12 * cm, length, 0.32 * cm, stroke=0, fill=1)
            c.setFillColor(TEXT)
            c.setFont("Helvetica-Bold", 8)
            c.drawRightString(w, y + 0.2 * cm, f"{delta:+.1f} pts")
        c.setStrokeColor(MUTED)
        c.setLineWidth(0.7)
        c.line(centre, top + 0.05 * cm, centre, y + 0.05 * cm)


def _heart(c, cx, cy, size, color):
    """A small vector heart (no font glyph needed)."""
    s = size / 2.0
    p = c.beginPath()
    p.moveTo(cx, cy - s * 0.95)
    p.curveTo(cx - s * 1.9, cy - s * 0.1, cx - s * 1.1, cy + s * 1.25, cx, cy + s * 0.45)
    p.curveTo(cx + s * 1.1, cy + s * 1.25, cx + s * 1.9, cy - s * 0.1, cx, cy - s * 0.95)
    p.close()
    c.setFillColor(color)
    c.drawPath(p, stroke=0, fill=1)


# ------------------------------------------------------------------------------------------------ page furniture
class NumberedCanvas(pdfcanvas.Canvas):
    """Draws the footer with 'Page x of y' once the total number of pages is known."""

    report_no = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._states = []

    def showPage(self):
        self._states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._states)
        for state in self._states:
            self.__dict__.update(state)
            self._footer(total)
            super().showPage()
        super().save()

    def _footer(self, total):
        y = 0.95 * cm
        self.setStrokeColor(GRID)
        self.setLineWidth(0.6)
        self.line(MARGIN, y + 0.42 * cm, PAGE_W - MARGIN, y + 0.42 * cm)
        self.setFillColor(MUTED)
        self.setFont("Helvetica", 6.8)
        self.drawString(MARGIN, y + 0.1 * cm, "CONFIDENTIAL: contains personal health information, intended for the named patient and their clinician.")
        self.drawString(MARGIN, y - 0.18 * cm, "CardioNova Health  |  Educational machine-learning project, not a medical device or a hospital-issued report.")
        self.setFont("Helvetica-Bold", 7.4)
        self.drawRightString(PAGE_W - MARGIN, y + 0.1 * cm, f"Page {self._pageNumber} of {total}")
        self.setFont("Helvetica", 6.8)
        self.drawRightString(PAGE_W - MARGIN, y - 0.18 * cm, f"Report No. {self.report_no}")


def _letterhead(c, meta):
    """Page 1: logo, institution block, report title block with the report number as a barcode."""
    top = PAGE_H - 0.9 * cm
    _heart(c, MARGIN + 0.62 * cm, top - 0.82 * cm, 1.02 * cm, TEAL)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(MARGIN + 1.5 * cm, top - 0.78 * cm, "CardioNova")
    width = c.stringWidth("CardioNova ", "Helvetica-Bold", 20)
    c.setFillColor(TEAL)
    c.drawString(MARGIN + 1.5 * cm + width, top - 0.78 * cm, "Health")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawString(MARGIN + 1.5 * cm, top - 1.2 * cm, "Smarter Insights. Healthier Hearts.")
    c.setFont("Helvetica", 7.2)
    c.drawString(MARGIN + 1.5 * cm, top - 1.58 * cm, "AI-assisted cardiovascular risk screening  |  Educational demonstration project")

    right = PAGE_W - MARGIN
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8.4)
    c.drawRightString(right, top - 0.5 * cm, "REPORT NUMBER")
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(right, top - 0.98 * cm, meta["report_no"])
    barcode = Code128(meta["report_no"], barHeight=0.62 * cm, humanReadable=False, quiet=False)
    target = 5.2 * cm
    c.saveState()
    c.translate(right - target, top - 1.78 * cm)
    c.scale(target / barcode.width, 1)
    barcode.drawOn(c, 0, 0)
    c.restoreState()

    y = PAGE_H - FIRST_TOP + 0.38 * cm
    c.setStrokeColor(TEAL)
    c.setLineWidth(1.6)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.5)
    c.line(MARGIN, y - 0.07 * cm, PAGE_W - MARGIN, y - 0.07 * cm)


def _running_header(c, meta):
    """Pages 2+: slim header so a loose page can still be matched to its patient."""
    y = PAGE_H - 1.05 * cm
    _heart(c, MARGIN + 0.22 * cm, y + 0.12 * cm, 0.4 * cm, TEAL)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN + 0.7 * cm, y, "CardioNova Health")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.6)
    c.drawRightString(PAGE_W - MARGIN, y, f"Patient: {meta['patient'][:48]}   |   Report No. {meta['report_no']}")
    c.setStrokeColor(TEAL)
    c.setLineWidth(1.1)
    c.line(MARGIN, y - 0.28 * cm, PAGE_W - MARGIN, y - 0.28 * cm)


# ------------------------------------------------------------------------------------------------ content blocks
def _info_table(meta, s):
    def cell(label, value):
        return [Paragraph(_s(label).upper(), s["label"]), Paragraph(_s(value), s["value"])]

    rows = [
        [cell("Patient name", meta["patient"]), cell("Assessment date", meta["date"])],
        [cell("Age / sex", meta["age_sex"]), cell("Report status", "Generated automatically; not reviewed by a clinician")],
        [cell("Assessment type", "Machine-learning risk screening from 13 clinical inputs"), cell("Model", meta["model"])],
    ]
    table = Table(rows, colWidths=[CONTENT_W * 0.5, CONTENT_W * 0.5])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PAPER), ("BOX", (0, 0), (-1, -1), 0.7, GRID), ("INNERGRID", (0, 0), (-1, -1), 0.4, GRID),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def _title_band(s):
    band = Table([[Paragraph("CARDIOVASCULAR RISK ASSESSMENT REPORT", ParagraphStyle(
        "CNBand", parent=s["head"], fontSize=11.5, leading=14, alignment=TA_CENTER))]], colWidths=[CONTENT_W])
    band.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY), ("TOPPADDING", (0, 0), (-1, -1), 6),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return band


def _result_block(level, probability, probability_text, trust, s):
    colour = LEVEL_COLOR.get(level, NAVY)
    word = LEVEL_WORD.get(level, "N/A")
    size = min(26.0, 26.0 * 124.0 / max(stringWidth(word, "Helvetica-Bold", 26), 1.0))       # fit the card width, never wrap
    word_style = ParagraphStyle("CNRiskWordFit", parent=s["risk_word"], fontSize=size, leading=size * 1.12)
    card = Table([[Paragraph("ESTIMATED RISK OF HEART DISEASE", s["risk_label"])],
                  [Paragraph(word, word_style)],
                  [Paragraph(probability_text, s["risk_prob"])]], colWidths=[5.2 * cm])
    card.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colour), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                              ("TOPPADDING", (0, 0), (0, 0), 8), ("BOTTOMPADDING", (0, 2), (0, 2), 8)]))
    right = [Paragraph("<b>Risk meter</b> (project-defined bands: below 30% low, 30% to below 60% moderate, 60% or more high)", s["small"]),
             Spacer(1, 3), RiskMeter(probability if probability is not None else 0.0)]
    if trust:
        tcolour = TRUST_COLOR.get(trust.get("level"), MUTED)
        rng = trust.get("range")
        spread = f"  Estimates from the model's internal versions range from {rng[0]}% to {rng[1]}%." if rng else ""
        right += [Spacer(1, 2), Paragraph(
            f"<b>Result reliability:</b> <font color='{tcolour.hexval().replace('0x', '#')}'><b>{_s(str(trust.get('label', '')).upper())}</b></font>.{_s(spread)}", s["body"])]
    block = Table([[card, right]], colWidths=[5.6 * cm, CONTENT_W - 5.6 * cm])
    block.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, 0), 6),
                               ("LEFTPADDING", (1, 0), (1, 0), 10), ("RIGHTPADDING", (1, 0), (1, 0), 0)]))
    return block


def _box(flowables, background, border, width=CONTENT_W, pad=8):
    table = Table([[flowables]], colWidths=[width])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), background), ("BOX", (0, 0), (-1, -1), 0.9, border),
                               ("LEFTPADDING", (0, 0), (-1, -1), pad), ("RIGHTPADDING", (0, 0), (-1, -1), pad),
                               ("TOPPADDING", (0, 0), (-1, -1), pad - 2), ("BOTTOMPADDING", (0, 0), (-1, -1), pad - 2)]))
    return table


def _parameters_table(record, rows, s):
    age = _num(getattr(record, "age", None))
    shown = {name: (rows[i][1] if i < len(rows) else "") for i, name in enumerate(FEATURE_ORDER)}
    widths = [4.9 * cm, 3.0 * cm, 1.2 * cm, 6.0 * cm, 2.9 * cm]
    data = [[Paragraph(h, s["head"]) for h in ("PARAMETER", "RESULT", "UNIT", "GENERAL GUIDE (adults)", "STATUS")]]
    styles = [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.4, GRID),
              ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 2.3),
              ("BOTTOMPADDING", (0, 0), (-1, -1), 2.3)]
    for title, names in GROUPS:
        data.append([Paragraph(f"<b>{_s(title.upper())}</b>", ParagraphStyle("CNGrp", parent=s["cell_s"], textColor=NAVY, fontName="Helvetica-Bold")), "", "", "", ""])
        r = len(data) - 1
        styles += [("SPAN", (0, r), (-1, r)), ("BACKGROUND", (0, r), (-1, r), TEAL_LIGHT)]
        for name in names:
            raw = getattr(record, name, None)
            guide, status, colour = _guide_and_status(name, raw, age)
            result = shown.get(name) or _fmt(raw)
            if name in UNITS:
                result = _fmt(raw)
            data.append([Paragraph(_s(TITLES[name]), s["cell"]), Paragraph(f"<b>{_s(result)}</b>", s["cell"]), Paragraph(_s(UNITS.get(name, "")), s["cell_s"]),
                         Paragraph(_s(guide), s["cell_s"]),
                         Paragraph(f"<font color='{(colour or MUTED).hexval().replace('0x', '#')}'>{_s(status) if status else '-'}</font>", s["status"])])
            r = len(data) - 1
            if colour:
                styles.append(("BACKGROUND", (4, r), (4, r), _tint(colour)))
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle(styles))
    return table


def _factor_items(record):
    items = []
    for entry in list(getattr(record, "explanation", None) or []):
        try:
            delta = float(entry.get("delta", 0))
        except (TypeError, ValueError, AttributeError):
            continue
        if abs(delta) < 0.05:
            continue
        items.append((f"{str(entry.get('label', ''))[:38]} ({str(entry.get('value', ''))[:22]})", delta))
    items.sort(key=lambda item: abs(item[1]), reverse=True)
    return items[:6]


def _signature_block(s):
    def line(label):
        return [Paragraph(label.upper(), s["label"]), ""]

    rows = [[Paragraph("CLINICIAN REVIEW (OPTIONAL)", s["head"]), "", "", ""],
            [Paragraph("Reviewed by (name)", s["label"]), "", Paragraph("Registration no.", s["label"]), ""],
            [Paragraph("Signature", s["label"]), "", Paragraph("Date", s["label"]), ""],
            [Paragraph("Comments", s["label"]), "", "", ""]]
    table = Table(rows, colWidths=[3.3 * cm, 5.9 * cm, 3.0 * cm, 5.8 * cm], rowHeights=[None, 0.8 * cm, 0.8 * cm, 1.15 * cm])
    table.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)), ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("SPAN", (1, 3), (3, 3)),
        ("BOX", (0, 0), (-1, -1), 0.7, GRID), ("INNERGRID", (0, 1), (-1, -1), 0.4, GRID), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 1), (0, -1), PAPER), ("BACKGROUND", (2, 1), (2, 2), PAPER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, 0), 4), ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
    ]))
    return table


# ------------------------------------------------------------------------------------------------ main entry point
def build_report(record, rows, username=None, advice="", reliability=None, narrative=None, report_no=None):
    """Return the report as PDF bytes."""
    s = _styles()
    level = str(getattr(record, "risk_level", "") or "").upper()
    probability = _num(getattr(record, "probability", None))
    probability_text = f"{probability:.1f}%" if probability is not None else "N/A"
    created = getattr(record, "created_at", None)
    try:
        date_text = created.strftime("%d %b %Y, %H:%M")
    except (AttributeError, ValueError):
        date_text = "Not available"
    patient = (getattr(record, "patient_label", "") or "").strip() or "Not provided"
    sex_text = "Male" if _num(getattr(record, "sex", None)) == 1 else "Female" if _num(getattr(record, "sex", None)) == 0 else "Not stated"
    age = _num(getattr(record, "age", None))
    model_name = getattr(record, "model_name", "") or "Not specified"
    info = {}
    try:
        from . import ml
        info = ml.model_info() or {}
    except Exception:                                   # the report must still be produced without the model files
        info = {}
    if not report_no:               # callers should pass a keyed number; this fallback is derived from the content, never from the database id
        digest = hashlib.sha256(f"{patient}|{date_text}|{probability_text}|{model_name}".encode()).hexdigest()[:8].upper()
        report_no = "CN-" + (created.strftime("%y%m%d") if hasattr(created, "strftime") else "000000") + "-" + digest
    meta = {"patient": patient, "report_no": report_no, "date": date_text, "model": f"{model_name} (calibrated)",
            "age_sex": f"{age:g} years / {sex_text}" if age is not None else sex_text}

    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=LATER_TOP, bottomMargin=BOTTOM,
                          title="CardioNova Health: Cardiovascular Risk Assessment Report", author="CardioNova Health",
                          subject="Machine-learning heart disease risk assessment (educational)")
    first = Frame(MARGIN, BOTTOM, CONTENT_W, PAGE_H - FIRST_TOP - BOTTOM, id="first", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    later = Frame(MARGIN, BOTTOM, CONTENT_W, PAGE_H - LATER_TOP - BOTTOM, id="later", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="first", frames=[first], onPage=lambda c, d: _letterhead(c, meta), autoNextPageTemplate="later"),
                          PageTemplate(id="later", frames=[later], onPage=lambda c, d: _running_header(c, meta))])

    story = [_title_band(s), Spacer(1, 6), _info_table(meta, s), Spacer(1, 8), _result_block(level, probability, probability_text, reliability, s)]

    if reliability and reliability.get("level") == "low":
        reasons = [Paragraph(f"<b>Low reliability.</b> The category above may not be trustworthy. Please check the entered values before relying on it.", s["body"])]
        for reason in (reliability.get("reasons") or [])[:3]:
            reasons.append(Paragraph(_s(reason), s["bullet"], bulletText="-"))
        story += [Spacer(1, 8), _box(reasons, RED_BG, RED)]

    summary = [Paragraph("<b>Summary of findings</b>", ParagraphStyle("CNSumH", parent=s["body"], textColor=NAVY, fontSize=10, leading=12.5, spaceAfter=3))]
    if narrative:
        summary.append(Paragraph(_s(narrative.get("summary", "")), s["body"]))
        factor_points = [pt for pt in (narrative.get("points") or []) if not pt.startswith(("Trust check", "Across the cross-validation"))]
        for point in factor_points[:4]:
            summary.append(Paragraph(_s(point), s["bullet"], bulletText="-"))
    elif advice:
        summary.append(Paragraph(_s(advice), s["body"]))
    story += [Spacer(1, 8), _box(summary, TEAL_LIGHT, TEAL)]
    if advice and narrative:
        story += [Spacer(1, 6), Paragraph(f"<b>Guidance:</b> {_s(advice)}", s["body"])]
    story += [Spacer(1, 4),
              Paragraph("This report presents the output of a statistical model. It does not confirm or exclude heart disease and must not be used "
                        "to make treatment decisions.", s["small"])]

    items = _factor_items(record)
    if items:
        story += [KeepTogether([Paragraph("Factors influencing the estimate", s["section"]), FactorChart(items),
                                Paragraph("Each bar shows how many percentage points the estimate changes when that input is replaced by the typical value in "
                                          "the training data. These are model associations, not medical causes, and need not add up to the total.", s["small"])])]
    story += [CondPageBreak(9 * cm), Paragraph("Clinical parameters entered", s["section"]), _parameters_table(record, rows, s),
              Paragraph("Guide values are general adult reference points shown for context. They are not personal targets and not a diagnosis; "
                        "categorical inputs have no numeric range.", s["small"])]

    steps = [Paragraph("Suggested next steps", s["section"]),
             Paragraph("Share this report with a qualified healthcare professional and discuss it together with your symptoms, examination and tests.", s["bullet"], bulletText="-"),
             Paragraph("<b>If you have chest pain, severe breathlessness, fainting or any emergency symptom, seek emergency care immediately.</b> "
                       "Do not wait for a report.", s["bullet"], bulletText="-")]
    if narrative:
        for question in (narrative.get("questions") or [])[:4]:
            steps.append(Paragraph(f"Ask: {_s(question)}", s["bullet"], bulletText="-"))
    story += [KeepTogether(steps), Spacer(1, 6), KeepTogether([_signature_block(s)])]

    metrics = info.get("metrics") or {}
    ci = (info.get("metrics_ci") or {}).get("roc_auc")
    method = (f"<b>About the method.</b> Model: {_s(model_name)}, trained on {_s(info.get('rows', 'n/a'))} patient records from the UCI Cleveland dataset. "
              f"Held-out test ROC-AUC {_s(metrics.get('roc_auc', 'n/a'))}"
              + (f" (95% interval {ci[0]} to {ci[1]})" if ci else "") +
              ". The small, single-site, mostly older training population limits how well the model fits other people.")
    disclaimer = [Paragraph("<b>LIMITATIONS AND MEDICAL DISCLAIMER</b>", ParagraphStyle("CNDisH", parent=s["small"], textColor=NAVY, fontName="Helvetica-Bold")),
                  Paragraph(method, s["small"]),
                  Paragraph("CardioNova Health is an academic machine-learning project. This report is for educational and demonstration purposes only; it is not a "
                            "hospital-issued diagnostic report, does not confirm or exclude heart disease, and must not be used to make treatment decisions. "
                            "The model and its probabilities have not been clinically validated for individual patient care. Consult a qualified healthcare "
                            "professional for medical assessment and interpretation of clinical tests.", s["small"]),
                  Paragraph("Project-defined risk bands: below 30% = Low; 30% to below 60% = Moderate; 60% or above = High. These thresholds are not official "
                            "clinical risk classifications.", s["small"])]
    story += [Spacer(1, 6), KeepTogether([_box(disclaimer, PAPER, GRID, pad=7)])]

    class _Canvas(NumberedCanvas):
        pass
    _Canvas.report_no = report_no
    doc.build(story, canvasmaker=_Canvas)
    return buffer.getvalue()
