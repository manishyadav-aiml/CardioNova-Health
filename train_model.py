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

from ml_pipeline.data import FEATURES, load_dataset  # noqa: E402
from prediction.ml import LOW_LIMIT  # noqa: E402  (the app's LOW/MODERATE limit; no Django needed)

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


def main(quick):
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
    base_clf = best_pipe.named_steps["clf"]

    # Keep preprocessing inside each calibration CV fold to prevent leakage.
    calibration_pipe = Pipeline([
        ("prep", preprocessor()),
        ("clf", clone(base_clf)),
    ])
    raw_brier = -cross_val_score(
        clone(calibration_pipe), X_train, y_train,
        cv=cv, scoring="neg_brier_score"
    ).mean()
    calibrated = CalibratedClassifierCV(
        clone(calibration_pipe), method="sigmoid", cv=5
    )
    cal_brier = -cross_val_score(
        calibrated, X_train, y_train,
        cv=cv, scoring="neg_brier_score"
    ).mean()

    # Select calibration only when it improves the cross-validation Brier score.
    use_cal = cal_brier < raw_brier
    if use_cal:
        final_model = CalibratedClassifierCV(
            clone(calibration_pipe), method="sigmoid", cv=5
        ).fit(X_train, y_train)
    else:
        final_model = clone(calibration_pipe).fit(X_train, y_train)
    print(f"CV Brier score: raw {raw_brier:.4f}  calibrated {cal_brier:.4f}  -> "
          f"{'calibrated' if use_cal else 'raw'} model used")

    # ---- 7. final evaluation
    final_prob = final_model.predict_proba(X_test)[:, 1]
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

    external = {}
    for path in sorted(list(EXTERNAL_DIR.glob("*.csv")) + list(EXTERNAL_DIR.glob("*.data"))):
        try:
            Xe, ye = load_dataset(path, drop_missing=False)
        except ValueError as exc:
            print("Skipping", path.name, "-", exc)
            continue
        prob = final_model.predict_proba(Xe)[:, 1]
        m = metrics_for(ye, prob)
        m["rows"] = int(len(Xe))
        m["positive_rate"] = round(float(ye.mean()), 3)
        m["missing_share"] = round(float(Xe.isna().mean().mean()), 3)
        external[path.name] = m
        print(f"External {path.name}: {m}")

    # ---- 8. feature importance and explanation baseline
    perm = permutation_importance(final_model, X_test, y_test, scoring="roc_auc",
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
        "external_validation": external,
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
    if not info["external_validation"]:
        print("NOTE: no external validation files found. Run  python scripts/fetch_uci_external.py  and train again.")
    if info["demo_data"]:
        print("NOTE: DEMO_DATA.txt exists, so the model was trained on synthetic demo data.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="smaller hyper-parameter search")
    main(parser.parse_args().quick)
