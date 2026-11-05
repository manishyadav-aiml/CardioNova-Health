"""
Input drift monitoring: are the people using the app still similar to the people the model was trained on?

train_model.py stores a compact reference of the training inputs (bin edges and shares for numbers, category
shares for the rest). This module compares the inputs of recent predictions with that reference.

Measure: Population Stability Index (PSI), the usual drift score in credit-risk and ML monitoring.
    PSI = sum over bins of (share_now - share_train) * ln(share_now / share_train)
    Rule of thumb: < 0.10 stable, 0.10 to 0.25 watch, 0.25 or more drift.
PSI is inflated on small samples (about (bins - 1) / n even when nothing changed), so that expected noise is
subtracted first ("adjusted PSI"), and nothing is judged below MIN_RECORDS records.

Pure Python (standard library only). No patient identity is used anywhere; only the 13 input values.
"""
import bisect
import math
import statistics

NUMERIC = ("age", "trestbps", "chol", "thalach", "oldpeak")
CATEGORICAL = ("sex", "cp", "fbs", "restecg", "exang", "slope", "ca", "thal")
MIN_RECORDS = 30
WATCH, DRIFT = 0.10, 0.25
RANGE_SHARE_WATCH = 0.25          # share of records with at least one input outside the training 1st-99th percentile
EPS = 1e-4


def _quantile(sorted_values, q):
    if not sorted_values:
        return 0.0
    position = q * (len(sorted_values) - 1)
    low, high = int(math.floor(position)), int(math.ceil(position))
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (position - low)


def _bin(value, edges):
    return bisect.bisect_right(edges, value)


def _shares(counts):
    total = sum(counts)
    return [c / total for c in counts] if total else [0.0] * len(counts)


def build_reference(columns, bins=5):
    """
    columns: {feature: [values]} for the training data. Returns a JSON-friendly reference.
    """
    n = len(next(iter(columns.values())))
    reference = {"n": n, "numeric": {}, "categorical": {}}
    for name in NUMERIC:
        values = sorted(float(v) for v in columns[name])
        edges = sorted({round(_quantile(values, i / bins), 6) for i in range(1, bins)})
        counts = [0] * (len(edges) + 1)
        for v in values:
            counts[_bin(v, edges)] += 1
        reference["numeric"][name] = {
            "edges": edges, "shares": [round(s, 6) for s in _shares(counts)],
            "mean": round(statistics.fmean(values), 4), "sd": round(statistics.pstdev(values), 4),
            "low": round(_quantile(values, 0.01), 4), "high": round(_quantile(values, 0.99), 4)}
    for name in CATEGORICAL:
        counts = {}
        for v in columns[name]:
            key = str(int(v))
            counts[key] = counts.get(key, 0) + 1
        reference["categorical"][name] = {k: round(c / n, 6) for k, c in sorted(counts.items())}
    return reference


def psi(expected, actual):
    """Population Stability Index between two lists of shares of equal length."""
    total = 0.0
    for e, a in zip(expected, actual):
        e, a = max(e, EPS), max(a, EPS)
        total += (a - e) * math.log(a / e)
    return total


def status_for(adjusted):
    return "drift" if adjusted >= DRIFT else "watch" if adjusted >= WATCH else "stable"


def out_of_range(values, ranges):
    """Names of the inputs outside the training range. ranges: {feature: (low, high)}."""
    return [name for name, (low, high) in ranges.items() if name in values and not low <= values[name] <= high]


def compare(reference, rows):
    """
    rows: list of dicts with the 13 inputs (recent predictions).
    Returns {"n", "overall", "features": [...], "out_of_range_share", "flagged": [...]}.
    """
    n = len(rows)
    result = {"n": n, "overall": "insufficient", "features": [], "out_of_range_share": None, "flagged": [],
              "min_records": MIN_RECORDS, "training_records": reference.get("n")}
    if n < MIN_RECORDS:
        return result

    for name in NUMERIC:
        ref = reference["numeric"][name]
        counts = [0] * (len(ref["edges"]) + 1)
        for row in rows:
            counts[_bin(float(row[name]), ref["edges"])] += 1
        score = psi(ref["shares"], _shares(counts))
        adjusted = max(0.0, score - (len(counts) - 1) / n)
        mean_now = statistics.fmean(float(r[name]) for r in rows)
        shift = (mean_now - ref["mean"]) / ref["sd"] if ref["sd"] else 0.0
        result["features"].append({
            "name": name, "kind": "number", "psi": round(score, 3), "adjusted": round(adjusted, 3),
            "status": status_for(adjusted),
            "detail": f"mean {mean_now:.1f} now vs {ref['mean']:.1f} in training ({shift:+.2f} SD)"})

    for name in CATEGORICAL:
        ref = reference["categorical"][name]
        keys = sorted(set(ref) | {str(int(r[name])) for r in rows})
        counts = [sum(1 for r in rows if str(int(r[name])) == k) for k in keys]
        score = psi([ref.get(k, 0.0) for k in keys], _shares(counts))
        adjusted = max(0.0, score - (len(keys) - 1) / n)
        unseen = [k for k in keys if k not in ref and counts[keys.index(k)]]
        detail = "share per value now: " + ", ".join(f"{k}: {c / n:.0%}" for k, c in zip(keys, counts))
        if unseen:
            detail += f"; values never seen in training: {', '.join(unseen)}"
        result["features"].append({"name": name, "kind": "category", "psi": round(score, 3), "adjusted": round(adjusted, 3),
                                   "status": status_for(adjusted), "detail": detail})

    ranges = {name: (ref["low"], ref["high"]) for name, ref in reference["numeric"].items()}
    outside = sum(1 for row in rows if out_of_range(row, ranges))
    result["out_of_range_share"] = round(outside / n, 3)
    result["flagged"] = [f["name"] for f in result["features"] if f["status"] == "drift"]
    watch = [f["name"] for f in result["features"] if f["status"] == "watch"]
    if result["flagged"] or result["out_of_range_share"] > 2 * RANGE_SHARE_WATCH:
        result["overall"] = "drift"
    elif watch or result["out_of_range_share"] > RANGE_SHARE_WATCH:
        result["overall"] = "watch"
    else:
        result["overall"] = "stable"
    return result
