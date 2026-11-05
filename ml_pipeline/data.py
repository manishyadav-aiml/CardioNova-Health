"""Dataset loading helpers shared by train_model.py (UCI heart disease coding)."""
from pathlib import Path

import pandas as pd

FEATURES = ["age", "sex", "cp", "trestbps", "chol", "fbs", "restecg",
            "thalach", "exang", "oldpeak", "slope", "ca", "thal"]


# The popular Kaggle copies of the Cleveland data (heart.csv with 303 or 1025 rows) use a different coding AND an
# inverted target. Verified against the Cleveland file by matching records (see docs/DATASETS.md):
#   cp 0,1,2,3 -> UCI 4,2,3,1      restecg 0,1,2 -> UCI 2,0,1      slope 0,1,2 -> UCI 3,2,1      thal 1,2,3 -> UCI 6,3,7
#   ca 4 and thal 0 mean "missing"      target 1 = NO disease (UCI: 1 = disease)
KAGGLE_TO_UCI = {"cp": {0: 4, 1: 2, 2: 3, 3: 1}, "restecg": {0: 2, 1: 0, 2: 1},
                 "slope": {0: 3, 1: 2, 2: 1}, "thal": {1: 6, 2: 3, 3: 7}}


def looks_kaggle_coded(df, threshold=0.2):
    """
    True when many rows hold values that do not exist in the UCI coding (cp 0, slope 0, thal 0/1/2).
    Used to refuse such files instead of silently reading them with the wrong meaning. A few typos in an otherwise
    correct file stay below the threshold and are reported row by row instead.
    """
    if not {"cp", "slope", "thal"} <= set(df.columns) or len(df) == 0:
        return False
    cp, slope, thal = (pd.to_numeric(df[c], errors="coerce") for c in ("cp", "slope", "thal"))
    suspicious = (cp == 0) | (slope == 0) | thal.isin([0, 1, 2])
    return bool(suspicious.mean() >= threshold)


def kaggle_to_uci(df, target_column="target"):
    """Recodes a Kaggle-style frame to the UCI coding used by this project (and flips its target)."""
    out = df.copy()
    for column, mapping in KAGGLE_TO_UCI.items():
        out[column] = pd.to_numeric(out[column], errors="coerce").map(mapping)       # unknown codes (thal 0) become missing
    out.loc[pd.to_numeric(out["ca"], errors="coerce") == 4, "ca"] = float("nan")
    if target_column in out.columns:
        out[target_column] = 1 - pd.to_numeric(out[target_column], errors="coerce")
    return out


def overlap_mask(reference, other):
    """
    True for every row of `other` whose 13 inputs are identical to a row of `reference`.
    Data that is also in the training set is not external validation; counting it would inflate the results.
    """
    ref = reference[FEATURES].drop_duplicates().assign(_in_reference=1)
    merged = other[FEATURES].merge(ref, on=FEATURES, how="left")
    return pd.Series(merged["_in_reference"].notna().to_numpy(), index=other.index)


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
    df = df[FEATURES + ["target"]].apply(pd.to_numeric, errors="coerce")
    if looks_kaggle_coded(df):
        raise ValueError(f"{path.name} looks like the Kaggle version of the data (different coding and an inverted target). "
                         "Convert it first: python scripts/convert_kaggle_heart.py in.csv out.csv")
    # The Switzerland and VA files record "no measurement" as 0 (cholesterol 0 mg/dl is impossible), so these zeros are
    # missing values. The Cleveland training file has none, so training is unaffected.
    for name in ("trestbps", "chol", "thalach"):
        df.loc[df[name] == 0, name] = float("nan")
    df = df.drop_duplicates()
    df = df.dropna(subset=["target"])
    if drop_missing:
        df = df.dropna()
    if df.empty:
        raise ValueError(f"{path.name}: no usable rows. Expected the 13 lower-case UCI columns "
                         "(age, sex, cp, trestbps, chol, fbs, restecg, thalach, exang, oldpeak, slope, ca, thal) "
                         "and a numeric target (0-4 or 0/1), not text such as Presence/Absence.")
    df["target"] = (df["target"] > 0).astype(int)
    return df[FEATURES], df["target"]
