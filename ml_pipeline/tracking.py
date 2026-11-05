"""
Experiment tracking for train_model.py.

1. Always: one JSON line per training run is appended to model/experiments.jsonl (what was trained, on which data,
   with which settings and results). No extra software needed; the model page shows the latest runs.
2. Optional: the same run is sent to MLflow when `python train_model.py --mlflow` is used (or MLFLOW_TRACKING_URI is
   set) and the `mlflow` package is installed (`pip install -r requirements-mlops.txt`, then `mlflow ui`).
"""
import hashlib
import json
import platform
from datetime import datetime
from pathlib import Path

EXPERIMENT_NAME = "cardionova-heart-risk"
LOG_LIMIT = 500                      # keep the file small: older lines are dropped


def sha256_of(path, length=16):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()[:length]


def flatten(data, prefix=""):
    """{'a': {'b': 1}} -> {'a.b': 1}; lists are joined into strings."""
    flat = {}
    for key, value in data.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(flatten(value, name + "."))
        elif isinstance(value, (list, tuple)):
            flat[name] = ", ".join(str(v) for v in value)
        else:
            flat[name] = value
    return flat


def summarise(info, dataset_path, model_path, seed):
    """The compact record of one run (everything needed to compare runs later)."""
    best = next((row for row in info["comparison"] if row["model"] == info["best_model"]), {})
    trust = info.get("trust_validation") or {}
    levels = trust.get("levels") or {}
    return {
        "trained_at": info["trained_at"],
        "best_model": info["best_model"],
        "quick_mode": info["quick_mode"],
        "seed": seed,
        "scikit_learn": info["scikit_learn"],
        "python": platform.python_version(),
        "rows": info["rows"], "train_rows": info["train_rows"], "test_rows": info["test_rows"],
        "dataset_sha256": sha256_of(dataset_path),
        "model_sha256": sha256_of(model_path),
        "params": best.get("params", {}),
        "cv_roc_auc": best.get("cv_roc_auc"),
        "metrics": info["metrics"],
        "recall_at_low_limit": (info.get("at_low_limit") or {}).get("metrics", {}).get("recall"),
        "trust_error_pct": {name: level.get("error_pct") for name, level in levels.items()},
        "external_sites": sorted(info.get("external_validation") or {}),
    }


def append_log(summary, path):
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    lines.append(json.dumps(summary, sort_keys=True))
    path.write_text("\n".join(lines[-LOG_LIMIT:]) + "\n", encoding="utf-8")


def latest_runs(path, limit=5):
    """Newest first. Bad lines are skipped; a missing file gives an empty list."""
    path = Path(path)
    if not path.exists():
        return []
    runs = []
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        try:
            runs.append(json.loads(line))
        except ValueError:
            continue
        if len(runs) >= limit:
            break
    return runs


def log_to_mlflow(summary, artifacts, tracking_uri=None):
    """Sends one run to MLflow. Returns True on success, False when MLflow is not installed."""
    try:
        import mlflow
    except ImportError:
        print("NOTE: mlflow is not installed (pip install -r requirements-mlops.txt); the run was only saved to experiments.jsonl.")
        return False
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(EXPERIMENT_NAME)
    params = {k: v for k, v in flatten({"params": summary["params"], "seed": summary["seed"],
                                        "quick_mode": summary["quick_mode"], "model": summary["best_model"],
                                        "dataset_sha256": summary["dataset_sha256"], "rows": summary["rows"]}).items()}
    metrics = {k: float(v) for k, v in flatten({"test": summary["metrics"], "trust_error_pct": summary["trust_error_pct"]}).items()
               if isinstance(v, (int, float)) and not isinstance(v, bool)}
    if summary.get("cv_roc_auc") is not None:
        metrics["cv_roc_auc"] = float(summary["cv_roc_auc"])
    if summary.get("recall_at_low_limit") is not None:
        metrics["test.recall_at_low_limit"] = float(summary["recall_at_low_limit"])
    with mlflow.start_run(run_name=f"{summary['best_model']} {summary['trained_at']}"):
        mlflow.log_params({k: str(v)[:480] for k, v in params.items()})
        mlflow.log_metrics(metrics)
        mlflow.set_tags({"scikit_learn": summary["scikit_learn"], "python": summary["python"], "model_sha256": summary["model_sha256"]})
        for artifact in artifacts:
            if Path(artifact).exists():
                mlflow.log_artifact(str(artifact))
    return True


def record(info, dataset_path, model_path, log_path, seed, artifacts=(), use_mlflow=False, tracking_uri=None):
    summary = summarise(info, dataset_path, model_path, seed)
    append_log(summary, log_path)
    sent = log_to_mlflow(summary, artifacts, tracking_uri) if use_mlflow else False
    return summary, sent
