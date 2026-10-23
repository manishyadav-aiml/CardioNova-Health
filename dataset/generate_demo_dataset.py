"""
Creates SYNTHETIC demo files so that the project runs out of the box:

    dataset/heart.csv                      (303 rows, main training file)
    dataset/external/demo_external.csv     (200 rows, slightly different population)
    dataset/DEMO_DATA.txt                  (marker: tells the app the data is synthetic)

Columns and coding are the same as the UCI Cleveland heart disease dataset, but the
values are random and only loosely follow medical patterns. Predictions made with a
model trained on these files are NOT meaningful.

To use real data: put the real heart.csv in dataset/, real external files in
dataset/external/, delete dataset/DEMO_DATA.txt and delete demo_external.csv,
then run:  python train_model.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent


def make(n, seed, age_shift=0, chol_shift=0, bias=-2.0):
    rng = np.random.default_rng(seed)
    age = rng.integers(29 + age_shift, 78 + age_shift // 2, n)
    sex = rng.choice([0, 1], n, p=[0.32, 0.68])
    cp = rng.choice([1, 2, 3, 4], n, p=[0.08, 0.17, 0.28, 0.47])
    trestbps = np.clip(rng.normal(131, 17, n), 94, 200).astype(int)
    chol = np.clip(rng.normal(246 + chol_shift, 52, n), 126, 564).astype(int)
    fbs = rng.choice([0, 1], n, p=[0.85, 0.15])
    restecg = rng.choice([0, 1, 2], n, p=[0.50, 0.49, 0.01])
    thalach = np.clip(rng.normal(150, 23, n) - (age - 54) * 0.6, 71, 202).astype(int)
    exang = rng.choice([0, 1], n, p=[0.67, 0.33])
    oldpeak = np.round(np.clip(rng.gamma(1.2, 0.9, n), 0, 6.2), 1)
    slope = rng.choice([1, 2, 3], n, p=[0.47, 0.46, 0.07])
    ca = rng.choice([0, 1, 2, 3], n, p=[0.58, 0.22, 0.13, 0.07])
    thal = rng.choice([3, 6, 7], n, p=[0.55, 0.06, 0.39])

    score = (
        0.04 * (age - 54) + 0.8 * sex + 0.9 * (cp == 4) - 0.6 * (cp < 4)
        + 0.012 * (trestbps - 131) + 0.003 * (chol - 246)
        - 0.03 * (thalach - 150) + 1.0 * exang + 0.6 * oldpeak
        + 0.9 * ca + 0.7 * (thal == 7) + 0.4 * (slope >= 2) + bias
    )
    prob = 1 / (1 + np.exp(-(score + rng.normal(0, 0.9, n))))
    target = (rng.random(n) < prob).astype(int)
    return pd.DataFrame({
        "age": age, "sex": sex, "cp": cp, "trestbps": trestbps, "chol": chol,
        "fbs": fbs, "restecg": restecg, "thalach": thalach, "exang": exang,
        "oldpeak": oldpeak, "slope": slope, "ca": ca, "thal": thal, "target": target,
    })


if __name__ == "__main__":
    (HERE / "external").mkdir(exist_ok=True)
    main = make(303, 42)
    ext = make(200, 7, age_shift=4, chol_shift=15, bias=-1.8)
    main.to_csv(HERE / "heart.csv", index=False)
    ext.to_csv(HERE / "external" / "demo_external.csv", index=False)
    (HERE / "DEMO_DATA.txt").write_text(
        "heart.csv and external/demo_external.csv are SYNTHETIC demo data.\n"
        "Replace them with the real datasets, delete this file and demo_external.csv,\n"
        "then run: python train_model.py\n", encoding="utf-8")
    print("Demo data written:", len(main), "main rows,", len(ext), "external rows")
