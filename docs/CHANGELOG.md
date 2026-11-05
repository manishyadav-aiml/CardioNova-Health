# Changelog

## v7 (November 2026)

### Clinical-style PDF report
- Completely redesigned `prediction/report.py`: letterhead with logo and report-number barcode, title band, patient/assessment block, risk card with a drawn **risk meter**, result-reliability line and a red low-reliability box, summary of findings, **parameter table with general guide ranges and colour-coded status**, diverging factor chart, next steps with an emergency-symptoms line, **clinician-review block**, method notes and disclaimer, confidentiality footer with "Page x of y", running header with patient and report number on later pages.
- Always two pages (checked on four sample reports including the worst case); long names, markup and missing data are handled (tests in `prediction/tests_v6.py`).
- Report numbers are keyed hashes (`CN-yymmdd-XXXXXXXX`), never the database id; the report states it is generated automatically and not clinician-reviewed.
- Sample PDFs and preview images in `docs/sample_reports/`.

## v6 (November 2026)

### Dataset safety (found by checking two extra datasets and a tutorial notebook)
- The Kaggle `heart.csv` copies are the Cleveland data again (1025 rows = 302 unique; 296 of 302 identical on all 13 inputs with agreeing labels), recoded (cp, restecg, slope, thal) with an **inverted target**; the Statlog file is 270 of 270 identical Cleveland records. Evidence and mapping: `docs/DATASETS.md`.
- `load_dataset` and the batch upload now refuse Kaggle-coded files; `evaluate_external` removes rows that are copies of the training data and lists skipped files on the model page; clearer errors for unreadable files.
- `scripts/convert_kaggle_heart.py` converts a Kaggle copy to the UCI coding and reports its overlap with Cleveland.
- `prediction/tests_v5.py` (12 tests, including a round trip of the conversion on the real records).

## v5 (November 2026)

### New features
- **Two-factor login (TOTP)** with recovery codes, replay protection, lockout and an optional requirement for doctors; own standard-library implementation checked against the RFC 6238 test vectors.
- **Input drift monitoring**: training reference stored in the model file, `drift_report` command (`--fail-on-drift` for cron/CI), staff page `/ops/drift/`, log warnings for out-of-range inputs (names only).
- **Experiment tracking**: `model/experiments.jsonl` with a data fingerprint for every run, shown on the model page; optional MLflow (`--mlflow`, `requirements-mlops.txt`).
- **Stronger external validation**: per site, pooled, trust levels on external data; impossible zeros (blood pressure, cholesterol, heart rate) treated as missing; `fetch_uci_external.py` ready.
- **Redis**: service in `docker-compose.yml`, `redis` in `requirements-prod.txt`, connection timeouts, `KEY_PREFIX`, health endpoint reports the store, explicit fail-open / fail-closed policy if the store is down.

### Tests and CI
- `prediction/tests_v4.py` (TOTP vectors, login flow, setup, lockout, replay, outage behaviour, drift core and app, tracking with a fake MLflow); CI runs the drift command.

## v4 (November 2026)

### Verified user interface
- `scripts/audit_ui.py`: static audit of every `{% url %}`, static file, button, form, link and JavaScript hook (fails CI on any dead control). Found and fixed an inline style on the login page that the CSP silently blocked.
- `tests_js/`: 18 Node tests for the charts, confirm dialogs (delete record / account), dark-mode switch and what-if simulator; checked by mutation (breaking the CSRF header or the cancel path makes them fail).
- Charts no longer use a CDN: `charts.js` draws the history line and the risk doughnut on a canvas (hover tooltip, dark mode, resize, accessible label). The CSP now allows scripts from this site only and the privacy page says so.

### Machine learning
- **The trust check is validated** by nested cross-validation (error rate Good / Fair / Low) and shown on the model page. Its scoring rule is now one shared function (`ml.signal_points`) used by the app and by the evaluation.
- A "Low trust" warning now appears next to the risk category on the result page and in the PDF, and the PDF reliability label is coloured by level.

### Delivery
- `python manage.py seed_demo` creates a demo patient (six invented records) and a demo doctor; refuses to run when DEBUG is off unless `--force`.
- Sample PDF reports in `docs/sample_reports/`, MIT `LICENSE`, CI runs the UI audit and the JavaScript tests.

## v3 (October 2026)

### Security and privacy
- **Doctor sharing is now opt-in** (`Profile.share_with_doctors` defaults to `False`, migration `0004`). Existing profiles keep their value; the migration docstring has a one-line command to make all existing patients private.
- **Password reset** limits now use the real visitor address (`security.client_ip`) instead of `REMOTE_ADDR`, which behind a reverse proxy was the proxy itself (one shared limit for every user).
- The **e-mail-link password reset** is rate limited per address (`password_reset_link`).
- **DEBUG defaults to off**; `manage.py` enables development mode only for a plain local checkout. Docker build uses a build-only key; the image runs as an unprivileged user.
- scikit-learn pinned to the version that wrote the committed model files (`==1.8.0`); the original model files could not even be loaded by a newer scikit-learn.

### Machine learning
- Retrained in full (not quick) mode; always-on calibration so the trust check keeps its fold models.
- Bootstrap 95% intervals for test metrics; metrics at the app's own LOW/MODERATE limit; model card on the model page.
- `scripts/fetch_uci_external.py` downloads the other UCI files for external validation.

### New features
- **Data-entry checks** (`ml.input_warnings`) feed the trust check.
- **Plain-language summary and doctor questions** (`ml.narrative`) on the result page and in the PDF; rule-based, runs on the server.
- PDF reference column now shows general guide values; factor note explains the median-replacement method.

### Housekeeping
- Branding unified to "CardioNova"; README rewritten with measured numbers; interview guide corrected.
- New tests in `prediction/tests_v3.py`; existing tests updated for opt-in sharing.
