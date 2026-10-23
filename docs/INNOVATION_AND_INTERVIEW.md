# What is different about this project (interview guide)

## The one-sentence pitch
"Most heart-disease projects print one probability. Mine also tells you **how far that probability can be trusted** and lets you **ask the model what-if questions**, inside a privacy-aware web application with a security audit behind it."

## Innovation 1: Trust check (reliability of each prediction)
`ml.reliability()` combines three signals for every single prediction:
1. **Out-of-range inputs**: values outside the 1st to 99th percentile of the training data.
2. **Model disagreement**: the cross-validation versions of the model give a spread of probabilities; a wide spread means the estimate is unstable.
3. **Borderline result**: the probability is close to a LOW/MODERATE/HIGH limit.
Result: Good / Fair / Low plus plain-language reasons and a probability range. In the PDF too. If trust is Low the page tells the user to see a doctor.
*Why it matters:* medical models that always sound confident are dangerous; this is "selective prediction / uncertainty awareness" in a student-sized form.

## Innovation 2: What-if simulator + target scenarios
Sliders for blood pressure, cholesterol and blood sugar call a server endpoint that re-scores the stored record (only the changed values travel from the browser). A table shows the estimate if values were at commonly cited targets.
*Honesty line to say out loud:* "This shows how the **model** reacts, a statistical association, not a causal guarantee."

## Supporting strengths
- Leak-safe pipeline, GridSearchCV, 6 models + ensembles, calibration, Brier score, permutation importance, **external validation** on other UCI sites.
- Roles (patient/doctor), opt-in sharing, **access log the patient can read**, delete account.
- Token API with hashed tokens, batch CSV with strict validation.
- 20 UI features and a 20-point security checklist, all with tests (`docs/FEATURES_AND_SECURITY_CHECKLIST.md`).

## Questions you will be asked
**Why Cleveland, 297 rows?** Standard benchmark, but small, so I report cross-validated mean ± std and validate externally; I do not claim clinical use.
**Why recall?** A missed sick patient costs more than a false alarm.
**Why calibrate?** So that "70%" behaves like 70%; needed for the risk bands and the trust range.
**How do you know the Trust check works?** Unusual inputs lower it (tested); a next step is to measure error rate by trust level on held-out data (selective-risk curve).
**What did you find in your own security review?** The PDF report accepted markup from user text, doctors' views of patient data were not logged, the dev secret key was hard-coded, and `docker-compose.yml` contained passwords; all fixed.
**What would you do next?** Real clinical dataset with more rows, fairness by sex/age, 2-factor login, MLflow tracking, model monitoring.

## Before you present
Replace the demo dataset with real Cleveland data and retrain; copy the **new** numbers from `model/model_info.json` into your slides. Never quote the demo-data numbers.
