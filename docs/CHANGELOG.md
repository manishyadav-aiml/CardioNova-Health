# Changelog

## v3 (October 2026)

### Security and privacy
- **Doctor sharing is now opt-in** (`Profile.share_with_doctors` defaults to `False`, migration `0004`). Existing profiles keep their value; the migration docstring has a one-line command to make all existing patients private.
- **Password reset** limits now use the real visitor address (`security.client_ip`) instead of `REMOTE_ADDR`, which behind a reverse proxy was the proxy itself (one shared limit for every user).
- The **e-mail-link password reset** is rate limited per address (`password_reset_link`).
- **DEBUG defaults to off**; `manage.py` enables development mode only for a plain local checkout. Docker build uses a build-only key; the image runs as an unprivileged user.
- scikit-learn pinned to the version that wrote the committed model files (`==1.8.0`).

### Machine learning
- Retrained in full (not quick) mode; always-on calibration so the trust check keeps its fold models.
- Bootstrap 95% intervals for test metrics; metrics at the app's own LOW/MODERATE limit; model card on the model page.
- `scripts/fetch_uci_external.py` downloads the other UCI files for external validation.

### New features
- **Data-entry checks** (`ml.input_warnings`) feed the trust check.
- **Plain-language summary and doctor questions** (`ml.narrative`) on the result page and in the PDF; rule-based, runs on the server.
- PDF reference column now shows general guide values; factor note explains the median-replacement method.

### Housekeeping
- Branding unified to "CardioNova"; README rewritten with measured numbers; interview guide corrected (no unsupported external-validation claim).
- New tests in `prediction/tests_v3.py`; existing tests updated for opt-in sharing.
