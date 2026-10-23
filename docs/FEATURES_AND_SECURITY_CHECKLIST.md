# Checklist: 20 website features and 20 security points

Status: **Done** = implemented and covered by a test or by `scripts/security_check.py`.
**N/A** = the project does not use that technology (explained). **You** = needs an action from you on your own accounts.
Run `python manage.py test` to prove the "Done" items on your computer.

## A. 20 website features

| # | Feature | Where it is | Test / how to see it |
|---|---|---|---|
| 1 | Dark mode toggle | `theme-init.js` (no flash), `main.js`, `[data-theme="dark"]` in `style.css`; follows the system setting first | Click the moon/sun button in the header |
| 2 | Simple cookie banner | `base.html`, `main.js`; honest text: only essential cookies | Clear site data, reload |
| 3 | Site search | Header box and `/search/`; searches pages, FAQ and **your own** history only | `test_search_*` |
| 4 | Back to top button | `#back-to-top`, appears after 400 px | Scroll down |
| 5 | Mobile menu | Hamburger button below 900 px, Esc closes, `aria-expanded` | Narrow the window |
| 6 | Loading animations | Button spinner, page loader after 0.5 s, shimmer on the simulator, fade-in; double-submit blocked | Submit any form |
| 7 | Hover states | Cards, buttons, table rows, links, chips, FAQ, floating buttons | Move the mouse |
| 8 | Scroll progress bar | `#scroll-progress` at the top | Scroll |
| 9 | Copy button | API token, curl example, "Copy summary" on the result page | Profile / result page |
| 10 | Print stylesheet | `print.css`: no menus or buttons, black on white, link addresses shown; "Print" button | Ctrl+P on the result page |
| 11 | Sticky header | `.navbar { position: sticky }` | Scroll |
| 12 | Skip to content | First link in the page, visible on focus | Press Tab once |
| 13 | Password visibility toggle | Added by `main.js` to every password field | Login page |
| 14 | UTM tracking | `UTMMiddleware` keeps the first `utm_source/medium/campaign` (validated), saved at sign-up, visible in the admin | `test_utm_*`; open `/?utm_source=linkedin&utm_medium=social&utm_campaign=portfolio` then register |
| 15 | Form success state | Contact form success panel, flash messages, "Copied" state | `test_contact_form_success_state_and_storage` |
| 16 | Form error state | Red field + message + summary + focus on first error (server side and instant client side) | `test_contact_form_error_state` |
| 17 | Confirmation modals | `<dialog>`: logout, delete prediction, delete account, replace API token | Click Logout |
| 18 | Last updated date | Footer and privacy page (`SITE_LAST_UPDATED`) | Footer |
| 19 | Expandable FAQ | `/faq/` with `<details>` | `test_faq_is_expandable` |
| 20 | Floating contact button | Bottom right, opens `/contact/` (stored in the admin, rate limited, honeypot) | Any page |

## B. 20 security points

| # | Point | What was done | Proof |
|---|---|---|---|
| 1 | Secure API keys | The app needs **no third-party API keys**. Its own API token is shown once, only the SHA-256 hash is stored. Secrets are read from environment variables only | `security_check.py`, `Profile.new_api_token` |
| 2 | Hide all .env files | `.gitignore` (`.env`, `.env.*`, `*.pem`, `*.key`) and `.dockerignore`; only `.env.example` is tracked | `security_check.py` fails if missing |
| 3 | Never hardcode secrets | The built-in development key was removed: a random key is generated per run when `DEBUG=1`; production refuses to start without a strong `DJANGO_SECRET_KEY`. `docker-compose.yml` no longer contains passwords | `test_03_*`, `security_check.py` |
| 4 | Add authentication | Django auth, password validators, 12-hour sessions, `HttpOnly` + `SameSite` cookies, CSRF on all forms, hashed API tokens | `test_04_*` |
| 5 | Verify permissions server-side | Every view checks the role/ownership on the server (`_can_view`, `doctor_required`); a user cannot make themselves a doctor | `test_05_*` |
| 6 | Don't trust frontend user IDs | No view reads a user id from the browser. The simulator gets only the changed values; the record comes from the URL and is permission-checked. Delete uses `pk=…, user=request.user` | `test_whatif_ignores_user_ids_and_uses_stored_values` |
| 7 | Isolate user data | Every query is filtered by the logged-in user; search, history and batch only touch own rows; doctors see only users who opted in, and every doctor view is logged for the patient | `test_05_06_07_*` |
| 8 | Lock down your database | Docker: the database port is **not published**; unique password from `.env`; `ATOMIC_REQUESTS`; optional `DJANGO_DB_SSLMODE=require`; ORM only (no raw SQL). **You:** use a least-privilege DB user on your host | `docker-compose.yml`, `settings.py` |
| 9 | Secure Firebase, Supabase, storage | **N/A**: none of them is used. Uploaded CSV files are processed in memory and never stored; no `MEDIA_ROOT` is served | `FILE_UPLOAD_*`, `forms.py` |
| 10 | Protect admin routes | Staff login required; admin path can be moved (`DJANGO_ADMIN_URL`) and limited to IPs (`DJANGO_ADMIN_ALLOWED_IPS`, answers 404 to others); admin login attempts are throttled | `test_10_*` |
| 11 | Disable production debug | `DEBUG=0` in Docker/Render files; the app refuses to start in production without a real secret key; `check --deploy` runs in CI | `ci.yml` |
| 12 | Hide detailed errors | Own 400/403/404/429/500 pages and JSON errors for the API; login says only "incorrect"; nothing technical is shown | `test_12_*` |
| 13 | Validate inputs server-side | Django forms with ranges for all 13 values, contact form, search length, `validate_changes()` for the simulator, API JSON checks, batch file validation | all form tests |
| 14 | Sanitize user content | Tags/control characters removed when saving (`sanitize.py`) **and** escaped on output; CSV formula injection neutralised; PDF text escaped (this closed a ReportLab `<img src="file://…">` hole) | `test_14_*` |
| 15 | Secure file uploads | `.csv` only, content type allow-list, 1 MB, UTF-8 text only, NUL bytes rejected, max 500 rows / 40 columns, requests over 2 MB refused before parsing, never saved to disk | `test_15_*` |
| 16 | Prevent SQL / NoSQL injection | Django ORM everywhere; the audit script fails on `.raw(`, `.extra(`, `cursor.execute(`. No NoSQL database is used | `test_16_*`, `security_check.py` |
| 17 | Rate-limit login and signup | 5 wrong passwords per user+IP and 50 per IP in 15 min; 10 sign-ups/hour; contact, API, simulator, admin login and account deletion are limited too; forged `X-Forwarded-For` does not help | `test_17_*` |
| 18 | Check Git history for secrets | `scripts/security_check.py` scans the working tree **and** the whole git history; CI runs it plus `gitleaks` with `fetch-depth: 0`. **You:** run it inside your real clone and rotate anything found | `ci.yml`, `test_18_*` |
| 19 | Security headers; restrict CORS | CSP (scripts only from this site + jsDelivr, no inline code), `X-Frame-Options: DENY`, nosniff, `Referrer-Policy`, `Permissions-Policy`, COOP/CORP, HSTS/secure cookies in production, `no-store` for logged-in pages. **No CORS headers are sent at all**, so other websites cannot read responses | `test_19_*` |
| 20 | Test as an untrusted user | `tests_v2.py` acts as visitor, other user, patient-vs-doctor, bot and attacker (IDOR, CSRF, brute force, XSS, upload abuse, forged headers) | `python manage.py test` |

## C. Things only you can do
1. Replace the **synthetic demo dataset** with the real UCI Cleveland data and retrain (see README). Until then every metric is meaningless.
2. Run `python manage.py test` and `python manage.py check --deploy` on your machine and fix anything reported.
3. Run `python scripts/security_check.py` inside your git clone (it then scans the history too).
4. In production set: `DJANGO_SECRET_KEY`, `DJANGO_ADMIN_URL`, `DJANGO_TRUSTED_PROXIES` (number of proxies in front of the app), a strong admin password, and `REDIS_URL` if you run several workers.
