"""
Security helpers: rate limiting, security headers, request guard and UTM tracking.

Rate limits are defined in settings.RATE_LIMITS and stored in the Django cache.
"""
import hashlib
import logging
import re

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

logger = logging.getLogger("prediction.security")

# Content-Security-Policy: scripts only from this site (+ Chart.js from jsDelivr), no inline scripts or styles.
CSP = ("default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; style-src 'self'; img-src 'self' data:; "
       "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; "
       "frame-ancestors 'none'")
CSP_ADMIN = CSP.replace("style-src 'self'", "style-src 'self' 'unsafe-inline'")      # Django admin uses inline styles


# --------------------------------------------------------------------------- client address and counters
def client_ip(request):
    """Address of the visitor. X-Forwarded-For is trusted only as far as settings.TRUSTED_PROXY_COUNT says."""
    proxies = getattr(settings, "TRUSTED_PROXY_COUNT", 0)
    if proxies > 0:
        parts = [p.strip() for p in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if p.strip()]
        if len(parts) >= proxies:
            return parts[-proxies]          # the entry added by our own proxy; earlier entries can be forged
    return request.META.get("REMOTE_ADDR", "")


def ip_fingerprint(request):
    """Short salted hash of the address, for logs and the contact table (the raw address is not stored)."""
    raw = (settings.SECRET_KEY + client_ip(request)).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _key(name, ident):
    return "rl:%s:%s" % (name, hashlib.sha256(str(ident).encode()).hexdigest()[:32])


def is_limited(name, ident):
    """True when `ident` has already used up its attempts for rate limit `name` (does not count a new attempt)."""
    limit, _ = settings.RATE_LIMITS[name]
    return cache.get(_key(name, ident), 0) >= limit


def hit(name, ident):
    """Counts one attempt. Returns True when the limit is now exceeded."""
    limit, window = settings.RATE_LIMITS[name]
    key = _key(name, ident)
    if cache.add(key, 1, window):
        count = 1
    else:
        try:
            count = cache.incr(key)
        except ValueError:                  # the key expired between add() and incr()
            cache.set(key, 1, window)
            count = 1
    return count > limit


def reset(name, ident):
    cache.delete(_key(name, ident))


def too_many_requests(request, wait_minutes=15):
    """429 page (JSON for the API)."""
    from django.http import JsonResponse
    from django.shortcuts import render
    if request.path.startswith("/api/"):
        response = JsonResponse({"error": "Too many requests. Please slow down."}, status=429)
    else:
        response = render(request, "prediction/error.html", {
            "code": 429, "title": "Too many attempts",
            "message": f"Please wait about {wait_minutes} minutes and try again."}, status=429)
    response["Retry-After"] = str(wait_minutes * 60)
    return response


# --------------------------------------------------------------------------- middleware
class SecurityHeadersMiddleware:
    """Adds the headers Django does not add itself, and stops browsers from caching private pages."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        admin = request.path.startswith("/" + settings.ADMIN_URL)
        response.setdefault("Content-Security-Policy", CSP_ADMIN if admin else CSP)
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
        response.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        response.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        # No CORS headers are ever sent: other websites cannot read responses from this site in a browser.
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not request.path.startswith("/static/"):
            response["Cache-Control"] = "no-store"          # health data must not stay in a shared or back-button cache
        return response


class RequestGuardMiddleware:
    """Rejects oversized requests, optionally limits the admin to listed IPs and throttles admin login attempts."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            length = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            return HttpResponse("Bad request.", status=400, content_type="text/plain")
        if length > settings.MAX_REQUEST_BYTES:
            return HttpResponse("The request is too large.", status=413, content_type="text/plain")

        if request.path.startswith("/" + settings.ADMIN_URL):
            ip = client_ip(request)
            allowed = settings.ADMIN_ALLOWED_IPS
            if allowed and ip not in allowed:
                return HttpResponse("Not found.", status=404, content_type="text/plain")     # pretend it is not there
            if request.method == "POST" and request.path.rstrip("/").endswith("/login"):
                if hit("admin_login", ip):
                    logger.warning("admin login throttled ip_hash=%s", ip_fingerprint(request))
                    return too_many_requests(request)
        return self.get_response(request)


_UTM_VALUE = re.compile(r"[A-Za-z0-9_.\-]{1,100}")
UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign")


class UTMMiddleware:
    """Remembers the first campaign (utm_source / utm_medium / utm_campaign) a visitor arrived with, in the session.
    It is saved on the profile at registration. Values are restricted to harmless characters."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session = getattr(request, "session", None)
        if request.method == "GET" and session is not None and any(k in request.GET for k in UTM_KEYS):
            if "utm" not in session:                          # first touch wins
                found = {k: request.GET[k] for k in UTM_KEYS if _UTM_VALUE.fullmatch(request.GET.get(k, ""))}
                if found:
                    session["utm"] = found
        return self.get_response(request)
