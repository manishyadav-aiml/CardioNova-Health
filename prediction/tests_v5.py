"""
Tests for the dataset-safety guards found while checking the popular Kaggle copies of the heart-disease data:
different coding, inverted target, and records that are also in the Cleveland training file.
Run with:  python manage.py test
"""
import tempfile
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.test import SimpleTestCase

from ml_pipeline.data import (FEATURES, KAGGLE_TO_UCI, kaggle_to_uci, load_dataset, looks_kaggle_coded, overlap_mask)

from . import batch


def cleveland():
    return load_dataset(settings.BASE_DIR / "dataset" / "heart.csv", drop_missing=True)


def to_kaggle(frame, target):
    """The reverse of kaggle_to_uci: how the Kaggle copy writes the same records."""
    out = frame.copy()
    for column, mapping in KAGGLE_TO_UCI.items():
        out[column] = out[column].map({uci: kaggle for kaggle, uci in mapping.items()})
    out["target"] = 1 - target.to_numpy()
    return out


class KaggleCodingTests(SimpleTestCase):
    def test_uci_file_is_not_flagged(self):
        X, y = cleveland()
        self.assertFalse(looks_kaggle_coded(X.assign(target=y)))

    def test_kaggle_style_file_is_flagged(self):
        X, y = cleveland()
        self.assertTrue(looks_kaggle_coded(to_kaggle(X, y)))

    def test_a_few_typos_in_a_uci_file_are_not_mistaken_for_kaggle(self):
        X, y = cleveland()
        frame = X.assign(target=y).copy()
        frame.iloc[:2, frame.columns.get_loc("cp")] = 0
        self.assertFalse(looks_kaggle_coded(frame))

    def test_conversion_restores_the_original_records_and_labels(self):
        X, y = cleveland()
        back = kaggle_to_uci(to_kaggle(X, y))
        pd.testing.assert_frame_equal(back[FEATURES].astype(float), X.astype(float), check_dtype=False)
        self.assertTrue((back["target"].to_numpy() == y.to_numpy()).all())

    def test_kaggle_missing_markers_become_missing_values(self):
        X, y = cleveland()
        frame = to_kaggle(X.head(3), y.head(3))
        frame.loc[frame.index[0], "ca"] = 4
        frame.loc[frame.index[1], "thal"] = 0
        converted = kaggle_to_uci(frame)
        self.assertTrue(pd.isna(converted["ca"].iloc[0]))
        self.assertTrue(pd.isna(converted["thal"].iloc[1]))


class OverlapTests(SimpleTestCase):
    def test_identical_records_are_found_and_changed_ones_are_not(self):
        X, _ = cleveland()
        other = pd.concat([X.head(5), X.iloc[5:8].assign(age=lambda f: f.age + 1)], ignore_index=True)
        mask = overlap_mask(X, other)
        self.assertEqual(mask.tolist(), [True] * 5 + [False] * 3)

    def test_records_with_missing_values_are_not_counted_as_copies(self):
        X, _ = cleveland()
        other = X.head(3).copy()
        other.iloc[0, other.columns.get_loc("ca")] = float("nan")
        self.assertEqual(overlap_mask(X, other).tolist(), [False, True, True])


class FileGuardTests(SimpleTestCase):
    def write(self, frame, **kwargs):
        path = Path(tempfile.mkdtemp()) / "data.csv"
        frame.to_csv(path, index=False, **kwargs)
        return path

    def test_training_file_still_loads(self):
        X, y = cleveland()
        self.assertEqual(len(X), len(y))
        self.assertGreater(len(X), 250)

    def test_loader_refuses_a_kaggle_coded_file(self):
        X, y = cleveland()
        with self.assertRaises(ValueError) as caught:
            load_dataset(self.write(to_kaggle(X, y)), drop_missing=False)
        self.assertIn("convert_kaggle_heart.py", str(caught.exception))

    def test_loader_explains_text_targets(self):
        X, y = cleveland()
        frame = X.assign(target=["Presence" if v else "Absence" for v in y])
        with self.assertRaises(ValueError) as caught:
            load_dataset(self.write(frame), drop_missing=False)
        self.assertIn("no usable rows", str(caught.exception))

    def test_batch_upload_refuses_a_kaggle_coded_file(self):
        X, y = cleveland()
        data = to_kaggle(X, y).drop(columns=["target"]).to_csv(index=False).encode()
        with self.assertRaises(batch.BatchError) as caught:
            batch.parse(data)
        self.assertIn("Kaggle", str(caught.exception))

    def test_batch_upload_still_accepts_the_sample_file(self):
        self.assertFalse(batch.parse(batch.sample_csv().encode()).empty)
