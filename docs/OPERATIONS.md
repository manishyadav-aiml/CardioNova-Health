# Operations guide

Everything below works from the command line; nothing needs a paid service.

## Two-factor login
- Users: **My account > Set up two-factor login**. Add the account in an authenticator app with "enter a setup key", type the 6-digit code, and save the 8 recovery codes (shown once).
- Doctors can be forced to use it: set `DJANGO_REQUIRE_2FA_DOCTORS=1`. A doctor without it is sent to the setup page.
- Login becomes two steps: password, then code (valid 5 minutes; 5 wrong codes lock the step for 15 minutes). A code cannot be used twice.
- Lost phone: use a recovery code (works once). Lost both: an administrator selects the profile in the admin site (Profiles) and runs the action "Switch off two-factor login". The secret and recovery codes are never shown in the admin site.
- Limits: the Django admin login and the API token are not covered by it (use a private admin address, keep tokens secret).

## Shared rate limits (Redis)
- Rate-limit counters live in the Django cache. With several workers or servers, set `REDIS_URL=redis://host:6379/0` so they share one counter. `docker compose up` already starts Redis and sets it.
- If Redis is unreachable the site logs an error and **allows** the request (default, keeps the site usable). Set `DJANGO_RATE_LIMIT_FAIL_CLOSED=1` to **block** logins and other limited actions instead.
- `GET /api/health/` shows `rate_limit_store` (`redis` or `local-memory`) and whether it answers.

## Input drift
```text
python manage.py drift_report --days 30            # table in the terminal
python manage.py drift_report --days 30 --json     # machine-readable
python manage.py drift_report --fail-on-drift      # exit code 1 when drift is found (cron, CI)
```
- Staff users also get a page at `/ops/drift/` (link on their profile page).
- Method: population stability index per input against the training data stored in `model/model_info.json`. Below 0.10 stable, 0.10 to 0.25 watch, 0.25 or more drift. Nothing is judged below 30 records; the expected noise of small samples is subtracted.
- Each saved prediction with an input outside the training range writes a warning to the `prediction.drift` log (input names only, never values or users).
- What to do when it says drift: look at which inputs moved, check whether a new group of users arrived, collect labelled data from them, retrain and compare (`model/experiments.jsonl`).

## Experiment tracking
- Every `python train_model.py` appends one line to `model/experiments.jsonl`: time, model, parameters, data fingerprint, metrics, trust-check results. The model page shows the latest runs.
- MLflow (optional): `pip install -r requirements-mlops.txt`, then `python train_model.py --mlflow` and `mlflow ui`. Set `MLFLOW_TRACKING_URI` to log to a server.

## External validation
```text
python scripts/fetch_uci_external.py     # downloads the Hungarian, Switzerland and VA files into dataset/external/
python train_model.py                     # trains on Cleveland only, then tests on each site and pooled
```
The model page then shows each site, the pooled result and the error rate per trust level on that data. Quote these numbers, even if they are lower than the Cleveland test set; a drop is what external validation is for. Zeros recorded for blood pressure, cholesterol or heart rate in those files are treated as missing.
