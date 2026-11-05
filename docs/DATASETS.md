# Datasets: what is independent and what is not

Checking the extra heart-disease files showed that **none of the popular copies is a second dataset**. Each is the Cleveland data again, some recoded and with the target inverted. This page records the evidence, because using them by mistake would give inflated or inverted results.

## Overview

| File | Rows | What it really is | Independent of the training data? |
|---|---:|---|---|
| `dataset/heart.csv` (UCI `processed.cleveland.data`) | 303 (297 complete) | The training data, original UCI coding | n/a |
| Hungarian, Switzerland, VA Long Beach (`scripts/fetch_uci_external.py`) | 294, 123, 200 | Other hospitals, same 13 attributes | **Yes**: use these for external validation |
| Kaggle `heart.csv` (1025 rows) | 1025 | Only **302 different records**: 723 duplicates of Cleveland | **No** |
| Kaggle `heart.csv` (303 rows, used by the "heart disease prediction with machine learning" notebook) | 303 | Cleveland, recoded, target inverted | **No** |
| Statlog "Heart_Disease_Prediction.csv" | 270 | **All 270 rows are identical Cleveland records** (13 inputs and label) | **No** |

## Evidence (from the files that were checked)
- Kaggle `heart.csv`: 1025 rows, 302 unique. After converting the coding, **296 of the 302 rows match a Cleveland record on all 13 inputs, and all 296 labels agree**; the other 6 rows hold missing-value markers (ca 4 or thal 0) that our training drops.
- Statlog: **270 of 270 rows** are exact Cleveland records.
- Matching was done with `ml_pipeline.data.overlap_mask` (exact match on the 13 inputs).

## The Kaggle copy uses a different coding
Mapping found by matching records one by one (every value pair is a one-to-one permutation, no exceptions):

| Field | Kaggle value | UCI value (used here) |
|---|---|---|
| cp (chest pain) | 0, 1, 2, 3 | 4, 2, 3, 1 |
| restecg | 0, 1, 2 | 2, 0, 1 |
| slope | 0, 1, 2 | 3, 2, 1 |
| thal | 1, 2, 3 (0 = missing) | 6, 3, 7 |
| ca | 0-3 (4 = missing) | 0-3 (missing) |
| **target** | **1 = no disease** | **1 = disease** |

sex, fbs, exang and all numeric fields are identical.

## What goes wrong if it is used by mistake
- **Inverted conclusions.** The target is flipped. In the real Cleveland data 56% of men (201 records) and 26% of women (96) have disease. A notebook trained on the 303-row Kaggle copy reports that "the frequency of female getting heart disease is higher", which is an artefact of the flipped label. Its scores (logistic regression 88.5% on 61 test rows, cross-validated accuracy 84.5%, recall 92%) describe the "no disease" class, so they cannot be compared with this project's numbers.
- **Leakage.** In the 1025-row file, 71% of the rows are duplicates, so a random train/test split puts copies of training records into the test set and inflates every metric.
- **Silent errors in the app.** A Kaggle-coded batch upload would be read with the wrong meaning and give wrong risks without any error.

## Guards built into this project
- `load_dataset` refuses a Kaggle-coded file (also if someone replaces `heart.csv` with it) and explains how to convert it; it also gives a clear error for text targets such as Presence/Absence.
- The batch CSV upload refuses Kaggle-coded files.
- `evaluate_external` removes every row that is identical to a Cleveland record before measuring anything, and **skips and lists** files that are mostly copies (see the model page).
- `python scripts/convert_kaggle_heart.py in.csv out.csv` converts a Kaggle copy to the UCI coding, drops duplicates and reports how much of it is Cleveland.
- Tests: `prediction/tests_v5.py`.

## What to say in an interview
"I looked for a second dataset and found that the popular Kaggle copies are the same 303 patients: one has 723 duplicate rows, one recodes the fields and flips the label, and the Statlog file is a strict subset. I built checks that refuse them and remove overlapping rows from external validation. The real independent data are the Hungarian, Switzerland and VA files from UCI, and I report those separately."
