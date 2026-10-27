import hashlib
import hmac
import logging
import secrets
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import SetPasswordForm
from django.core.cache import cache
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from . import security


logger = logging.getLogger(__name__)

User = get_user_model()

SESSION_KEY = "cardionova_password_reset"

OTP_EXPIRY = getattr(
    settings,
    "PASSWORD_RESET_OTP_EXPIRY_SECONDS",
    600,
)

MAX_OTP_ATTEMPTS = getattr(
    settings,
    "PASSWORD_RESET_OTP_MAX_ATTEMPTS",
    5,
)


def _otp_digest(user_id, otp):
    """Create a keyed digest without storing the plain OTP."""
    message = f"{user_id}:{otp}".encode("utf-8")

    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


def _is_rate_limited(key, limit, window):
    """Basic cache-based rate limiting."""
    if cache.add(key, 1, timeout=window):
        return False

    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window)
        return False

    return count > limit


def _clear_reset_session(request):
    request.session.pop(SESSION_KEY, None)
    request.session.modified = True


@require_http_methods(["GET", "POST"])
def password_reset_request(request):
    """Request a password-reset OTP by registered email."""

    if request.method == "GET":
        return render(
            request,
            "prediction/password_reset_request.html",
        )

    email = request.POST.get("email", "").strip().lower()

    generic_response = render(
        request,
        "prediction/password_reset_request.html",
        {
            "sent": True,
            "message": (
                "If an eligible account matches that email, "
                "a password-reset code will be sent."
            ),
        },
    )

    if not email or len(email) > 254 or "@" not in email:
        return generic_response

    email_hash = hashlib.sha256(
        email.encode("utf-8")
    ).hexdigest()

    # Behind a reverse proxy REMOTE_ADDR is the proxy itself; client_ip() honours TRUSTED_PROXY_COUNT.
    ip_address = security.client_ip(request) or "unknown"

    ip_hash = hashlib.sha256(
        ip_address.encode("utf-8")
    ).hexdigest()

    limited_email = _is_rate_limited(
        f"pwreset:email:{email_hash}:{ip_hash}",
        limit=3,
        window=3600,
    )

    limited_ip = _is_rate_limited(
        f"pwreset:ip:{ip_hash}",
        limit=10,
        window=3600,
    )

    if limited_email or limited_ip:
        return generic_response

    matching_users = User.objects.filter(
        email__iexact=email,
        is_active=True,
    )

    # Avoid resetting an account if the email is ambiguous.
    if matching_users.count() != 1:
        return generic_response

    user = matching_users.first()

    if not user.email:
        return generic_response

    otp = f"{secrets.randbelow(1_000_000):06d}"

    request.session[SESSION_KEY] = {
        "user_id": user.pk,
        "otp_digest": _otp_digest(user.pk, otp),
        "issued_at": int(time.time()),
        "attempts": 0,
        "verified": False,
    }

    request.session.cycle_key()

    message = (
        f"Hello {user.get_username()},\n\n"
        f"Your CardioNova password-reset code is: {otp}\n\n"
        "This code expires in 10 minutes.\n"
        "If you did not request this code, ignore this email.\n\n"
        "Do not share this code with anyone."
    )

    try:
        send_mail(
            subject="CardioNova password reset code",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

    except Exception:
        # Never log the OTP or expose mail-server errors.
        logger.exception(
            "CardioNova password-reset email delivery failed"
        )

        _clear_reset_session(request)

    return generic_response


@require_http_methods(["GET", "POST"])
def password_reset_verify(request):
    """Verify the OTP entered by the user."""

    reset_data = request.session.get(SESSION_KEY)

    if not reset_data:
        return render(
            request,
            "prediction/password_reset_verify.html",
            {
                "error": (
                    "Your reset session has expired. "
                    "Please request a new code."
                ),
                "expired": True,
            },
        )

    age = (
        int(time.time())
        - reset_data.get("issued_at", 0)
    )

    if age > OTP_EXPIRY:
        _clear_reset_session(request)

        return render(
            request,
            "prediction/password_reset_verify.html",
            {
                "error": (
                    "Your code has expired. "
                    "Please request a new one."
                ),
                "expired": True,
            },
        )

    if reset_data.get("verified"):
        return redirect("password_reset_new")

    if request.method == "GET":
        return render(
            request,
            "prediction/password_reset_verify.html",
        )

    otp = request.POST.get("otp", "").strip()

    if (
        len(otp) != 6
        or not otp.isascii()
        or not otp.isdigit()
    ):
        otp = ""

    attempts = reset_data.get("attempts", 0) + 1
    reset_data["attempts"] = attempts

    expected_digest = reset_data.get(
        "otp_digest",
        "",
    )

    actual_digest = (
        _otp_digest(
            reset_data.get("user_id"),
            otp,
        )
        if otp
        else ""
    )

    valid = bool(otp) and secrets.compare_digest(
        expected_digest,
        actual_digest,
    )

    if not valid:
        if attempts >= MAX_OTP_ATTEMPTS:
            _clear_reset_session(request)

            return render(
                request,
                "prediction/password_reset_verify.html",
                {
                    "error": (
                        "Too many incorrect attempts. "
                        "Please request a new code."
                    ),
                    "expired": True,
                },
            )

        request.session[SESSION_KEY] = reset_data
        request.session.modified = True

        return render(
            request,
            "prediction/password_reset_verify.html",
            {
                "error": "Invalid code. Please try again.",
                "remaining_attempts": (
                    MAX_OTP_ATTEMPTS - attempts
                ),
            },
        )

    reset_data["verified"] = True
    reset_data["verified_at"] = int(time.time())

    request.session[SESSION_KEY] = reset_data
    request.session.modified = True

    return redirect("password_reset_new")


@require_http_methods(["GET", "POST"])
def password_reset_new(request):
    """Allow a verified user to choose a new password."""

    reset_data = request.session.get(SESSION_KEY)

    if (
        not reset_data
        or not reset_data.get("verified")
    ):
        return redirect("password_reset_request")

    verified_at = reset_data.get(
        "verified_at",
        0,
    )

    if int(time.time()) - verified_at > OTP_EXPIRY:
        _clear_reset_session(request)
        return redirect("password_reset_request")

    user = User.objects.filter(
        pk=reset_data.get("user_id"),
        is_active=True,
    ).first()

    if user is None:
        _clear_reset_session(request)
        return redirect("password_reset_request")

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)

        if form.is_valid():
            form.save()
            _clear_reset_session(request)

            return redirect("password_reset_complete")

    else:
        form = SetPasswordForm(user)

    return render(
        request,
        "prediction/password_reset_new.html",
        {"form": form},
    )


@require_http_methods(["GET"])
def password_reset_complete(request):
    """Display the successful-reset page."""

    return render(
        request,
        "prediction/password_reset_complete.html",
    )

class RateLimitedPasswordResetView(auth_views.PasswordResetView):
    """Django's e-mail-link reset, limited per IP address so it cannot be used to flood inboxes."""

    def post(self, request, *args, **kwargs):
        if security.hit("password_reset_link", security.client_ip(request)):
            # Same answer as a normal request: it reveals nothing and sends nothing.
            return HttpResponseRedirect(self.get_success_url())
        return super().post(request, *args, **kwargs)
