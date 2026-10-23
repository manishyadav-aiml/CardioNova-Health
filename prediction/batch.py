"""
CSV batch prediction helpers. This module does not import Django.

The CSV needs the 13 columns of ml.FEATURES and may contain an optional `label` column
(patient name or ID).
"""
import io

import pandas as pd

from . import ml
from .sanitize import clean_text

MAX_ROWS = 500
MAX_COLUMNS = 40
MAX_BYTES = 1024 * 1024
SAMPLE_ROW = {"age": 55, "sex": 1, "cp": 4, "trestbps": 140, "chol": 250, "fbs": 0, "restecg": 1,
              "thalach": 130, "exang": 1, "oldpeak": 2.0, "slope": 2, "ca": 1, "thal": 7}


class BatchError(Exception):
    """The uploaded file cannot be processed (shown to the user)."""


def sample_csv():
    cols = ["label"] + ml.FEATURES
    return ",".join(cols) + "\n" + ",".join(["Patient 1"] + [str(SAMPLE_ROW[c]) for c in ml.FEATURES]) + "\n"


def parse(data):
    """bytes -> DataFrame (all columns as text/numbers, not yet validated)."""
    if len(data) > MAX_BYTES:
        raise BatchError("The file is larger than 1 MB.")
    if b"\x00" in data:
        raise BatchError("The file does not look like a text CSV file.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise BatchError("The file must be saved as UTF-8 text.") from exc
    try:
        # never read more than MAX_ROWS + 1 rows, so a huge file cannot use up the memory
        df = pd.read_csv(io.StringIO(text), skipinitialspace=True, nrows=MAX_ROWS + 1)
    except Exception as exc:
        raise BatchError("The file could not be read as a CSV file.") from exc
    if len(df.columns) > MAX_COLUMNS:
        raise BatchError(f"Too many columns. The limit is {MAX_COLUMNS}.")
    df.columns = [str(c).strip().lower()[:60] for c in df.columns]
    missing = [c for c in ml.FEATURES if c not in df.columns]
    if missing:
        raise BatchError("Missing columns: " + ", ".join(missing))
    if df.empty:
        raise BatchError("The file has no data rows.")
    if len(df) > MAX_ROWS:
        raise BatchError(f"Too many rows. The limit is {MAX_ROWS}.")
    return df


def validate(df):
    """
    Returns (valid_df, errors). valid_df has the 13 numeric columns plus `label`.
    errors is a list of (row number as in the file, message).
    """
    labels = df["label"].astype(str).str.strip().str[:100] if "label" in df.columns else pd.Series([""] * len(df))
    labels = labels.where(df["label"].notna(), "") if "label" in df.columns else labels
    labels = labels.map(lambda v: clean_text(v, max_length=100))        # no HTML or control characters
    errors, keep = [], []
    for idx, row in df.iterrows():
        problems = []
        for name in ml.FEATURES:
            value = pd.to_numeric(row[name], errors="coerce")
            if pd.isna(value):
                problems.append(f"{name} is missing or not a number")
            elif name in ml.NUMERIC_RANGES:
                low, high = ml.NUMERIC_RANGES[name]
                if not low <= value <= high:
                    problems.append(f"{name} must be between {low} and {high}")
            elif value not in ml.CATEGORY_VALUES[name]:
                allowed = ", ".join(str(v) for v in sorted(ml.CATEGORY_VALUES[name]))
                problems.append(f"{name} must be one of {allowed}")
        if problems:
            errors.append((idx + 2, "; ".join(problems)))      # +2: header row + 1-based numbering
        else:
            keep.append(idx)
    valid = df.loc[keep, ml.FEATURES].apply(pd.to_numeric).copy()
    valid["label"] = labels.loc[keep].values
    return valid.reset_index(drop=True), errors


def predict(valid):
    """Adds `probability` (percent) and `risk_level` columns."""
    if valid.empty:
        return valid.assign(probability=[], risk_level=[])
    probs = ml.predict_many(valid)
    out = valid.copy()
    out["probability"] = [round(p * 100, 1) for p in probs]
    out["risk_level"] = [ml.risk_level(p) for p in probs]
    return out
