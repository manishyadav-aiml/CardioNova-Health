External validation datasets
============================
Put extra heart disease files here (.csv or raw UCI .data files with the same 13
attributes and coding as the Cleveland data), for example the other UCI databases:

    processed.hungarian.data
    processed.switzerland.data
    processed.va.data

train_model.py trains on dataset/heart.csv ONLY and then tests the final model on every
file in this folder (external validation). Missing values ('?') are filled with the
medians learned from the training data. These files are never used for training.

IMPORTANT: only independent hospitals belong here (Hungarian, Switzerland, VA Long Beach).
The Kaggle heart.csv copies and the Statlog file are Cleveland data again, so train_model.py removes copied rows
and skips such files. See docs/DATASETS.md.
