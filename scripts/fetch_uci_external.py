#!/usr/bin/env python3
"""
Downloads the three other UCI heart-disease databases (Hungarian, Switzerland, VA Long Beach) into
dataset/external/ so that train_model.py can test the final model on data it never saw.

    python scripts/fetch_uci_external.py
    python train_model.py

Needs internet access once. The files use the same 13 attributes and coding as the Cleveland file;
'?' marks missing values (filled with medians learned from the training data).
"""
import sys
import urllib.request
from pathlib import Path

BASE = "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/"
FILES = ["processed.hungarian.data", "processed.switzerland.data", "processed.va.data"]
TARGET = Path(__file__).resolve().parent.parent / "dataset" / "external"


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    failed = 0
    for name in FILES:
        try:
            request = urllib.request.Request(BASE + name, headers={"User-Agent": "cardionova-fetch/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:      # noqa: S310 (fixed https URL)
                data = response.read()
            (TARGET / name).write_bytes(data)
            lines = data.count(b"\n")
            print(f"saved {name}  ({len(data):,} bytes, {lines} lines)")
        except Exception as exc:                  # network problems are reported, never hidden
            failed += 1
            print(f"could not download {name}: {exc}")
    if failed:
        print("Some files are missing. Download them from the UCI repository page and place them in dataset/external/.")
        sys.exit(1)
    print("Done. Now run:  python train_model.py")


if __name__ == "__main__":
    main()
