"""Dataset loading helpers shared by train_model.py (UCI heart disease coding)."""
from pathlib import Path

import pandas as pd

FEATURES = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
            "thalach", "exang", "oldpeak", "slope", "ca", "thal"]


def load_dataset(path, drop_missing):
    """
    Reads a heart disease CSV / UCI .data file and returns (X, y).

    * Works with a header row (age,...,target / num / condition) or the raw UCI
      processed files that have no header and use '?' for missing values.
    * The target is converted to binary: 0 = no disease, 1 = disease (UCI 1-4).
    * drop_missing=True removes rows with missing values (used for the main
      Cleveland training file). drop_missing=False keeps them so that the model's
      imputer can fill them (used for external validation files).
    """
    path = Path(path)
    df = pd.read_csv(path, na_values=["?"])
    if "age" not in df.columns:
        df = pd.read_csv(path, header=None, names=FEATURES + ["target"], na_values=["?"])
    for name in ("target", "condition", "num"):
        if name in df.columns:
            df = df.rename(columns={name: "target"})
            break
    missing = [c for c in FEATURES + ["target"] if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name} is missing the columns: {missing}")
    df = df[FEATURES + ["target"]].apply(pd.to_numeric, errors="coerce").drop_duplicates()
    df = df.dropna(subset=["target"])
    if drop_missing:
        df = df.dropna()
    df["target"] = (df["target"] > 0).astype(int)
    return df[FEATURES], df["target"]
