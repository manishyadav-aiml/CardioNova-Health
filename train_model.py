"""
Trains, tunes, compares, calibrates and evaluates the heart disease models.

    python train_model.py            full hyper-parameter search (about 1-3 minutes)
    python train_model.py --quick    smaller search (for a fast test / CI)

Steps
  1. Load dataset/heart.csv (rows with missing values are removed)
  2. Stratified 80/20 train/test split
  3. Tune 6 models with GridSearchCV (5-fold stratified CV, ROC-AUC)
  4. Build two ensembles (soft Voting and Stacking) from the tuned models
  5. Select the model with the best cross-validation ROC-AUC (training data only)
  6. Calibrate the probabilities (sigmoid, 5-fold); the fold models also feed the app's trust check
  7. Evaluate once on the untouched test set and on every external dataset
  8. Compute permutation feature importance and the baseline used for explanations
  9. Save model files, charts for the web app and model/model_info.json
"""
import argparse
import json
import os
import warnings
from datetime import datetime
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd
import sklearn

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from sklearn.base import clone  # noqa: E402
from sklearn.calibration import CalibratedClassifierCV, calibration_curve  # noqa: E402
from sklearn.ensemble import (GradientBoostingClassifier, RandomForestClassifier,  # noqa: E402
                              StackingClassifier, VotingClassifier)
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import (accuracy_score, brier_score_loss, confusion_matrix,  # noqa: E402
                             f1_score, precision_score, recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import (GridSearchCV, StratifiedKFold, cross_val_score,  # noqa: E402
                                     train_test_split)
from sklearn.neighbors import KNeighborsClassifier  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402
from sklearn.svm import SVC  # noqa: E402
from sklearn.tree import DecisionTreeClassifier  # noqa: E402

from ml_pipeline.data import FEATURES, load_dataset, overlap_mask  # noqa: E402
from ml_pipeline import tracking  # noqa: E402
from prediction import drift  # noqa: E402
from prediction.ml import (LOW_LIMIT, NUMERIC_RANGES, UNUSUAL_HIGH_Q, UNUSUAL_LOW_Q, input_warnings,  # noqa: E402
                           signal_points, trust_level)   # the app's own rules; no Django needed

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent
DATASET = BASE_DIR / "dataset" / "heart.csv"
EXTERNAL_DIR = BASE_DIR / "dataset" / "external"
DEMO_MARKER = BASE_DIR / "dataset" / "DEMO_DATA.txt"
MODEL_DIR = BASE_DIR / "model"
REPORT_DIR = BASE_DIR / "prediction" / "static" / "prediction" / "reports"
SEED = 42

FULL_GRIDS = {
    "Logistic Regression": (LogisticRegression(max_iter=2000),
                            {"clf__C": [0.01, 0.1, 1, 10], "clf__class_weight": [None, "balanced"]}),
    "K-Nearest Neighbors": (KNeighborsClassifier(),
                            {"clf__n_neighbors": [3, 5, 7, 9, 11, 15], "clf__weights": ["uniform", "distance"]}),
    "Support Vector Machine": (SVC(probability=True, random_state=SEED),
                               {"clf__C": [0.1, 1, 10], "clf__gamma": ["scale", 0.01, 0.1]}),
    "Decision Tree": (DecisionTreeClassifier(random_state=SEED),
                      {"clf__max_depth": [2, 3, 4, 5], "clf__min_samples_leaf": [1, 5, 10]}),
    "Random Forest": (RandomForestClassifier(random_state=SEED),
                      {"clf__n_estimators": [200, 400], "clf__max_depth": [None, 4, 6],
                       "clf__min_samples_leaf": [1, 3]}),
    "Gradient Boosting": (GradientBoostingClassifier(random_state=SEED),
                          {"clf__n_estimators": [100, 200], "clf__learning_rate": [0.05, 0.1],
                           "clf__max_depth": [2, 3]}),
}
QUICK_GRIDS = {
    "Logistic Regression": (LogisticRegression(max_iter=2000), {"clf__C": [0.1, 1]}),
    "K-Nearest Neighbors": (KNeighborsClassifier(), {"clf__n_neighbors": [7, 11]}),
    "Support Vector Machine": (SVC(probability=True, random_state=SEED), {"clf__C": [1, 10]}),
    "Decision Tree": (DecisionTreeClassifier(random_state=SEED), {"clf__max_depth": [3, 4]}),
    "Random Forest": (RandomForestClassifier(random_state=SEED, n_estimators=150), {"clf__max_depth": [4, None]}),
    "Gradient Boosting": (GradientBoostingClassifier(random_state=SEED, n_estimators=100), {"clf__max_depth": [2, 3]}),
}


def preprocessor():
    return Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])


def metrics_for(y_true, prob, threshold=0.5):
    pred = (prob >= threshold).astype(int)
    out = {
        "accuracy": accuracy_score(y_true, pred),
        "precision": precision_score(y_true, pred, zero_division=0),
        "recall": recall_score(y_true, pred, zero_division=0),
        "f1": f1_score(y_true, pred, zero_division=0),
        "brier": brier_score_loss(y_true, prob),
    }
    out["roc_auc"] = roc_auc_score(y_true, prob) if len(set(y_true)) > 1 else None
    return {k: (round(float(v), 3) if v is not None else None) for k, v in out.items()}


def bootstrap_ci(y_true, prob, threshold=0.5, n_boot=2000, seed=SEED):
    """95% bootstrap intervals for the test-set metrics (the test set is small, so single numbers can mislead)."""
    rng = np.random.default_rng(seed)
    y_true, prob = np.asarray(y_true), np.asarray(prob)
    pred = (prob >= threshold).astype(int)
    samples = {"accuracy": [], "precision": [], "recall": [], "roc_auc": []}
    for _ in range(n_boot):
        idx = rng.integers(0, len(y_true), len(y_true))
        yt = y_true[idx]
        if yt.min() == yt.max():
            continue
        samples["accuracy"].append(accuracy_score(yt, pred[idx]))
        samples["precision"].append(precision_score(yt, pred[idx], zero_division=0))
        samples["recall"].append(recall_score(yt, pred[idx], zero_division=0))
        samples["roc_auc"].append(roc_auc_score(yt, prob[idx]))
    return {k: [round(float(np.percentile(v, 2.5)), 3), round(float(np.percentile(v, 97.5)), 3)] for k, v in samples.items()}


def wilson(errors, n, z=1.96):
    """95% Wilson interval for a proportion (reliable for small groups)."""
    if n == 0:
        return [0.0, 0.0]
    p = errors / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(float(max(0, centre - half)), 3), round(float(min(1, centre + half)), 3)]


def evaluate_trust_check(X, y, estimator, n_splits=10):
    """
    Does the app's trust check really warn about wrong predictions?
    Nested cross-validation on ALL records: every record is predicted by a model that never saw it, and its
    trust level is computed with the same rules as the web app (percentile ranges come from the training folds only).
    Then the error rate (50% cut-off) is compared between Good / Fair / Low.
    """
    rows = []
    outer = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    for train_idx, test_idx in outer.split(X, y):
        x_tr, x_te, y_tr, y_te = X.iloc[train_idx], X.iloc[test_idx], y.iloc[train_idx], y.iloc[test_idx]
        prep_fold = preprocessor().fit(x_tr)
        model = CalibratedClassifierCV(clone(estimator), method="sigmoid", cv=5).fit(prep_fold.transform(x_tr), y_tr)
        x_te_t = prep_fold.transform(x_te)
        prob = model.predict_proba(x_te_t)[:, 1]
        members = np.column_stack([m.predict_proba(x_te_t)[:, 1] for m in model.calibrated_classifiers_])
        spread = (members.max(axis=1) - members.min(axis=1)) * 100
        ranges = {n: (x_tr[n].quantile(UNUSUAL_LOW_Q), x_tr[n].quantile(UNUSUAL_HIGH_Q)) for n in NUMERIC_RANGES}
        for i in range(len(x_te)):
            values = x_te.iloc[i].to_dict()
            unusual = sum(1 for n, (lo, hi) in ranges.items() if not lo <= values[n] <= hi)
            points = signal_points(prob[i], unusual, spread[i], len(input_warnings(values)))
            score = sum(points.values())
            rows.append({"score": score, "level": trust_level(score)[0], "wrong": int((prob[i] >= 0.5) != bool(y_te.iloc[i])),
                         "brier": float((prob[i] - y_te.iloc[i]) ** 2)})
    df = pd.DataFrame(rows)
    levels = {}
    for name in ("good", "fair", "low"):
        part = df[df["level"] == name]
        errors, n = int(part["wrong"].sum()), int(len(part))
        ci = wilson(errors, n)
        levels[name] = {"n": n, "errors": errors, "error_rate": round(errors / n, 3) if n else None,
                        "error_pct": round(100 * errors / n, 1) if n else None, "ci": ci,
                        "ci_pct": [round(100 * ci[0], 1), round(100 * ci[1], 1)],
                        "brier": round(float(part["brier"].mean()), 3) if n else None}
    selective = []
    for label, keep in (("all records", ["good", "fair", "low"]), ("Good + Fair only", ["good", "fair"]), ("Good only", ["good"])):
        part = df[df["level"].isin(keep)]
        if len(part):
            selective.append({"answered": label, "coverage": round(len(part) / len(df), 3),
                              "coverage_pct": round(100 * len(part) / len(df), 1),
                              "accuracy": round(1 - part["wrong"].mean(), 3),
                              "accuracy_pct": round(100 * (1 - part["wrong"].mean()), 1), "n": int(len(part))})
    auc = None
    if df["wrong"].nunique() == 2 and df["score"].nunique() > 1:
        auc = round(float(roc_auc_score(df["wrong"], df["score"])), 3)
    return {"method": f"{n_splits}-fold nested cross-validation on all {len(df)} records; each record is scored by a model that "
                      "never saw it; trust computed with the web app's own rules (training ranges from the training folds only)",
            "n": int(len(df)), "levels": levels, "selective": selective, "auc_score_vs_error": auc}


def evaluate_external(paths, final_model, prep, X_train, X_reference):
    """
    External validation: the final model (trained on the Cleveland file ONLY) is tested on other hospitals' data.
    Rows that are identical to a Cleveland record (X_reference) are removed first: copies of the training data are not
    external data and would inflate every number. Files that are mostly copies, or that cannot be read, are skipped
    and listed. Returns (results, skipped).
    Reports each site, a pooled result, and (for 100+ pooled records) the error rate per trust level, so you can see
    whether the trust check still warns about mistakes on data from another population.
    """
    ranges = {n: (X_train[n].quantile(UNUSUAL_LOW_Q), X_train[n].quantile(UNUSUAL_HIGH_Q)) for n in NUMERIC_RANGES}
    results, skipped, all_y, all_prob, trust_rows = {}, [], [], [], []
    for path in paths:
        try:
            Xe, ye = load_dataset(path, drop_missing=False)
        except ValueError as exc:
            print("Skipping", path.name, "-", exc)
            skipped.append({"file": path.name, "reason": str(exc)})
            continue
        copies = int(overlap_mask(X_reference, Xe).sum())
        if copies:
            keep = ~overlap_mask(X_reference, Xe)
            Xe, ye = Xe[keep], ye[keep]
            print(f"WARNING {path.name}: removed {copies} rows that are identical to Cleveland training records")
        if len(Xe) < 20:
            reason = (f"{copies} rows are copies of the Cleveland training records, so this is not independent data"
                      if copies else "fewer than 20 usable records")
            print("Skipping", path.name, "-", reason)
            skipped.append({"file": path.name, "reason": reason})
            continue
        Xt = prep.transform(Xe)
        prob = final_model.predict_proba(Xt)[:, 1]
        members = np.column_stack([m.predict_proba(Xt)[:, 1] for m in final_model.calibrated_classifiers_])
        spread = (members.max(axis=1) - members.min(axis=1)) * 100
        for i in range(len(Xe)):
            values = Xe.iloc[i].to_dict()
            unusual = sum(1 for n, (lo, hi) in ranges.items() if pd.notna(values[n]) and not lo <= values[n] <= hi)
            score = sum(signal_points(prob[i], unusual, spread[i], len(input_warnings(values))).values())
            trust_rows.append({"level": trust_level(score)[0], "wrong": int((prob[i] >= 0.5) != bool(ye.iloc[i]))})
        m = metrics_for(ye, prob)
        m["recall_at_low_limit"] = metrics_for(ye, prob, threshold=LOW_LIMIT)["recall"]
        m["rows"], m["positive_rate"] = int(len(Xe)), round(float(ye.mean()), 3)
        m["missing_share"] = round(float(Xe.isna().mean().mean()), 3)
        m["overlap_removed"] = copies
        results[path.name] = m
        all_y.extend(ye.tolist())
        all_prob.extend(prob.tolist())
        print(f"External {path.name}: {m}")
    if len(results) >= 2:
        pooled = metrics_for(np.array(all_y), np.array(all_prob))
        pooled["recall_at_low_limit"] = metrics_for(np.array(all_y), np.array(all_prob), threshold=LOW_LIMIT)["recall"]
        pooled["rows"], pooled["positive_rate"] = len(all_y), round(float(np.mean(all_y)), 3)
        frame = pd.DataFrame(trust_rows)
        if len(frame) >= 100:
            levels = {}
            for name in ("good", "fair", "low"):
                part = frame[frame["level"] == name]
                errors, n = int(part["wrong"].sum()), int(len(part))
                levels[name] = {"n": n, "errors": errors, "error_pct": round(100 * errors / n, 1) if n else None}
            pooled["trust_levels"] = levels
        results["pooled"] = pooled
        print("External pooled:", pooled)
    return results, skipped


def main(quick, use_mlflow=False):
    print("Loading", DATASET)
    X, y = load_dataset(DATASET, drop_missing=True)
    print(f"{len(X)} usable records  (class 0: {(y == 0).sum()}, class 1: {(y == 1).sum()})")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)

    # ---- 3. tune the single models
    grids = QUICK_GRIDS if quick else FULL_GRIDS
    tuned, results = {}, {}
    for name, (est, grid) in grids.items():
        pipe = Pipeline([("prep", preprocessor()), ("clf", est)])
        search = GridSearchCV(pipe, grid, scoring="roc_auc", cv=cv, n_jobs=1).fit(X_train, y_train)
        tuned[name] = search.best_estimator_
        results[name] = {"cv_roc_auc": float(search.best_score_),
                         "best_params": {k.replace("clf__", ""): v for k, v in search.best_params_.items()}}
        print(f"{name:<24} CV ROC-AUC = {search.best_score_:.3f}   {results[name]['best_params']}")

    # ---- 4. ensembles built from the tuned models
    def part(name):
        return clone(tuned[name].named_steps["clf"])

    ensembles = {
        "Voting Ensemble": VotingClassifier(
            [("lr", part("Logistic Regression")), ("svm", part("Support Vector Machine")),
             ("rf", part("Random Forest"))], voting="soft"),
        "Stacking Ensemble": StackingClassifier(
            [("lr", part("Logistic Regression")), ("svm", part("Support Vector Machine")),
             ("rf", part("Random Forest")), ("gb", part("Gradient Boosting"))],
            final_estimator=LogisticRegression(max_iter=2000), cv=5, stack_method="predict_proba"),
    }
    for name, est in ensembles.items():
        pipe = Pipeline([("prep", preprocessor()), ("clf", est)])
        score = cross_val_score(pipe, X_train, y_train, cv=cv, scoring="roc_auc").mean()
        tuned[name] = pipe.fit(X_train, y_train)
        results[name] = {"cv_roc_auc": float(score), "best_params": {}}
        print(f"{name:<24} CV ROC-AUC = {score:.3f}")

    # ---- test-set results of every candidate (reported only, NOT used for selection)
    test_probs = {}
    for name, pipe in tuned.items():
        test_probs[name] = pipe.predict_proba(X_test)[:, 1]
        results[name]["test"] = metrics_for(y_test, test_probs[name])

    # ---- 5. selection on cross-validation only
    best_name = max(results, key=lambda n: results[n]["cv_roc_auc"])
    print("\nSelected model:", best_name)
    best_pipe = tuned[best_name]
    prep = best_pipe.named_steps["prep"]
    X_train_t, X_test_t = prep.transform(X_train), prep.transform(X_test)
    base_clf = best_pipe.named_steps["clf"]

    # ---- 6. probability calibration
    raw_brier = -cross_val_score(clone(base_clf), X_train_t, y_train, cv=cv, scoring="neg_brier_score").mean()
    calibrated = CalibratedClassifierCV(clone(base_clf), method="sigmoid", cv=5)
    cal_brier = -cross_val_score(calibrated, X_train_t, y_train, cv=cv, scoring="neg_brier_score").mean()
    # Always calibrate: the Brier difference is tiny (see the printout) and the trust check in the web app
    # needs the cross-validation fold models that CalibratedClassifierCV keeps.
    use_cal = True
    final_model = (CalibratedClassifierCV(clone(base_clf), method="sigmoid", cv=5).fit(X_train_t, y_train)
                   if use_cal else base_clf)
    print(f"CV Brier score: raw {raw_brier:.4f}  calibrated {cal_brier:.4f}  -> "
          f"{'calibrated' if use_cal else 'raw'} model used")

    # ---- 7. final evaluation
    final_prob = final_model.predict_proba(X_test_t)[:, 1]
    final_metrics = metrics_for(y_test, final_prob)
    tn, fp, fn, tp = confusion_matrix(y_test, (final_prob >= 0.5).astype(int)).ravel()
    print("Test-set metrics:", final_metrics)
    metrics_ci = bootstrap_ci(y_test, final_prob)
    print("95% bootstrap intervals:", metrics_ci)
    # The app treats everything at or above its own LOW limit as "not low". The limit is fixed in advance
    # (it is NOT tuned on the test set); this shows what that choice means for recall.
    low_metrics = metrics_for(y_test, final_prob, threshold=LOW_LIMIT)
    ltn, lfp, lfn, ltp = confusion_matrix(y_test, (final_prob >= LOW_LIMIT).astype(int)).ravel()
    at_low_limit = {"threshold": LOW_LIMIT, "metrics": low_metrics,
                    "confusion": {"tn": int(ltn), "fp": int(lfp), "fn": int(lfn), "tp": int(ltp)}}
    print(f"At the app's LOW limit ({LOW_LIMIT}):", low_metrics)

    trust_validation = evaluate_trust_check(X, y, base_clf)
    print("Trust-check validation:", json.dumps(trust_validation["levels"]), "AUC", trust_validation["auc_score_vs_error"])

    external, external_skipped = evaluate_external(sorted(list(EXTERNAL_DIR.glob("*.csv")) + list(EXTERNAL_DIR.glob("*.data"))),
                                                   final_model, prep, X_train, X)

    # ---- 8. feature importance and explanation baseline
    perm = permutation_importance(final_model, X_test_t, y_test, scoring="roc_auc",
                                  n_repeats=20, random_state=SEED)
    raw_imp = np.clip(perm.importances_mean, 0, None)
    share = raw_imp / raw_imp.sum() * 100 if raw_imp.sum() > 0 else raw_imp
    importance = sorted(({"feature": f, "importance": round(float(s), 1)} for f, s in zip(FEATURES, share)),
                        key=lambda d: -d["importance"])
    baseline = {f: float(X_train[f].median()) for f in FEATURES}

    # ---- 9. charts for the web app
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    figures = []

    def save(fig, filename):
        fig.savefig(REPORT_DIR / filename, dpi=130, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        figures.append(filename)

    fig, ax = plt.subplots(figsize=(6, 5))
    for name, prob in test_probs.items():
        fpr, tpr, _ = roc_curve(y_test, prob)
        auc = results[name]["test"]["roc_auc"]
        ax.plot(fpr, tpr, lw=2 if name == best_name else 1, label=f"{name} ({auc})")
    ax.plot([0, 1], [0, 1], "k--", lw=1)
    ax.set(xlabel="False positive rate", ylabel="True positive rate", title="ROC curves (test set)")
    ax.legend(fontsize=7, loc="lower right")
    save(fig, "roc_curves.png")

    fig, ax = plt.subplots(figsize=(4.2, 3.8))
    cm = np.array([[tn, fp], [fn, tp]])
    ax.imshow(cm, cmap="Blues")
    for (i, j), v in np.ndenumerate(cm):
        ax.text(j, i, str(v), ha="center", va="center", fontsize=16, fontweight="bold",
                color="white" if v > cm.max() / 2 else "black")
    ax.set_xticks([0, 1], ["No disease", "Disease"])
    ax.set_yticks([0, 1], ["No disease", "Disease"])
    ax.set(xlabel="Predicted", ylabel="Actual", title=f"Confusion matrix - {best_name}")
    save(fig, "confusion_matrix.png")

    fig, ax = plt.subplots(figsize=(5, 4.5))
    frac, mean_pred = calibration_curve(y_test, final_prob, n_bins=5, strategy="quantile")
    ax.plot([0, 1], [0, 1], "k--", label="Perfectly calibrated")
    ax.plot(mean_pred, frac, "o-", color="#C62828", label="Selected model")
    ax.set(xlabel="Mean predicted probability", ylabel="Observed fraction with disease",
           title="Calibration curve (test set)")
    ax.legend()
    save(fig, "calibration_curve.png")

    fig, ax = plt.subplots(figsize=(6, 4.5))
    top = importance[::-1]
    ax.barh([d["feature"] for d in top], [d["importance"] for d in top], color="#1F3A5F")
    ax.set(xlabel="Share of total importance (%)", title="Permutation feature importance")
    save(fig, "feature_importance.png")

    names = list(results)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    xs = np.arange(len(names))
    ax.bar(xs - 0.2, [results[n]["cv_roc_auc"] for n in names], 0.4, label="CV ROC-AUC (train)", color="#7FA7D9")
    ax.bar(xs + 0.2, [results[n]["test"]["recall"] for n in names], 0.4, label="Test recall", color="#C62828")
    ax.set_xticks(xs, names, rotation=25, ha="right", fontsize=8)
    ax.set(ylim=(0, 1.05), title="Model comparison")
    ax.legend(fontsize=8)
    save(fig, "model_comparison.png")

    # ---- save everything
    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(final_model, MODEL_DIR / "heart_disease_model.pkl")
    joblib.dump(prep, MODEL_DIR / "scaler.pkl")      # imputer + scaler
    pd.DataFrame([{"model": n, "cv_roc_auc": round(r["cv_roc_auc"], 3), **r["test"]}
                  for n, r in results.items()]).to_csv(MODEL_DIR / "model_comparison.csv", index=False)
    info = {
        "best_model": best_name,
        "calibrated": bool(use_cal),
        "brier_cv": {"raw": round(float(raw_brier), 4), "calibrated": round(float(cal_brier), 4)},
        "features": FEATURES,
        "rows": int(len(X)),
        "class_counts": {"0": int((y == 0).sum()), "1": int((y == 1).sum())},
        "train_rows": int(len(X_train)), "test_rows": int(len(X_test)),
        "comparison": [{"model": n, "cv_roc_auc": round(r["cv_roc_auc"], 3), "params": r["best_params"],
                        **r["test"]} for n, r in sorted(results.items(), key=lambda kv: -kv[1]["cv_roc_auc"])],
        "metrics": final_metrics,
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "metrics_ci": metrics_ci,
        "at_low_limit": at_low_limit,
        "trust_validation": trust_validation,
        "drift_reference": drift.build_reference({f: X[f].tolist() for f in FEATURES}),
        "external_validation": external,
        "external_skipped": external_skipped,
        "feature_importance": importance,
        "baseline": baseline,
        "figures": figures,
        "demo_data": DEMO_MARKER.exists(),
        "quick_mode": bool(quick),
        "scikit_learn": sklearn.__version__,
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    (MODEL_DIR / "model_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print("\nSaved model files in", MODEL_DIR, "and charts in", REPORT_DIR)
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    _, sent = tracking.record(
        info, DATASET, MODEL_DIR / "heart_disease_model.pkl", MODEL_DIR / "experiments.jsonl", SEED,
        artifacts=[MODEL_DIR / "model_info.json", MODEL_DIR / "model_comparison.csv", *[REPORT_DIR / name for name in figures]],
        use_mlflow=use_mlflow or bool(tracking_uri), tracking_uri=tracking_uri)
    print("Run recorded in model/experiments.jsonl" + (" and in MLflow" if sent else ""))
    if not info["external_validation"]:
        print("NOTE: no external validation files found. Run  python scripts/fetch_uci_external.py  and train again.")
    if info["demo_data"]:
        print("NOTE: DEMO_DATA.txt exists, so the model was trained on synthetic demo data.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="smaller hyper-parameter search")
    parser.add_argument("--mlflow", action="store_true", help="also log the run to MLflow (pip install -r requirements-mlops.txt)")
    args = parser.parse_args()
    main(args.quick, args.mlflow)
