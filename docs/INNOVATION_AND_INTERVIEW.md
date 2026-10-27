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

## Innovation 2: What-if simulator + target scenarios
Sliders for blood pressure, cholesterol and blood sugar call a server endpoint that re-scores the stored record (only the changed values travel from the browser).
*Honesty line to say out loud:* "This shows how the **model** reacts, a statistical association, not a causal guarantee."

## Innovation 3: Plain-language summary and doctor questions
`ml.narrative()` writes a short explanation and a list of questions for a doctor from the model's own outputs (top factors, trust level, risk band). It is **rule-based natural-language generation, not a language model**: it runs on the server, nothing is sent to a third party, and every sentence is unit-tested to avoid diagnosis wording.
*Why I did not add an LLM chatbot:* health data would have to leave the application, which contradicts the privacy page, the CSP (`connect-src 'self'`) and the opt-in sharing design. A clean extension would be an optional, off-by-default module with explicit consent.

## Supporting strengths
- Leak-safe pipeline (split first, imputer/scaler inside the pipeline), GridSearchCV, 6 models + 2 ensembles, selection on training CV only, calibration, Brier score, permutation importance, **bootstrap confidence intervals** on the small test set.
- Roles (patient/doctor), **opt-in** sharing (off by default), an **access log the patient can read**, delete account.
- Token API with hashed tokens, batch CSV with strict validation.
- 20 UI features and a 20-point security checklist, all with tests (`docs/FEATURES_AND_SECURITY_CHECKLIST.md`).
- CI: quick training, migration check, tests, `check --deploy`, repository scan, gitleaks.

## Numbers to quote (from `model/model_info.json`, scikit-learn 1.8.0)
- Selected model: **Gradient Boosting**, chosen on cross-validated ROC-AUC of the training data only.
- Test set (60 records), 50% cut-off: accuracy 0.817, recall 0.714 (95% CI 0.536-0.885), ROC-AUC 0.925 (95% CI 0.851-0.982), Brier 0.121.
- At the app's own LOW limit (0.3, fixed in advance): recall 0.929, precision 0.765 (2 missed of 28).
- Say the interval before anyone asks: with 60 test records, one more or fewer correct case moves recall by several points.

## Questions you will be asked
**Why Cleveland, 297 rows?** Standard benchmark, but small, so I report cross-validated scores and bootstrap intervals and I do not claim clinical use. External validation on the other UCI sites is built in (`scripts/fetch_uci_external.py`, then `python train_model.py`); I have not reported those results yet.
**Why recall?** A missed sick patient costs more than a false alarm. So the app's alarm line is its own LOW limit (0.3), not 50%; at that limit recall is 0.929 at the price of more false alarms. The limit was fixed before looking at the test set.
**Why calibrate?** So that "70%" behaves like 70%; needed for the risk bands. The calibration folds also give the fold models used by the trust check.
**Why was Gradient Boosting chosen if SVM or k-NN have a higher test ROC-AUC?** The rule is fixed: best cross-validated ROC-AUC on training data only. On 60 test records those differences are within noise; picking by test score would be test-set leakage.
**How do you know the trust check works?** Unusual inputs lower it (tested); a next step is to measure error rate by trust level on held-out data (selective-risk curve).
**What did you find in your own security review?** The PDF report accepted markup from user text, doctors' views of patient data were not logged, the dev secret key was hard-coded, `docker-compose.yml` contained passwords, doctor sharing was on by default, password-reset limits used the proxy's address instead of the visitor's, and debug defaulted to on; all fixed.
**What would you do next?** Real clinical dataset with more rows, fairness by sex/age, 2-factor login, MLflow tracking, drift monitoring.

## Before you present
Copy the numbers from `model/model_info.json` into your slides after every retrain. Never quote numbers from a `--quick` run (the page says "quick mode").
