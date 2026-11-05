#!/usr/bin/env python3
"""
Converts the popular Kaggle copy of the Cleveland heart-disease data (heart.csv) to the UCI coding used here.

    python scripts/convert_kaggle_heart.py heart.csv heart_uci.csv

What it changes (verified by matching records against the Cleveland file, see docs/DATASETS.md):
    cp 0,1,2,3 -> 4,2,3,1    restecg 0,1,2 -> 2,0,1    slope 0,1,2 -> 3,2,1    thal 1,2,3 -> 6,3,7    ca 4 / thal 0 -> missing
    target is INVERTED in that copy (1 = no disease), so it is flipped.
Duplicates are removed (the 1025-row version has only 302 different rows).
It then reports how many rows are identical to the Cleveland training records: such rows are NOT external data.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from ml_pipeline.data import FEATURES, kaggle_to_uci, load_dataset, looks_kaggle_coded, overlap_mask  # noqa: E402


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    source, target = Path(sys.argv[1]), Path(sys.argv[2])
    frame = pd.read_csv(source)
    if not looks_kaggle_coded(frame):
        sys.exit(f"{source.name} does not look Kaggle-coded (no cp 0, slope 0 or thal 0-2). Nothing converted.")
    unique = frame.drop_duplicates()
    converted = kaggle_to_uci(unique)
    converted.to_csv(target, index=False)
    print(f"{len(frame)} rows read, {len(frame) - len(unique)} duplicates removed, {len(converted)} rows written to {target}")
    print(f"missing values after conversion (ca 4 / thal 0): {int(converted[FEATURES].isna().any(axis=1).sum())} rows")

    cleveland, _ = load_dataset(ROOT / "dataset" / "heart.csv", drop_missing=True)
    same = overlap_mask(cleveland, converted[FEATURES]).sum()
    print(f"{same} of {len(converted)} rows are identical to Cleveland training records ({same / len(converted):.0%}).")
    if same / len(converted) > 0.5:
        print("WARNING: this is the Cleveland data again, not an independent dataset. Do not use it for external validation.")


if __name__ == "__main__":
    main()
