# What is different about this project (interview guide)

## The one-sentence pitch
"Most heart-disease projects print one probability. Mine also tells you **how far that probability can be trusted**, **why** the model produced it, and **what to ask a doctor**, inside a privacy-aware web application with a security audit and CI behind it."

## Innovation 1: Trust check (reliability of each prediction)
`ml.reliability()` combines four signals for every single prediction:
1. **Out-of-range inputs**: values outside the 1st to 99th percentile of the training data.
2. **Model disagreement**: the cross-validation fold models inside the calibrated classifier give a spread of probabilities; a wide spread means the estimate is unstable.
3. **Borderline result**: the probability is close to a LOW/MODERATE/HIGH limit.
4. **Data-entry check** (`ml.input_warnings`): implausible combinations such as a maximum heart rate far below `220 - age` (a resting pulse typed in the wrong box), systolic pressure under 90, or cholesterol under 125 (wrong unit).
Result: Good / Fair / Low plus plain-language reasons and a probability range, on the page, in the PDF and in the API.
*Why it matters:* medical models that always sound confident are dangerous; this is "selective prediction / uncertainty awareness" in a student-sized form.
**Validated, not just claimed.** `train_model.py` runs nested 10-fold cross-validation on all 297 records (each record scored by a model that never saw it, trust computed with the app's own `ml.signal_points` rule). Result: predictions marked **Good were wrong 3.0%** of the time (2/66), **Fair 16.9%** (32/189), **Low 38.1%** (16/42); the Good and Low 95% intervals (0.8-10.4% and 25.0-53.2%) do not overlap. Answering only for Good or Fair would cover 85.9% of cases at 86.7% accuracy (all cases 83.2%). The trust score predicts mistakes with ROC-AUC 0.701: useful, not perfect. Say that last part yourself.

## Innovation 2: What-if simulator + target scenarios
Sliders for blood pressure, cholesterol and blood sugar call a server endpoint that re-scores the stored record (only the changed values travel from the browser).
*Honesty line to say out loud:* "This shows how the **model** reacts, a statistical association, not a causal guarantee."

## Innovation 3: Plain-language summary and doctor questions
`ml.narrative()` writes a short explanation and a list of questions for a doctor from the model's own outputs (top factors, trust level, risk band). It is **rule-based natural-language generation, not a language model**: it runs on the server, nothing is sent to a third party, and every sentence is unit-tested to avoid diagnosis wording.
*Why I did not add an LLM chatbot:* health data would have to leave the application, which contradicts the privacy page, the CSP (`connect-src 'self'`) and the opt-in sharing design. A clean extension would be an optional, off-by-default module with explicit consent.

## Operations features (what makes it production-minded)
- **Two-factor login** with standard TOTP written with the standard library (no new dependency) and verified against the RFC 6238 test vectors; recovery codes, replay protection, lockout, optional requirement for doctors.
- **Drift monitor**: PSI per input against a training reference stored with the model; small-sample noise removed; resampling the training data gave 0 false alarms in 100 tries, shifted ages or cholesterol and unseen categories are caught. Command line (cron/CI) and a staff page.
- **Experiment tracking**: every run logged with a data fingerprint; optional MLflow.
- **Redis-ready rate limits** with an explicit fail-open or fail-closed policy for outages.
- **Stronger external check** built in: Hungarian, Switzerland and VA files tested site by site and pooled, including the trust check on that data (run it and quote the result).
*Be ready to say:* "I wrote TOTP myself to avoid a dependency, and I checked it against the RFC's published vectors; in production I would use a vetted library and encrypt the secret at rest."

## Supporting strengths
- Leak-safe pipeline (split first, imputer/scaler inside the pipeline), GridSearchCV, 6 models + 2 ensembles, selection on training CV only, calibration, Brier score, permutation importance, **bootstrap confidence intervals** on the small test set.
- Roles (patient/doctor), **opt-in** sharing (off by default), an **access log the patient can read**, delete account.
- Token API with hashed tokens, batch CSV with strict validation.
- 20 UI features and a 20-point security checklist, all with tests (`docs/FEATURES_AND_SECURITY_CHECKLIST.md`).
- **Every button is checked**: `scripts/audit_ui.py` fails the build on a dead button, dead link, missing CSRF token, unknown URL name or missing script hook; Node tests exercise the confirm dialogs, dark-mode switch, what-if simulator and charts (18 JavaScript tests, mutation-checked).
- **No third-party requests**: charts are drawn on a canvas (no CDN), the CSP allows this site only, and the privacy page says so truthfully.
- `python manage.py seed_demo` gives a demo patient and doctor in one command, so a live demo never starts empty.
- CI: quick training, migration check, tests, `check --deploy`, repository scan, gitleaks.

## Numbers to quote (from `model/model_info.json`, scikit-learn 1.8.0)
- Selected model: **Gradient Boosting**, chosen on cross-validated ROC-AUC of the training data only.
- Test set (60 records), 50% cut-off: accuracy 0.817, recall 0.714 (95% CI 0.536-0.885), ROC-AUC 0.925 (95% CI 0.851-0.982), Brier 0.121.
- At the app's own LOW limit (0.3, fixed in advance): recall 0.929, precision 0.765 (2 missed of 28).
- Say the interval before anyone asks: with 60 test records, one more or fewer correct case moves recall by several points.

## Questions you will be asked
**Why not use the Kaggle `heart.csv` (1025 rows) as a second dataset?** I checked it: it has only 302 unique records and all of them are Cleveland patients, recoded, with the target inverted. The Statlog file is a strict subset (270 of 270 identical). So I built guards that refuse them and remove overlapping rows, and I use the independent Hungarian, Switzerland and VA files instead (docs/DATASETS.md).
**Why Cleveland, 297 rows?** Standard benchmark, but small, so I report cross-validated scores and bootstrap intervals and I do not claim clinical use. External validation on the other UCI sites is built in (`scripts/fetch_uci_external.py`, then `python train_model.py`); I have not reported those results yet.
**Why recall?** A missed sick patient costs more than a false alarm. So the app's alarm line is its own LOW limit (0.3), not 50%; at that limit recall is 0.929 at the price of more false alarms. The limit was fixed before looking at the test set.
**Why calibrate?** So that "70%" behaves like 70%; needed for the risk bands. The calibration folds also give the fold models used by the trust check.
**Why was Gradient Boosting chosen if SVM or k-NN have a higher test ROC-AUC?** The rule is fixed: best cross-validated ROC-AUC on training data only. On 60 test records those differences are within noise; picking by test score would be test-set leakage.
**How do you know the trust check works?** I measured it: nested cross-validation on all 297 records. Error rate rises from 3.0% (Good) to 16.9% (Fair) to 38.1% (Low); the model page shows the table. Limits: small groups, one dataset, the data-entry warnings rarely trigger on clean benchmark data.
**What would a senior engineer criticise first?** Pickled model files (only load files you trained), the TOTP secret stored unencrypted, hand-written TOTP instead of a vetted library, external validation not yet run, one small dataset. Name them before they do.
**What did you find in your own security review?** The PDF report accepted markup from user text, doctors' views of patient data were not logged, the dev secret key was hard-coded, `docker-compose.yml` contained passwords, doctor sharing was on by default, password-reset limits used the proxy's address instead of the visitor's, and debug defaulted to on; all fixed.
**What would you do next?** Run the external validation, fairness by sex/age, passkeys, encrypted secrets, alerting from the drift command, a real clinical dataset with more rows.

## Before you present
Copy the numbers from `model/model_info.json` into your slides after every retrain. Never quote numbers from a `--quick` run (the page says "quick mode").
