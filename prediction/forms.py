from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from . import ml
from .models import Profile
from .sanitize import clean_text

AGE, BP, CHOL, HR, ST = (ml.NUMERIC_RANGES[k] for k in ("age", "trestbps", "chol", "thalach", "oldpeak"))


class StyledFormMixin:
    """Adds the CSS class used by the site to every form widget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()


class RegisterForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(required=True, help_text="Used only for your account.")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class LoginForm(StyledFormMixin, AuthenticationForm):
    pass


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["share_with_doctors"]
        labels = {"share_with_doctors": "Let registered doctors see my prediction history"}


class BatchUploadForm(StyledFormMixin, forms.Form):
    file = forms.FileField(label="CSV file", help_text="Maximum 500 rows and 1 MB.")

    ALLOWED_TYPES = {"text/csv", "application/csv", "application/vnd.ms-excel", "text/plain",
                     "application/octet-stream", ""}        # browsers label CSV files in different ways

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith(".csv"):
            raise forms.ValidationError("Please upload a .csv file.")
        if f.size > 1024 * 1024:
            raise forms.ValidationError("The file is larger than 1 MB.")
        if (getattr(f, "content_type", "") or "").lower() not in self.ALLOWED_TYPES:
            raise forms.ValidationError("This file type is not allowed. Upload a plain CSV file.")
        head = f.read(4096)
        f.seek(0)
        if b"\x00" in head:
            raise forms.ValidationError("The file does not look like a text CSV file.")
        return f                # the content is checked again (encoding, rows, columns) in batch.parse()


class ContactForm(StyledFormMixin, forms.Form):
    """Contact form. `website` is a honeypot: people never see it, bots fill it in."""

    name = forms.CharField(label="Your name", max_length=100)
    email = forms.EmailField(label="Your email", max_length=254)
    message = forms.CharField(label="Message", min_length=10, max_length=2000,
                              widget=forms.Textarea(attrs={"rows": 5}))
    website = forms.CharField(label="Leave this field empty", required=False, max_length=200,
                              widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    def clean_name(self):
        value = clean_text(self.cleaned_data["name"], max_length=100)
        if not value:
            raise forms.ValidationError("Please enter your name.")
        return value

    def clean_message(self):
        value = clean_text(self.cleaned_data["message"], multiline=True, max_length=2000)
        if len(value) < 10:
            raise forms.ValidationError("Please write at least 10 characters.")
        return value


def _choice(label, choices, help_text=""):
    return forms.TypedChoiceField(label=label, choices=choices, coerce=int, help_text=help_text)


YES_NO = [(0, "No"), (1, "Yes")]


class PredictionForm(StyledFormMixin, forms.Form):
    """The 13 health parameters. Codes follow the UCI Cleveland dataset coding."""

    patient_label = forms.CharField(label="Patient name / ID (optional)", required=False, max_length=100)

    # --- Personal details
    age = forms.IntegerField(label="Age (years)", min_value=AGE[0], max_value=AGE[1])
    sex = _choice("Sex", [(0, "Female"), (1, "Male")])

    # --- Symptoms
    cp = _choice("Chest pain type", [
        (1, "1 - Typical angina"),
        (2, "2 - Atypical angina"),
        (3, "3 - Non-anginal pain"),
        (4, "4 - Asymptomatic"),
    ], "UCI coding of the 'cp' column")
    exang = _choice("Exercise induced angina", YES_NO)

    # --- Vitals and blood tests
    trestbps = forms.IntegerField(label="Resting blood pressure (mm Hg)", min_value=BP[0], max_value=BP[1])
    chol = forms.IntegerField(label="Serum cholesterol (mg/dl)", min_value=CHOL[0], max_value=CHOL[1])
    fbs = _choice("Fasting blood sugar above 120 mg/dl", YES_NO)
    thalach = forms.IntegerField(label="Maximum heart rate achieved (bpm)", min_value=HR[0], max_value=HR[1])

    # --- ECG and other tests
    restecg = _choice("Resting ECG result", [
        (0, "0 - Normal"),
        (1, "1 - ST-T wave abnormality"),
        (2, "2 - Left ventricular hypertrophy"),
    ])
    oldpeak = forms.FloatField(
        label="ST depression induced by exercise", min_value=ST[0], max_value=ST[1],
        widget=forms.NumberInput(attrs={"step": "0.1"}),
    )
    slope = _choice("Slope of the peak exercise ST segment", [
        (1, "1 - Upsloping"),
        (2, "2 - Flat"),
        (3, "3 - Downsloping"),
    ])
    ca = _choice("Major vessels coloured by fluoroscopy", [(i, str(i)) for i in range(4)])
    thal = _choice("Thal test result", [
        (3, "3 - Normal"),
        (6, "6 - Fixed defect"),
        (7, "7 - Reversible defect"),
    ], "UCI coding of the 'thal' column")

    def clean_patient_label(self):
        return clean_text(self.cleaned_data.get("patient_label", ""), max_length=100)

    GROUPS = [
        ("Record", ["patient_label"]),
        ("Personal details", ["age", "sex"]),
        ("Symptoms", ["cp", "exang"]),
        ("Vitals and blood tests", ["trestbps", "chol", "fbs", "thalach"]),
        ("ECG and other tests", ["restecg", "oldpeak", "slope", "ca", "thal"]),
    ]

    def grouped(self):
        """Fields arranged in sections for the template."""
        return [(title, [self[name] for name in names]) for title, names in self.GROUPS]


def value_display(name, value):
    """Readable text for a stored value, e.g. cp=4 -> '4 - Asymptomatic'."""
    field = PredictionForm.base_fields[name]
    if isinstance(field, forms.TypedChoiceField):
        return dict(field.choices).get(value, value)
    return value


def describe(record):
    """List of (label, readable value) pairs for a saved PredictionRecord."""
    return [(PredictionForm.base_fields[name].label, value_display(name, getattr(record, name)))
            for name in ml.FEATURES]
