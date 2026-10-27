"""CardioNova Health PDF report generator.

Drop-in replacement for the existing ReportLab report module.
Keeps the build_report(record, rows, username=None, advice="", reliability=None)
function signature so existing callers can continue to work.

Design: navy/teal clinical-style header, patient metadata card, risk banner,
reliability/insights card, two-column factors and entered-parameters section,
and medical disclaimer footer.
"""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether,
)

# ---------- Palette ----------
NAVY = colors.HexColor("#10446D")
NAVY_DARK = colors.HexColor("#083B61")
TEAL = colors.HexColor("#07999B")
TEAL_LIGHT = colors.HexColor("#E4F7F6")
BLUE_LIGHT = colors.HexColor("#EDF5FD")
BLUE_HEADER = colors.HexColor("#DFF0FB")
GRID = colors.HexColor("#C7E0F1")
TEXT = colors.HexColor("#17324D")
MUTED = colors.HexColor("#587087")
WHITE = colors.white
GREEN = colors.HexColor("#35A96B")
AMBER = colors.HexColor("#E7A62D")
RED = colors.HexColor("#E84C5B")

LEVEL_COLORS = {
    "LOW": GREEN,
    "MODERATE": AMBER,
    "HIGH": RED,
}
LEVEL_TEXT_COLORS = {
    "LOW": colors.HexColor("#FFFFFF"),
    "MODERATE": NAVY_DARK,
    "HIGH": colors.HexColor("#FFFFFF"),
}

# Contextual notes, not clinical thresholds or personalized advice.
REFERENCE_INFO = {
    "age": "Risk generally rises with age; interpret in clinical context",
    "sex": "Categorical model input",
    "chest pain": "Categorical model input",
    "resting blood pressure": (
        "General guide: below 120/80 mm Hg is considered normal. A single systolic "
        "value is incomplete; a BP reading normally has systolic and diastolic values"
    ),
    "cholesterol": "General guide: total cholesterol below 200 mg/dl is desirable; interpret with the full lipid profile",
    "fasting blood sugar": "General guide: fasting glucose below 100 mg/dl is normal; this model input flags values above 120",
    "blood sugar": "General guide: fasting glucose below 100 mg/dl is normal; this model input flags values above 120",
    "resting ecg": "Requires interpretation by a qualified clinician",
    "maximum heart rate": "Rough age guide: 220 minus age; interpret with exercise-test context",
    "exercise-induced angina": "Categorical model input",
    "exercise induced angina": "Categorical model input",
    "st depression": "Requires exercise-test interpretation",
    "slope": "Categorical model input",
    "major vessels": "Imaging/test-specific model input",
    "thal": "Test-specific categorical model input",
}


def _s(value):
    """Safely convert values for ReportLab paragraph markup."""
    return escape(str(value if value is not None else ""))


def _style(name, parent, **kwargs):
    return ParagraphStyle(name, parent=parent, **kwargs)


def _p(text, style):
    return Paragraph(text, style)


def _reference_for(label):
    key = str(label).strip().lower()
    for fragment, note in REFERENCE_INFO.items():
        if fragment in key:
            return note
    return "No project reference supplied; interpret in clinical context"


def _footer(canvas, doc):
    canvas.saveState()
    page_w, _ = A4
    left, right = doc.leftMargin, page_w - doc.rightMargin
    y = 0.72 * cm
    canvas.setStrokeColor(GRID)
    canvas.setLineWidth(0.65)
    canvas.line(left, y + 0.28 * cm, right, y + 0.28 * cm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(left, y - 0.02 * cm, "CardioNova Health  |  Smarter Insights. Healthier Hearts.")
    canvas.drawRightString(right, y - 0.02 * cm, f"Page {doc.page}")
    canvas.restoreState()


def _make_table(data, widths, header=True, font_size=7.2, padd=4.5):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    cmds = [
        ("GRID", (0, 0), (-1, -1), 0.45, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), padd),
        ("RIGHTPADDING", (0, 0), (-1, -1), padd),
        ("TOPPADDING", (0, 0), (-1, -1), padd),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padd),
    ]
    if header:
        cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), BLUE_HEADER),
            ("TEXTCOLOR", (0, 0), (-1, 0), NAVY),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F5FAFE")]),
        ]
    else:
        cmds += [
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, colors.HexColor("#F5FAFE")]),
        ]
    t.setStyle(TableStyle(cmds))
    return t


def build_report(record, rows, username=None, advice="", reliability=None, narrative=None):
    """Return a professionally styled PDF report as bytes.

    `username` is accepted for backwards compatibility but intentionally not
    displayed. The database primary key/report number is also not displayed.
    """
    buffer = BytesIO()
    page_w, page_h = A4
    left = 1.25 * cm
    right = 1.25 * cm
    top = 1.0 * cm
    bottom = 1.25 * cm

    # A BaseDocTemplate + frame allows a clean, predictable printable page.
    doc = BaseDocTemplate(
        buffer, pagesize=A4,
        leftMargin=left, rightMargin=right,
        topMargin=top, bottomMargin=bottom,
        title="CardioNova Health - Heart Health Assessment Report",
        author="CardioNova Health",
    )
    frame = Frame(left, bottom, page_w-left-right, page_h-top-bottom,
                  id="main", leftPadding=0, rightPadding=0, topPadding=0,
                  bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="report", frames=[frame], onPage=_footer)])

    base = getSampleStyleSheet()
    brand = _style("CNBrand", base["Title"], fontName="Helvetica-Bold",
                   fontSize=21, leading=23, textColor=NAVY, alignment=TA_LEFT,
                   spaceAfter=0)
    tagline = _style("CNTagline", base["Normal"], fontSize=8.5, leading=10,
                     textColor=TEAL, spaceAfter=0)
    report_kind = _style("CNKind", base["Normal"], fontName="Helvetica-Bold",
                         fontSize=9, leading=12, textColor=NAVY, alignment=TA_RIGHT)
    heading = _style("CNHeading", base["Heading1"], fontName="Helvetica-Bold",
                     fontSize=15, leading=18, textColor=NAVY, spaceBefore=5, spaceAfter=4)
    section = _style("CNSection", base["Heading2"], fontName="Helvetica-Bold",
                     fontSize=9.2, leading=11, textColor=NAVY, spaceBefore=5, spaceAfter=4)
    body = _style("CNBody", base["BodyText"], fontSize=7.8, leading=10,
                  textColor=TEXT, spaceAfter=2)
    small = _style("CNSmall", base["BodyText"], fontSize=6.6, leading=8.2,
                   textColor=MUTED, spaceAfter=1)
    cell = _style("CNCell", base["BodyText"], fontSize=6.7, leading=8,
                  textColor=TEXT, spaceAfter=0)
    cell_bold = _style("CNCellBold", cell, fontName="Helvetica-Bold", textColor=NAVY)
    table_head = _style("CNTableHead", cell, fontName="Helvetica-Bold", textColor=NAVY)
    center = _style("CNCenter", cell, alignment=TA_CENTER)
    white_center = _style("CNWhiteCenter", cell, fontName="Helvetica-Bold",
                          textColor=WHITE, alignment=TA_CENTER)
    risk_value_style = _style("CNRiskValue", base["Normal"], fontName="Helvetica-Bold",
                              fontSize=22, leading=24, textColor=WHITE, alignment=TA_CENTER)
    prob_value_style = _style("CNProbValue", base["Normal"], fontName="Helvetica-Bold",
                              fontSize=20, leading=23, textColor=NAVY, alignment=TA_CENTER)

    risk_level = str(getattr(record, "risk_level", "UNKNOWN") or "UNKNOWN").upper()
    risk_color = LEVEL_COLORS.get(risk_level, NAVY)
    probability = getattr(record, "probability", None)
    try:
        probability_text = f"{float(probability):.1f}%"
    except (TypeError, ValueError):
        probability_text = "N/A"
    patient = getattr(record, "patient_label", "") or "Not provided"
    created = getattr(record, "created_at", None)
    try:
        date_text = created.strftime("%d %b %Y, %H:%M") if created else "Not available"
    except (AttributeError, ValueError):
        date_text = str(created)
    model_name = getattr(record, "model_name", "") or "Not specified"

    story = []

    # Top brand row, approximating the supplied reference design.
    logo_mark = _p(
        "<font color='#07999B' size='23'><b>♥</b></font>",
        _style("CNLogoMark", base["Normal"], alignment=TA_CENTER, leading=24)
    )
    brand_block = [
        _p("CardioNova <font color='#07999B'>Health</font>", brand),
        _p("Smarter Insights. Healthier Hearts.", tagline),
    ]
    header = Table(
        [[logo_mark, brand_block,
          _p("ML ASSESSMENT REPORT<br/><font size='8'>HEART DISEASE RISK</font>", report_kind)]],
        colWidths=[1.0*cm, 9.0*cm, 7.0*cm],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.1, TEAL),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    story += [header, Spacer(1, 5),
              _p("Heart Health Assessment Report", heading),
              _p("This report summarizes the values entered into the project's machine-learning model and the model's estimated output.", body),
              Spacer(1, 4)]

    # Patient metadata card.
    metadata = [
        [_p("<b>Patient name</b>", cell_bold), _p(_s(patient), cell),
         _p("<b>Assessment date</b>", cell_bold), _p(_s(date_text), cell)],
        [_p("<b>Model used</b>", cell_bold), _p(_s(model_name), cell),
         _p("<b>Report type</b>", cell_bold), _p("Machine-learning assessment", cell)],
    ]
    meta = Table(metadata, colWidths=[2.3*cm, 5.5*cm, 2.5*cm, 6.7*cm])
    meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.6, GRID),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [meta, Spacer(1, 7)]

    # Risk banner with category on the left and probability on the right.
    risk_left = Table([
        [_p("MODEL RISK CATEGORY", white_center)],
        [_p(_s(risk_level), risk_value_style)],
    ], colWidths=[7.7*cm])
    risk_left.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 3),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
    ]))
    probability_block = Table([
        [_p("ESTIMATED PROBABILITY", _style("CNProbHead", cell_bold, alignment=TA_CENTER, fontSize=8))],
        [_p(_s(probability_text), prob_value_style)],
        [_p("Model output — not a diagnosis", small)],
    ], colWidths=[8.7*cm])
    probability_block.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TEAL_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    risk_banner = Table([[risk_left, probability_block]], colWidths=[7.7*cm, 8.7*cm])
    risk_banner.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story += [risk_banner, Spacer(1, 5)]

    notice = Table([[
        _p("<b>ⓘ &nbsp; Important:</b> The displayed percentage is the model's estimated probability, "
           "not a confirmed diagnosis or a clinically validated personal risk measurement.", body)
    ]], colWidths=[16.4*cm])
    notice.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TEAL_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#A6E5E2")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [notice, Spacer(1, 5)]

    # Insights and reliability side-by-side.
    insights_text = _s(advice) if advice else (
        "The model generated an estimate from the entered values. "
        "Discuss health concerns and clinical test results with a qualified healthcare professional."
    )
    if narrative and narrative.get("points"):
        insights_text += "<br/><br/><b>In plain language:</b> " + " ".join(_s(p) for p in narrative["points"][:2])
    reliability_label = "Not assessed"
    reasons_text = ""
    if reliability:
        reliability_label = str(reliability.get("label", "Not specified"))
        reasons_text = " ".join(str(x) for x in reliability.get("reasons", []) if x)

    insights = Table([
        [_p("<b>Key Insights</b>", section)],
        [_p(insights_text, body)],
    ], colWidths=[9.4*cm])
    insights.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, GRID),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    reliability_content = (
        f"<b>Model Reliability</b><br/><br/><font color='#27864B'><b>{_s(reliability_label)}</b></font>"
        + (f"<br/><br/>{_s(reasons_text)}" if reasons_text else "")
    )
    rel = Table([[_p(reliability_content, body)]], colWidths=[7.0*cm])
    rel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, GRID),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    insight_row = Table([[insights, rel]], colWidths=[9.4*cm, 7.0*cm])
    insight_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story += [insight_row, Spacer(1, 4)]

    # Factors table and entered-parameter table in two columns.
    factors = list(getattr(record, "explanation", None) or [])[:6]
    factor_rows = [[_p("Model input", table_head),
                    _p("Entered value", table_head),
                    _p("Model effect", table_head)]]
    for f in factors:
        try:
            delta = f"{float(f.get('delta', 0)):+.1f} points"
        except (TypeError, ValueError):
            delta = "N/A"
        factor_rows.append([
            _p(_s(f.get("label", "")), cell),
            _p(_s(f.get("value", "")), cell),
            _p(_s(delta), cell),
        ])
    if len(factor_rows) == 1:
        factor_rows.append([_p("No explanation factors available", cell), "", ""])

    factor_table = _make_table(factor_rows, [3.5*cm, 2.4*cm, 2.6*cm], font_size=6.5, padd=4)
    factor_note = _p(
        "Each effect is the change in the estimate (percentage points) when that input is replaced by the "
        "training-data median. Effects need not add up to the total. They do not establish medical causation "
        "or independent clinical risk.",
        small
    )
    left_column = [
        _p("Factors Influencing the Estimate", section),
        factor_table,
        Spacer(1, 3),
        factor_note,
        Spacer(1, 4),
        _p("Reference Information", section),
        _p(
            "Contextual notes only; not personalized normal ranges. This project does not calculate "
            "a medically validated increase/decrease for every parameter. Categorical inputs do not "
            "have meaningful arithmetic differences.",
            small
        ),
    ]

    param_rows = [[_p("Parameter", table_head),
                   _p("Your value", table_head),
                   _p("Reference information", table_head)]]
    for label, value in rows:
        param_rows.append([
            _p(_s(label), cell),
            _p(_s(value), cell),
            _p(_s(_reference_for(label)), cell),
        ])
    param_table = _make_table(
        param_rows, [2.7*cm, 2.2*cm, 3.5*cm], font_size=6.2, padd=3.5
    )
    right_column = [
        _p("Entered Health Parameters", section),
        param_table,
    ]

    columns = Table(
        [[left_column, right_column]],
        colWidths=[8.8*cm, 8.6*cm],
    )
    columns.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBEFORE", (1, 0), (1, 0), 0.7, GRID),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 5),
        ("LEFTPADDING", (1, 0), (1, 0), 5),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story += [columns, Spacer(1, 5)]

    # Disclaimer card.
    disclaimer = Table([[
        _p("<b>LIMITATIONS AND MEDICAL DISCLAIMER</b><br/><br/>"
           "CardioNova Health is an academic machine-learning project. This report is for educational "
           "and demonstration purposes only; it is not a hospital-issued diagnostic report, does not "
           "confirm or exclude heart disease, and must not be used to make treatment decisions. The model "
           "and its probabilities have not been established as clinically validated for individual patient "
           "care. Consult a qualified healthcare professional for medical assessment and interpretation "
           "of clinical tests.<br/><br/>"
           "Project-defined categories: below 30% = Low; 30% to below 60% = Moderate; 60% or above = High. "
           "These thresholds are not official clinical risk classifications.",
           small)
    ]], colWidths=[16.4*cm])
    disclaimer.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.6, GRID),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [disclaimer]

    doc.build(story)
    return buffer.getvalue()