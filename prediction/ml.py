"""
Loads the trained model + preprocessor from the /model folder, makes predictions
and explains them.

This module does not import Django, so it can also be tested on its own.
"""
import json
from pathlib import Path

import joblib
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "model"
MODEL_FILE = MODEL_DIR / "heart_disease_model.pkl"
SCALER_FILE = MODEL_DIR / "scaler.pkl"          # imputer + StandardScaler
INFO_FILE = MODEL_DIR / "model_info.json"

FEATURES = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
            "thalach", "exang", "oldpeak", "slope", "ca", "thal"]

LABELS = {
    "age": "Age", "sex": "Sex", "cp": "Chest pain type", "trestbps": "Resting blood pressure",
    "chol": "Cholesterol", "fbs": "Fasting blood sugar > 120", "restecg": "Resting ECG",
    "thalach": "Maximum heart rate", "exang": "Exercise induced angina", "oldpeak": "ST depression",
    "slope": "ST segment slope", "ca": "Major vessels coloured", "thal": "Thal test",
}

# Valid input values (UCI coding). Used by the form, the CSV upload and the API.
NUMERIC_RANGES = {"age": (1, 120), "trestbps": (80, 250), "chol": (100, 600),
                  "thalach": (60, 250), "oldpeak": (0.0, 10.0)}
CATEGORY_VALUES = {"sex": {0, 1}, "cp": {1, 2, 3, 4}, "fbs": {0, 1}, "restecg": {0, 1, 2},
                   "exang": {0, 1}, "slope": {1, 2, 3}, "ca": {0, 1, 2, 3}, "thal": {3, 6, 7}}

LOW_LIMIT = 0.30      # below 30%  -> LOW
HIGH_LIMIT = 0.60     # 60% and up -> HIGH, in between -> MODERATE


class ModelNotAvailable(Exception):
    """Raised when the model files are missing or cannot be loaded."""


_cache = {}


def _load():
    if "model" not in _cache:
        try:
            _cache["model"] = joblib.load(MODEL_FILE)
            _cache["prep"] = joblib.load(SCALER_FILE)
        except Exception as exc:  # missing file, or pickle from another scikit-learn version
            raise ModelNotAvailable(
                "The prediction model could not be loaded. "
                "Run 'python train_model.py' in the project folder and restart the server."
            ) from exc
    return _cache["model"], _cache["prep"]


def model_loaded():
    try:
        _load()
        return True
    except ModelNotAvailable:
        return False


def risk_level(probability):
    """probability is a number between 0 and 1."""
    if probability < LOW_LIMIT:
        return "LOW"
    if probability < HIGH_LIMIT:
        return "MODERATE"
    return "HIGH"


def predict_many(frame):
    """frame: DataFrame with the 13 feature columns. Returns a list of probabilities (0-1)."""
    model, prep = _load()
    scaled = prep.transform(frame[FEATURES])
    return [float(p) for p in model.predict_proba(scaled)[:, 1]]


def predict_probability(values):
    """values: dict with the 13 feature names. Returns probability (0-1) of heart disease."""
    return predict_many(pd.DataFrame([[values[name] for name in FEATURES]], columns=FEATURES))[0]


def explain(values):
    """
    Feature-ablation explanation of one prediction.

    Each attribute in turn is replaced by the median value of the training data and the
    probability is recalculated. `delta` is the change in percentage points that the
    patient's real value causes compared with that typical value:
    positive = the value raises the risk, negative = it lowers the risk.

    Returns a list sorted by the size of the effect (largest first), or [] when the
    baseline is not available.
    """
    baseline = model_info().get("baseline")
    if not baseline:
        return []
    rows = [[values[name] for name in FEATURES]]
    for i, name in enumerate(FEATURES):
        changed = list(rows[0])
        changed[i] = baseline[name]
        rows.append(changed)
    probs = predict_many(pd.DataFrame(rows, columns=FEATURES))
    full = probs[0]
    result = [{"feature": name, "label": LABELS[name], "delta": round((full - probs[i + 1]) * 100, 1)}
              for i, name in enumerate(FEATURES)]
    return sorted(result, key=lambda d: -abs(d["delta"]))


def model_info():
    """Details written by train_model.py (empty dict if the file does not exist)."""
    try:
        return json.loads(INFO_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# =========================================================================== innovation
# 1) Reliability check  - the system tells the user when its own estimate should be trusted less.
# 2) What-if simulator  - shows how the estimate would change if modifiable values changed.
# Both describe the MODEL's behaviour (statistical association), not medical cause and effect.

# Values a person can influence over time, with commonly cited targets (not personal medical advice).
MODIFIABLE = {
    "trestbps": {"label": "Resting blood pressure", "unit": "mm Hg", "target": 120},
    "chol": {"label": "Serum cholesterol", "unit": "mg/dl", "target": 200},
    "fbs": {"label": "Fasting blood sugar above 120 mg/dl", "unit": "", "target": 0},
}

UNUSUAL_LOW_Q, UNUSUAL_HIGH_Q = 0.01, 0.99     # an input outside this band of the training data is "unusual"
BORDER_POINTS = 5.0                              # within 5 points of a risk-level limit = borderline


def training_ranges():
    """{feature: (low, high)} = 1st and 99th percentile of the training data (empty if unavailable)."""
    if "ranges" not in _cache:
        ranges = {}
        try:
            from ml_pipeline.data import load_dataset
            x, _ = load_dataset(BASE_DIR / "dataset" / "heart.csv", drop_missing=True)
            for name in NUMERIC_RANGES:
                ranges[name] = (float(x[name].quantile(UNUSUAL_LOW_Q)), float(x[name].quantile(UNUSUAL_HIGH_Q)))
        except Exception:                        # the check is optional; never break a prediction
            ranges = {}
        _cache["ranges"] = ranges
    return _cache["ranges"]


def _fold_probabilities(frame):
    """
    Probability from each cross-validation fold model inside the calibrated classifier.
    If the folds disagree a lot, the estimate is unstable. Returns [] when not available.
    """
    model, prep = _load()
    members = getattr(model, "calibrated_classifiers_", None)
    if not members or len(members) < 2:
        return []
    scaled = prep.transform(frame[FEATURES])
    try:
        return [float(m.predict_proba(scaled)[0, 1]) for m in members]
    except Exception:
        return []


def reliability(values):
    """
    How far can this particular estimate be trusted?

    Three independent signals:
      * unusual inputs   - values outside the 1st-99th percentile of the training data
      * fold disagreement - spread of probabilities of the cross-validation models
      * borderline       - the probability is close to a LOW / MODERATE / HIGH limit

    Returns {"level": "good|fair|low", "label", "reasons": [...], "range": (low%, high%) or None}.
    """
    frame = pd.DataFrame([[values[name] for name in FEATURES]], columns=FEATURES)
    probability = predict_many(frame)[0]
    score, reasons = 0, []

    unusual = [LABELS[n] for n, (lo, hi) in training_ranges().items() if not lo <= values[n] <= hi]
    if unusual:
        score += len(unusual)
        reasons.append("Unusual compared with the training data: " + ", ".join(unusual) + ".")

    folds = _fold_probabilities(frame)
    prob_range = None
    if folds:
        spread = (max(folds) - min(folds)) * 100
        prob_range = (round(min(folds) * 100, 1), round(max(folds) * 100, 1))
        if spread >= 20:
            score += 2
            reasons.append(f"The internal models disagree strongly (spread {spread:.0f} percentage points).")
        elif spread >= 10:
            score += 1
            reasons.append(f"The internal models differ noticeably (spread {spread:.0f} percentage points).")

    nearest = min(abs(probability - LOW_LIMIT), abs(probability - HIGH_LIMIT)) * 100
    if nearest < BORDER_POINTS:
        score += 1
        reasons.append("The estimate is close to a risk-level limit, so a small change could move it to another level.")

    level, label = ("good", "Good") if score == 0 else ("fair", "Fair") if score <= 2 else ("low", "Low")
    if not reasons:
        reasons.append("Inputs are typical for the training data and the internal models agree.")
    return {"level": level, "label": label, "reasons": reasons, "range": prob_range}


def _pts(difference):
    """Difference of two probabilities in percentage points (never prints -0.0)."""
    return round(difference * 100, 1) + 0.0


def validate_changes(changes):
    """Checks a what-if request {feature: value}. Returns clean numbers or raises ValueError."""
    if not isinstance(changes, dict) or not changes:
        raise ValueError("Send an object with at least one value.")
    clean = {}
    for name, value in changes.items():
        if name not in MODIFIABLE:
            raise ValueError(f"'{name}' cannot be changed in the simulator.")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a number.")
        if name in NUMERIC_RANGES:
            low, high = NUMERIC_RANGES[name]
            if not low <= value <= high:
                raise ValueError(f"{name} must be between {low} and {high}.")
        elif value not in CATEGORY_VALUES[name]:
            raise ValueError(f"{name} has an invalid value.")
        clean[name] = int(value)
    return clean


def what_if(values, changes):
    """Probability (percent) before and after applying `changes` (already validated)."""
    before, after = predict_many(pd.DataFrame(
        [[values[n] for n in FEATURES], [{**values, **changes}[n] for n in FEATURES]], columns=FEATURES))
    return {"before": round(before * 100, 1), "after": round(after * 100, 1),
            "delta": _pts(after - before), "risk_level": risk_level(after)}


def target_scenarios(values):
    """For every modifiable value above its target: the estimate if it were at the target."""
    chosen = [(n, m) for n, m in MODIFIABLE.items() if values[n] > m["target"]]
    if not chosen:
        return []
    rows = [[values[n] for n in FEATURES]] + [[{**values, n: m["target"]}[k] for k in FEATURES] for n, m in chosen]
    probs = predict_many(pd.DataFrame(rows, columns=FEATURES))
    return [{"feature": n, "label": m["label"], "unit": m["unit"], "current": values[n], "target": m["target"],
             "after": round(probs[i + 1] * 100, 1), "delta": _pts(probs[i + 1] - probs[0])}
            for i, (n, m) in enumerate(chosen)]
