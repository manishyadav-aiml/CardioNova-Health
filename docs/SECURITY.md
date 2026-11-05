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
- Charts are drawn by `static/prediction/js/charts.js` with the browser's canvas, so the CSP allows scripts from this site only (no third-party hosts).
- The ML model is a pickle/joblib file. Only load model files you trained yourself.
- No email verification and no two-factor login. Both would be good next steps.
- Passwords are protected by Django's PBKDF2 hashing; the app never sees or logs them.


## Changes in v3
- Doctor sharing is opt-in and off by default; doctors see only patients who switched it on, and every doctor view is logged for the patient.
- Rate limits for password reset use `security.client_ip()` (honours `DJANGO_TRUSTED_PROXIES`); the e-mail-link reset is limited too.
- `DJANGO_DEBUG` defaults to `0`. The container runs as a non-root user.
- Charts no longer use a CDN: `charts.js` draws them on a canvas, so no third-party script is loaded and the CSP has no external host. `scripts/audit_ui.py` fails the build if an external script is added.

## Changes in v5
- **Two-factor login (TOTP)**: password first, then an authenticator code; the user is not logged in between the two steps. Codes are checked in constant time, a used code is refused (atomic step counter), wrong codes are rate limited per address and per user, recovery codes are stored only as keyed hashes (peppered with the secret key). Doctors can be required to use it (`DJANGO_REQUIRE_2FA_DOCTORS=1`).
  Known limits: the authenticator secret is stored unencrypted (it must be readable to check codes), so protect the database; the admin site and API tokens are outside this flow.
- **Rate-limit store outage**: if Redis fails, `security.py` logs an error and allows the request by default (`DJANGO_RATE_LIMIT_FAIL_CLOSED=1` blocks instead). Redis connections time out after 2 seconds.
- **Drift logging** never records input values or user identities, only the names of inputs outside the training range.
