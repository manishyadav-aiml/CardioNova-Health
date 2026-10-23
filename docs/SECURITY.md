# Security notes

## Threat model in one paragraph
The app stores health values, so the main risks are: someone reading another person's data (IDOR), account take-over by guessing passwords, malicious text or files turning into scripts or spreadsheet formulas, and leaked secrets. Each is handled below.

## Where things live
| Topic | File |
|---|---|
| Rate limits, headers, request guard, UTM | `prediction/security.py`, limits in `settings.RATE_LIMITS` |
| Text clean-up | `prediction/sanitize.py` |
| Upload rules | `prediction/forms.py` (`BatchUploadForm`), `prediction/batch.py` |
| Permissions | `prediction/views.py` (`_can_view`, `doctor_required`, `_log_access`) |
| Error pages | `error.html`, `500.html`, handlers in `heart_disease/urls.py` |
| Repository audit | `scripts/security_check.py` |

## Settings that matter in production
| Variable | Meaning |
|---|---|
| `DJANGO_SECRET_KEY` | required, 32+ random characters (`python -c "import secrets; print(secrets.token_urlsafe(50))"`) |
| `DJANGO_ADMIN_URL` | private admin path, for example `staff-7f3k/` |
| `DJANGO_ADMIN_ALLOWED_IPS` | optional comma separated list |
| `DJANGO_TRUSTED_PROXIES` | how many proxies sit in front of the app. Wrong value = wrong IP for rate limits. Check by logging in wrongly 5 times: only you should be locked, not everybody |
| `REDIS_URL` | shared counters. Without it the limits are per worker process (two workers = double the allowance) |
| `DJANGO_DB_SSLMODE` | `require` when PostgreSQL is reached over the internet |

## Known limits (be honest about them in an interview)
- Rate limiting is cache based; without Redis it is per process.
- The CSP allows Chart.js from `cdn.jsdelivr.net`. To remove that dependency, copy Chart.js into `static/` and delete the host from `CSP` in `security.py`.
- The ML model is a pickle/joblib file. Only load model files you trained yourself.
- No email verification and no two-factor login. Both would be good next steps.
- Passwords are protected by Django's PBKDF2 hashing; the app never sees or logs them.
