"""
Django settings for the Heart Disease Prediction System.

Works out of the box for local development. For deployment set the environment
variables listed in .env.example (DJANGO_SECRET_KEY, DJANGO_DEBUG=0, DATABASE_URL, ...).
"""

import os
import secrets
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv():
    """Tiny .env reader (KEY=VALUE lines) so that no extra package is needed."""
    path = BASE_DIR / ".env"

    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()

            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(
                    key.strip(),
                    value.strip().strip('"').strip("'"),
                )


_load_dotenv()


def env_list(name, default=""):
    return [
        item.strip()
        for item in os.environ.get(name, default).split(",")
        if item.strip()
    ]


# ============================================================
# CORE SETTINGS
# ============================================================

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")

if not SECRET_KEY:
    if not DEBUG: 
        raise ImproperlyConfigured(
            "Set DJANGO_SECRET_KEY when DJANGO_DEBUG=0."
        )

    SECRET_KEY = secrets.token_urlsafe(50)

elif not DEBUG and (
    len(SECRET_KEY) < 32
    or SECRET_KEY.lower().startswith(
        ("django-insecure", "put-a-long")
    )
    or "change-this" in SECRET_KEY.lower()
):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is too short or still a placeholder "
        "(use 32+ random characters)."
    )


ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    "127.0.0.1,localhost,[::1],testserver",
)

CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS"
)

_render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

if _render_host:
    ALLOWED_HOSTS.append(_render_host)
    CSRF_TRUSTED_ORIGINS.append(
        f"https://{_render_host}"
    )


# ============================================================
# INSTALLED APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "prediction",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "prediction.security.SecurityHeadersMiddleware",
    "prediction.security.RequestGuardMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "prediction.security.UTMMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "heart_disease.urls"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "prediction.context_processors.model_status",
            ],
        },
    },
]


WSGI_APPLICATION = "heart_disease.wsgi.application"
ASGI_APPLICATION = "heart_disease.asgi.application"


# ============================================================
# DATABASE
# ============================================================

# SQLite locally; PostgreSQL or another supported database
# when DATABASE_URL is configured.

if os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": dj_database_url.parse(
            os.environ["DATABASE_URL"],
            conn_max_age=600,
        )
    }

    if os.environ.get("DJANGO_DB_SSLMODE"):
        DATABASES["default"].setdefault(
            "OPTIONS", {}
        )["sslmode"] = os.environ["DJANGO_DB_SSLMODE"]

else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

DATABASES["default"]["ATOMIC_REQUESTS"] = True


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        )
    },
]


# ============================================================
# LANGUAGE AND TIME
# ============================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = os.environ.get(
    "DJANGO_TIME_ZONE",
    "Asia/Kolkata",
)

USE_I18N = True
USE_TZ = True


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": (
            "django.core.files.storage.FileSystemStorage"
        ),
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedStaticFilesStorage"
        ),
    },
}


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================
# AUTHENTICATION REDIRECTS
# ============================================================

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"


# ============================================================
# SECURITY SETTINGS
# ============================================================

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

if not DEBUG:
    _ssl = (
        os.environ.get("DJANGO_SECURE_SSL", "1") == "1"
    )

    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

    SECURE_SSL_REDIRECT = _ssl
    SESSION_COOKIE_SECURE = _ssl
    CSRF_COOKIE_SECURE = _ssl

    SECURE_HSTS_SECONDS = (
        int(
            os.environ.get(
                "DJANGO_HSTS_SECONDS",
                "2592000",
            )
        )
        if _ssl
        else 0
    )

    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False


# ============================================================
# LOGGING
# ============================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": (
                "%(asctime)s %(levelname)s "
                "%(name)s: %(message)s"
            )
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get(
            "DJANGO_LOG_LEVEL",
            "INFO",
        ),
    },
}


# ============================================================
# SITE DETAILS
# ============================================================

SITE_LAST_UPDATED = os.environ.get(
    "SITE_LAST_UPDATED",
    "13 October 2026",
)

CONTACT_EMAIL = os.environ.get(
    "CONTACT_EMAIL",
    "contact@example.com",
)


# ============================================================
# EMAIL CONFIGURATION
# Used by the OTP-based Forgot Password feature.
# ============================================================

# Local development:
# Django prints the email and OTP in the terminal.
#
# Production:
# Configure a real SMTP email service through environment
# variables. Never put your email password in this file.

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    (
        "django.core.mail.backends.console.EmailBackend"
        if DEBUG
        else "django.core.mail.backends.smtp.EmailBackend"
    ),
)

EMAIL_HOST = os.environ.get(
    "EMAIL_HOST",
    "smtp.gmail.com",
)

EMAIL_PORT = int(
    os.environ.get("EMAIL_PORT", "587")
)

EMAIL_USE_TLS = (
    os.environ.get("EMAIL_USE_TLS", "1") == "1"
)

EMAIL_USE_SSL = (
    os.environ.get("EMAIL_USE_SSL", "0") == "1"
)

EMAIL_HOST_USER = os.environ.get(
    "EMAIL_HOST_USER",
    "",
)

EMAIL_HOST_PASSWORD = os.environ.get(
    "EMAIL_HOST_PASSWORD",
    "",
)

DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    EMAIL_HOST_USER or CONTACT_EMAIL,
)


# Password-reset OTP settings.
# 600 seconds = 10 minutes.
PASSWORD_RESET_OTP_EXPIRY_SECONDS = 600

# Maximum incorrect OTP attempts per reset session.
PASSWORD_RESET_OTP_MAX_ATTEMPTS = 5


# ============================================================
# ADMIN PROTECTION
# ============================================================

ADMIN_URL = (
    os.environ.get(
        "DJANGO_ADMIN_URL",
        "admin/",
    ).strip("/")
    + "/"
)

ADMIN_ALLOWED_IPS = env_list(
    "DJANGO_ADMIN_ALLOWED_IPS"
)


# ============================================================
# SESSION AND COOKIE SETTINGS
# ============================================================

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True

SESSION_COOKIE_AGE = 60 * 60 * 12

CSRF_FAILURE_VIEW = "prediction.views.csrf_failure"


# ============================================================
# REQUEST AND UPLOAD LIMITS
# ============================================================

MAX_REQUEST_BYTES = 2 * 1024 * 1024

DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024

FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024

DATA_UPLOAD_MAX_NUMBER_FIELDS = 200


# ============================================================
# RATE LIMITING
# ============================================================

RATE_LIMITS = {
    "login_fail": (5, 900),
    "login_ip": (50, 900),
    "register": (10, 3600),
    "contact": (5, 3600),
    "api": (60, 60),
    "whatif": (120, 60),
    "admin_login": (15, 900),
    "delete_account": (5, 3600),
}


# Number of reverse proxies in front of the application.
# 0 = use the direct socket address.

TRUSTED_PROXY_COUNT = int(
    os.environ.get(
        "DJANGO_TRUSTED_PROXIES",
        "0" if DEBUG else "1",
    )
)


# ============================================================
# CACHE CONFIGURATION
# ============================================================

# Redis is recommended for shared rate limiting when using
# multiple workers or application instances.

if os.environ.get("REDIS_URL"):
    CACHES = {
        "default": {
            "BACKEND": (
                "django.core.cache.backends.redis.RedisCache"
            ),
            "LOCATION": os.environ["REDIS_URL"],
        }
    }

else:
    CACHES = {
        "default": {
            "BACKEND": (
                "django.core.cache.backends.locmem.LocMemCache"
            ),
            "LOCATION": "heartcare",
        }
    }