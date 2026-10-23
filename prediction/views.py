import csv
import hashlib
import json
import logging
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Max, Q
from django.http import HttpResponse, HttpResponseServerError, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from . import batch, ml, report, security, site_content
from .forms import (BatchUploadForm, ContactForm, LoginForm, PredictionForm, ProfileForm,
                    RegisterForm, describe, value_display)
from .models import ContactMessage, DoctorAccessLog, PredictionRecord, Profile

logger = logging.getLogger("prediction")

ADVICE = {
    "LOW": "The model estimates a low probability. Keep up healthy habits and have regular check-ups.",
    "MODERATE": "The model estimates a moderate probability. Consider a medical check-up and review lifestyle factors such as diet, exercise and smoking.",
    "HIGH": "The model estimates a high probability. Please consult a qualified doctor for proper tests and advice.",
}
DISCLAIMER = ("Screening aid for educational purposes only. Not a medical diagnosis; "
              "it does not replace advice from a qualified healthcare professional.")


# --------------------------------------------------------------------------- helpers
def get_profile(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


def is_doctor(user):
    return user.is_authenticated and (user.is_superuser or get_profile(user).is_doctor)


def doctor_required(view):
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not is_doctor(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


def build_explanation(values):
    """Per-feature effect on the prediction, with readable values (stored with the record)."""
    return [{"feature": e["feature"], "label": e["label"],
             "value": str(value_display(e["feature"], values[e["feature"]])), "delta": e["delta"]}
            for e in ml.explain(values)]


def save_prediction(user, values, label, source, probability, explanation):
    return PredictionRecord.objects.create(
        user=user, patient_label=label, probability=round(probability * 100, 1),
        risk_level=ml.risk_level(probability), explanation=explanation,
        model_name=ml.model_info().get("best_model", ""), source=source, **values)


def csv_safe(text):
    """Stops spreadsheet programs from running a cell that starts with = + - @ (CSV / formula injection)."""
    text = str(text)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


# --------------------------------------------------------------------------- pages
def home(request):
    recent = []
    if request.user.is_authenticated:
        recent = request.user.predictions.all()[:5]
    return render(request, "prediction/home.html", {"recent": recent})


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST" and security.hit("register", security.client_ip(request)):
        return security.too_many_requests(request, wait_minutes=60)
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        utm = request.session.get("utm", {})                      # first-touch campaign data, if the visitor had any
        if utm:
            Profile.objects.filter(user=user).update(**{k: utm.get(k, "") for k in security.UTM_KEYS})
        login(request, user)
        messages.success(request, f"Welcome, {user.username}! Your account has been created.")
        return redirect("predict")
    return render(request, "prediction/register.html", {"form": form})


@login_required
def predict(request):
    form = PredictionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = dict(form.cleaned_data)
        label = data.pop("patient_label", "")
        try:
            probability = ml.predict_probability(data)
            explanation = build_explanation(data)
        except ml.ModelNotAvailable as exc:
            messages.error(request, str(exc))
            return render(request, "prediction/prediction.html", {"form": form})
        record = save_prediction(request.user, data, label, PredictionRecord.SOURCE_FORM, probability, explanation)
        logger.info("prediction id=%s user=%s level=%s", record.pk, request.user.pk, record.risk_level)
        return redirect("result", pk=record.pk)
    return render(request, "prediction/prediction.html", {"form": form})


def _can_view(user, record):
    """Owner, or a doctor when the patient shares data with doctors."""
    if record.user_id == user.id:
        return True
    if not is_doctor(user):
        return False
    owner = get_profile(record.user)
    return owner.role == Profile.ROLE_PATIENT and owner.share_with_doctors


def _values(record):
    """The 13 stored inputs of a record as a dict (read from the database, never from the browser)."""
    return {name: getattr(record, name) for name in ml.FEATURES}


def _log_access(viewer, record):
    """Doctors leave a trace every time they open somebody else's data; the patient can read this log."""
    if record.user_id != viewer.id:
        DoctorAccessLog.objects.create(doctor=viewer, patient=record.user, record=record)


@login_required
def result(request, pk):
    record = get_object_or_404(PredictionRecord, pk=pk)
    if not _can_view(request.user, record):
        raise PermissionDenied
    _log_access(request.user, record)
    factors = list(record.explanation or [])[:8]
    biggest = max((abs(f["delta"]) for f in factors), default=0) or 1
    for f in factors:
        f["width"] = round(abs(f["delta"]) / biggest * 100)
        f["up"] = f["delta"] > 0
    try:                                    # the two innovations; they never block the page
        trust = ml.reliability(_values(record))
        scenarios = ml.target_scenarios(_values(record))
    except ml.ModelNotAvailable:
        trust, scenarios = None, []
    summary = (f"Heart disease risk: {record.risk_level} ({record.probability:.1f}%). "
               f"Trust check: {trust['label'] if trust else 'not available'}. "
               "Screening aid only, not a diagnosis.")
    context = {
        "record": record, "rows": describe(record), "advice": ADVICE[record.risk_level],
        "level_class": record.risk_level.lower(), "factors": factors,
        "reliability": trust, "scenarios": scenarios, "summary_text": summary,
        "ranges": {"trestbps": ml.NUMERIC_RANGES["trestbps"], "chol": ml.NUMERIC_RANGES["chol"]},
        "is_owner": record.user_id == request.user.id,
    }
    return render(request, "prediction/result.html", context)


@login_required
@require_POST
def whatif(request, pk):
    """What-if simulator for the result page. The record comes from the database; only the changed values come from the browser."""
    if security.hit("whatif", request.user.pk):
        return _error("Too many requests. Please slow down for a moment.", 429)
    record = get_object_or_404(PredictionRecord, pk=pk)
    if not _can_view(request.user, record):
        raise PermissionDenied
    try:
        payload = json.loads(request.body or b"{}")
        changes = ml.validate_changes(payload.get("changes") if isinstance(payload, dict) else None)
    except ValueError as exc:
        return _error(str(exc), 400)
    try:
        return JsonResponse(ml.what_if(_values(record), changes))
    except ml.ModelNotAvailable as exc:
        return _error(str(exc), 503)


@login_required
@require_POST
def delete_record(request, pk):
    record = get_object_or_404(PredictionRecord, pk=pk, user=request.user)       # only the owner can delete
    record.delete()
    messages.success(request, "The prediction was deleted.")
    return redirect("history")


@login_required
def download_report(request, pk):
    record = get_object_or_404(PredictionRecord, pk=pk)
    if not _can_view(request.user, record):
        raise PermissionDenied
    _log_access(request.user, record)
    try:
        trust = ml.reliability(_values(record))
    except ml.ModelNotAvailable:
        trust = None
    pdf = report.build_report(record, describe(record), record.user.username, ADVICE[record.risk_level], trust)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="heart_risk_report_{record.pk}.pdf"'
    return response


def _history(request, subject, own):
    records = subject.predictions.all()
    level = request.GET.get("level", "").upper()
    if level in ("LOW", "MODERATE", "HIGH"):
        records = records.filter(risk_level=level)
    else:
        level = ""
    chart = [{"label": r.created_at.strftime("%d %b %H:%M"), "p": r.probability}
             for r in reversed(list(records[:50]))]
    page = Paginator(records, 15).get_page(request.GET.get("page"))
    context = {"subject": subject, "own": own, "page_obj": page, "chart_data": chart,
               "level": level, "total": records.count()}
    return render(request, "prediction/history.html", context)


@login_required
def history(request):
    return _history(request, request.user, own=True)


@login_required
def batch_predict(request):
    form = BatchUploadForm(request.POST or None, request.FILES or None)
    results, errors = None, []
    if request.method == "POST" and form.is_valid():
        try:
            valid, errors = batch.validate(batch.parse(form.cleaned_data["file"].read()))
            results = batch.predict(valid)
        except batch.BatchError as exc:
            form.add_error("file", str(exc))
        except ml.ModelNotAvailable as exc:
            messages.error(request, str(exc))
        else:
            if request.POST.get("action") == "download":
                response = HttpResponse(content_type="text/csv")
                response["Content-Disposition"] = 'attachment; filename="heart_risk_predictions.csv"'
                writer = csv.writer(response)
                writer.writerow(["label"] + ml.FEATURES + ["probability_percent", "risk_level"])
                for _, row in results.iterrows():
                    writer.writerow([csv_safe(row["label"])] + [row[f] for f in ml.FEATURES]
                                    + [row["probability"], row["risk_level"]])
                return response
            name = ml.model_info().get("best_model", "")
            PredictionRecord.objects.bulk_create([
                PredictionRecord(
                    user=request.user, patient_label=row["label"], probability=row["probability"],
                    risk_level=row["risk_level"], model_name=name, source=PredictionRecord.SOURCE_BATCH,
                    **{f: (float(row[f]) if f == "oldpeak" else int(row[f])) for f in ml.FEATURES})
                for _, row in results.iterrows()])
            logger.info("batch user=%s saved=%s rejected=%s", request.user.pk, len(results), len(errors))
            messages.success(request, f"{len(results)} prediction(s) saved to your history.")
    context = {"form": form, "errors": errors[:20], "error_count": len(errors),
               "results": results.to_dict("records") if results is not None else None,
               "features": ml.FEATURES}
    return render(request, "prediction/batch.html", context)


@login_required
def batch_template(request):
    response = HttpResponse(batch.sample_csv(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="batch_template.csv"'
    return response


@login_required
def profile(request):
    prof = get_profile(request.user)
    form = ProfileForm(request.POST or None, instance=prof)
    new_token = None
    if request.method == "POST":
        if request.POST.get("action") == "token":
            new_token = prof.new_api_token()          # shown once, only the hash is stored
        elif form.is_valid():
            form.save()
            messages.success(request, "Your settings were saved.")
            return redirect("profile")
    context = {"profile": prof, "form": form, "new_token": new_token,
               "has_token": bool(prof.api_token_hash), "doctor": is_doctor(request.user),
               "access_log": request.user.access_log.select_related("doctor")[:20]}
    return render(request, "prediction/profile.html", context)


@login_required
@require_POST
def delete_account(request):
    """Deletes the account and, through the foreign keys, every prediction. Needs the current password."""
    if security.is_limited("delete_account", request.user.pk):
        return security.too_many_requests(request, wait_minutes=60)
    if not request.user.check_password(request.POST.get("password", "")):
        security.hit("delete_account", request.user.pk)
        messages.error(request, "The password was not correct. Your account was not deleted.")
        return redirect("profile")
    user = request.user
    logout(request)
    user.delete()
    messages.success(request, "Your account and all your predictions were deleted.")
    return redirect("home")


def model_details(request):
    info = ml.model_info()
    top = max((f["importance"] for f in info.get("feature_importance", [])), default=0) or 1
    for f in info.get("feature_importance", []):
        f["bar"] = round(f["importance"] / top * 100)
    return render(request, "prediction/model.html", {"info": info})


# --------------------------------------------------------------------------- doctor
@doctor_required
def doctor_dashboard(request):
    shared = {"profile__role": Profile.ROLE_PATIENT, "profile__share_with_doctors": True}
    patients = User.objects.filter(predictions__isnull=False, **shared)
    query = request.GET.get("q", "").strip()
    if query:
        patients = patients.filter(username__icontains=query)
    patients = list(patients.annotate(n=Count("predictions"), last=Max("predictions__created_at"))
                    .order_by("-last")[:100])
    for p in patients:
        p.latest = p.predictions.first()               # one small query per listed patient
    counts = {"LOW": 0, "MODERATE": 0, "HIGH": 0}
    for row in (PredictionRecord.objects.filter(user__profile__role=Profile.ROLE_PATIENT,
                                                user__profile__share_with_doctors=True)
                .values("risk_level").annotate(n=Count("id"))):
        counts[row["risk_level"]] = row["n"]
    context = {"patients": patients, "q": query, "counts": counts, "total": sum(counts.values()),
               "chart_data": [counts["LOW"], counts["MODERATE"], counts["HIGH"]]}
    return render(request, "prediction/doctor_dashboard.html", context)


@doctor_required
def doctor_patient(request, user_id):
    patient = get_object_or_404(User, pk=user_id, profile__role=Profile.ROLE_PATIENT,
                                profile__share_with_doctors=True)
    DoctorAccessLog.objects.create(doctor=request.user, patient=patient)
    return _history(request, patient, own=False)


# --------------------------------------------------------------------------- JSON API
def _api_user(request):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Token "):
        return None
    digest = hashlib.sha256(header[6:].strip().encode()).hexdigest()
    prof = Profile.objects.select_related("user").filter(api_token_hash=digest).first()
    return prof.user if prof and prof.user.is_active else None


def _api_limited(user):
    return security.hit("api", user.pk)


def _error(message, status, **extra):
    return JsonResponse({"error": message, **extra}, status=status)


@require_http_methods(["GET"])
def api_health(request):
    return JsonResponse({"status": "ok", "model_loaded": ml.model_loaded(),
                         "model": ml.model_info().get("best_model")})


@csrf_exempt
@require_http_methods(["POST"])
def api_predict(request):
    user = _api_user(request)
    if user is None:
        return _error("Missing or invalid API token. Send the header 'Authorization: Token <token>'.", 401)
    if _api_limited(user):
        return security.too_many_requests(request, wait_minutes=1)
    try:
        payload = json.loads(request.body or b"{}")
        if not isinstance(payload, dict):
            raise ValueError
    except ValueError:
        return _error("The request body must be a JSON object.", 400)

    form = PredictionForm(payload)
    if not form.is_valid():
        return _error("Invalid input.", 400, fields={k: list(v) for k, v in form.errors.items()})
    data = dict(form.cleaned_data)
    label = data.pop("patient_label", "")
    try:
        probability = ml.predict_probability(data)
        explanation = build_explanation(data)
    except ml.ModelNotAvailable as exc:
        return _error(str(exc), 503)

    body = {"probability_percent": round(probability * 100, 1), "risk_level": ml.risk_level(probability),
            "top_factors": [{"feature": e["feature"], "effect_points": e["delta"]} for e in explanation[:5]],
            "model": ml.model_info().get("best_model"), "disclaimer": DISCLAIMER}
    trust = ml.reliability(data)
    body["reliability"] = {"level": trust["level"], "reasons": trust["reasons"], "probability_range_percent": trust["range"]}
    if payload.get("save") is True:
        body["record_id"] = save_prediction(user, data, label, PredictionRecord.SOURCE_API,
                                            probability, explanation).pk
    logger.info("api prediction user=%s level=%s", user.pk, body["risk_level"])
    return JsonResponse(body)


@csrf_exempt
@require_http_methods(["POST"])
def api_whatif(request):
    """Body: the 13 values plus {"changes": {"trestbps": 120, "chol": 200}}."""
    user = _api_user(request)
    if user is None:
        return _error("Missing or invalid API token.", 401)
    if _api_limited(user):
        return security.too_many_requests(request, wait_minutes=1)
    try:
        payload = json.loads(request.body or b"{}")
        if not isinstance(payload, dict):
            raise ValueError("The request body must be a JSON object.")
        changes = ml.validate_changes(payload.get("changes"))
    except ValueError as exc:
        return _error(str(exc), 400)
    form = PredictionForm(payload)
    if not form.is_valid():
        return _error("Invalid input.", 400, fields={k: list(v) for k, v in form.errors.items()})
    data = dict(form.cleaned_data)
    data.pop("patient_label", None)
    try:
        return JsonResponse({**ml.what_if(data, changes), "disclaimer": DISCLAIMER})
    except ml.ModelNotAvailable as exc:
        return _error(str(exc), 503)


@require_http_methods(["GET"])
def api_history(request):
    user = _api_user(request)
    if user is None:
        return _error("Missing or invalid API token.", 401)
    if _api_limited(user):
        return security.too_many_requests(request, wait_minutes=1)
    try:
        limit = max(1, min(int(request.GET.get("limit", 20)), 100))
    except ValueError:
        limit = 20
    items = [{"id": r.pk, "created_at": r.created_at.isoformat(), "label": r.patient_label,
              "probability_percent": r.probability, "risk_level": r.risk_level, "source": r.source}
             for r in user.predictions.all()[:limit]]
    return JsonResponse({"count": len(items), "results": items})


# --------------------------------------------------------------------------- login with rate limiting
class RateLimitedLoginView(auth_views.LoginView):
    """Login that locks after repeated wrong passwords (per IP + username, and per IP)."""
    template_name = "prediction/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def _ids(self):
        username = (self.request.POST.get("username") or "").strip().lower()[:150]
        ip = security.client_ip(self.request)
        return ip, f"{ip}|{username}"

    def post(self, request, *args, **kwargs):
        ip, pair = self._ids()
        if security.is_limited("login_fail", pair) or security.is_limited("login_ip", ip):
            logger.warning("login blocked ip_hash=%s", security.ip_fingerprint(request))
            return security.too_many_requests(request)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        ip, pair = self._ids()
        security.hit("login_fail", pair)
        security.hit("login_ip", ip)
        logger.warning("failed login ip_hash=%s", security.ip_fingerprint(self.request))     # no username, no password
        return super().form_invalid(form)

    def form_valid(self, form):
        security.reset("login_fail", self._ids()[1])
        return super().form_valid(form)


# --------------------------------------------------------------------------- site pages
def faq(request):
    return render(request, "prediction/faq.html", {"faq": site_content.FAQ})


def privacy(request):
    return render(request, "prediction/privacy.html")


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST":
        if security.hit("contact", security.client_ip(request)):
            return security.too_many_requests(request, wait_minutes=60)
        if form.is_valid():
            if not form.cleaned_data.get("website"):                 # honeypot empty = a human
                ContactMessage.objects.create(
                    name=form.cleaned_data["name"], email=form.cleaned_data["email"],
                    message=form.cleaned_data["message"], ip_hash=security.ip_fingerprint(request))
            return redirect(reverse("contact") + "?sent=1")          # bots also see the success page
    return render(request, "prediction/contact.html", {"form": form, "sent": request.GET.get("sent") == "1"})


def search(request):
    """Site search: pages, FAQ and (for a logged-in user) the user's OWN prediction history."""
    query = request.GET.get("q", "").strip()[:100]
    pages, answers, records = [], [], []
    if len(query) >= 2:
        needle = query.lower()
        pages = [{"title": t, "url": reverse(name), "text": text}
                 for t, name, text, needs_login in site_content.PAGES
                 if (request.user.is_authenticated or not needs_login) and needle in f"{t} {text}".lower()]
        answers = [{"q": q, "a": a} for q, a in site_content.FAQ if needle in f"{q} {a}".lower()]
        if request.user.is_authenticated:
            records = list(request.user.predictions.filter(
                Q(patient_label__icontains=query) | Q(risk_level__iexact=query))[:20])
    return render(request, "prediction/search.html", {
        "q": query, "pages": pages, "answers": answers, "records": records, "too_short": 0 < len(query) < 2})


# --------------------------------------------------------------------------- error pages (no technical details)
def _error_page(request, status, title, message):
    if request.path.startswith("/api/"):
        return JsonResponse({"error": title}, status=status)
    return render(request, "prediction/error.html", {"code": status, "title": title, "message": message}, status=status)


def error_400(request, exception=None):
    return _error_page(request, 400, "Bad request", "The request could not be understood.")


def error_403(request, exception=None):
    return _error_page(request, 403, "Access denied", "You do not have permission to open this page.")


def error_404(request, exception=None):
    return _error_page(request, 404, "Page not found", "This page does not exist or was moved.")


def error_500(request):
    if request.path.startswith("/api/"):
        return JsonResponse({"error": "Server error"}, status=500)
    return HttpResponseServerError(render_to_string("prediction/500.html"))      # static page: no database needed


def csrf_failure(request, reason=""):
    return _error_page(request, 403, "Session expired", "The form is no longer valid. Reload the page and try again.")
